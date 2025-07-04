from typing import Annotated
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
import os
import argparse
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
import json
from langchain_core.messages import ToolMessage, AIMessageChunk
from langchain_ollama.chat_models import ChatOllama
from src.tools.get_top_k_recommendations import get_top_k_recommendations_tool
from src.utils import create_ml100k_db, create_vector_store, ensure_qdrant_running
from src.tools.item_filter import item_filter_tool
from src.tools.get_user_metadata import get_user_metadata_tool
from src.tools.get_item_metadata import get_item_metadata_tool
from src.tools.get_interacted_items import get_interacted_items_tool
from src.tools.get_like_percentage import get_like_percentage_tool
from src.tools.get_popular_items import get_popular_items_tool
from src.tools.vector_store_search import vector_store_search_tool
from src.tools.utils import create_lists_for_fuzzy_matching
from src.constants import SYSTEM_MESSAGE, SYSTEM_MESSAGE_ENHANCED
import chainlit as cl
load_dotenv()

memory = MemorySaver()

# create database
create_ml100k_db()
create_lists_for_fuzzy_matching()
ensure_qdrant_running()
create_vector_store()

# this is the list of tools that can be used by the LLM
tools = [item_filter_tool, get_user_metadata_tool, get_item_metadata_tool, get_interacted_items_tool,
         get_top_k_recommendations_tool, get_like_percentage_tool, get_popular_items_tool, vector_store_search_tool]

# this defines the state of the LLM, containing all the messages of the session
class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


# the graph defines the process the LLM has to use to answer the user queries
graph_builder = StateGraph(State)

llm = None

if os.getenv("SELF_HOST") == "true":
    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0,
        base_url="http://localhost:11434"
    )
else:
    api_key = os.getenv("OPENAI_API_KEY")

    llm = init_chat_model("openai:gpt-4.1", api_key=api_key)

# we tell the LLM which tools it can call
llm_with_tools = llm.bind_tools(tools)

# the chatbot is one of the nodes of the graph, usually where the process starts
def chatbot(state: State):
    messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=20000,
        start_on="human",
        end_on=("human", "tool"),
        include_system=True,
    )
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# this is the tool node
class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)

# define the tool node
tool_node = BasicToolNode(tools=tools)
# add the node to the graph
graph_builder.add_node("tools", tool_node)

def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "END" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    route_tools,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
    {"tools": "tools", END: END},
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile(checkpointer=memory)

# this is like the stream_tokes in Entities API
# given the user input, it produces the output of the LLM
config = {"configurable": {"thread_id": "1"}}

@cl.on_chat_start
def start():
    # Initialize the session state
    cl.user_session.set("conversation_started", False)
    cl.user_session.set("messages", [])

@cl.on_message
async def stream_graph_updates(message: cl.Message):
    user_input = message.content
    conversation_started = cl.user_session.get("conversation_started")
    messages = cl.user_session.get("messages")

    if not conversation_started:
        messages.extend(SYSTEM_MESSAGE if os.getenv("SELF_HOST") == "true" else SYSTEM_MESSAGE_ENHANCED)
        cl.user_session.set("conversation_started", True)

    messages.append({"role": "user", "content": user_input})

    msg = cl.Message(content="")

    # Stream responses from the model
    async for message_chunk, metadata in graph.astream({"messages": messages}, config=config, stream_mode="messages"):
        if message_chunk.content and isinstance(message_chunk, AIMessageChunk):
            await msg.stream_token(message_chunk.content)
        # for value in event.values():
        #     if isinstance(value["messages"][-1], AIMessage):
        #         content = value["messages"][-1].content
        #         await cl.Message(content=content).send()

    await msg.send()
    # Save updated message list
    cl.user_session.set("messages", messages)
