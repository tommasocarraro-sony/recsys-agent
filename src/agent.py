from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from src.utils import create_ml100k_db, create_vector_store, ensure_qdrant_running, create_vector_store_examples
from src.tools.item_filter import item_filter_tool
from src.tools.get_user_metadata import get_user_metadata_tool
from src.tools.get_item_metadata import get_item_metadata_tool
from src.tools.get_interacted_items import get_interacted_items_tool
from src.tools.get_like_percentage import get_like_percentage_tool
from src.tools.get_popular_items import get_popular_items_tool
from src.tools.vector_store_search import vector_store_search_tool
from src.tools.utils import create_lists_for_fuzzy_matching
from src.tools.get_top_k_recommendations import get_top_k_recommendations_tool
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from typing import Annotated
from langchain_core.messages import ToolMessage, AIMessageChunk
from src.utils import in_context_vector_store_search, format_tool_example
import json


# this defines the state of the LLM, containing all the messages of the session
class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


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


class Agent:
    def __init__(self, model, system_message):
        self.system_message = system_message
        self.memory = None
        self.graph = None
        self.tools = [item_filter_tool,
                      get_user_metadata_tool,
                      get_item_metadata_tool,
                      get_interacted_items_tool,
                      get_top_k_recommendations_tool,
                      get_like_percentage_tool,
                      get_popular_items_tool,
                      vector_store_search_tool]
        self.model_with_tools = model.bind_tools(self.tools)
        self.conversation_started = False
        self.init_agent()

    def set_memory(self, memory: MemorySaver):
        self.memory = memory

    def set_graph(self, graph_builder: StateGraph):
        def chatbot_node(state: State):
            messages = trim_messages(
                state["messages"],
                strategy="last",
                token_counter=count_tokens_approximately,
                max_tokens=20000,
                start_on="human",
                end_on=("human", "tool"),
                include_system=True,
            )
            response = self.model_with_tools.invoke(messages)
            print(f"\n\n----\n\nTool calls related to response:\n\n{response.tool_calls}\n\n----\n\n")
            return {"messages": [response]}

        graph_builder.add_node("chatbot", chatbot_node)
        graph_builder.add_node("tools", BasicToolNode(tools=self.tools))
        graph_builder.add_conditional_edges("chatbot", route_tools,{"tools": "tools", END: END})
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        self.graph = graph_builder.compile(checkpointer=self.memory)

    def init_agent(self):
        self.create_agent_envinroment()
        self.set_memory(MemorySaver())
        self.set_graph(StateGraph(State))

    @staticmethod
    def create_agent_envinroment():
        create_ml100k_db()
        create_lists_for_fuzzy_matching()
        ensure_qdrant_running()
        create_vector_store()
        create_vector_store_examples()

    def prepare_messages(self, user_input, messages, in_context_examples):
        if not self.conversation_started:
            messages.extend(self.system_message)
            self.conversation_started = True

        if in_context_examples:
            in_context_examples = in_context_vector_store_search(user_input)

            if in_context_examples[0]["score"] > 0.7:
                print(f"Selected in-context examples: {in_context_examples}")
                messages.append({"role": "user", "content": format_tool_example(
                    in_context_examples) + "\n\nTarget user query:\n\n'" + user_input + "'. \n\n**Call** the planned tools."})
            else:
                messages.append({"role": "user", "content": user_input})
        else:
            messages.append({"role": "user", "content": user_input})

    def stream_graph_updates(self, user_input: str, in_context_examples=False):
        messages = []

        self.prepare_messages(user_input, messages, in_context_examples)

        for message_chunk, metadata in self.graph.stream({"messages": messages}, config={"configurable": {"thread_id": "1"}}, stream_mode="messages"):
            if message_chunk.content and isinstance(message_chunk, AIMessageChunk):
                print(message_chunk.content, end="", flush=True)

    def graph_invoke(self, user_input: str, in_context_examples=False):
        messages = []

        self.prepare_messages(user_input, messages, in_context_examples)

        return self.graph.invoke({"messages": messages}, config={"configurable": {"thread_id": "1"}})
