from langgraph.graph import StateGraph, START, END
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from src.tools.item_filter import item_filter_tool
from src.tools.get_user_metadata import get_user_metadata_tool
from src.tools.get_item_metadata import get_item_metadata_tool
from src.tools.get_interacted_items import get_interacted_items_tool
from src.tools.get_like_percentage import get_like_percentage_tool
from src.tools.get_popular_items import get_popular_items_tool
from src.tools.vector_store_search import vector_store_search_tool
from src.tools.get_top_k_recommendations import get_top_k_recommendations_tool
from langchain_core.messages import AIMessageChunk
from src.utils import in_context_vector_store_search, format_tool_example
from src.agents.utils import State, route_tools, BasicToolNode

available_tools = (item_filter_tool, get_user_metadata_tool, get_item_metadata_tool, get_interacted_items_tool,
                   get_top_k_recommendations_tool, get_like_percentage_tool, get_popular_items_tool,
                   vector_store_search_tool)


class Agent:
    def __init__(self, model, system_message, memory, tools=available_tools):
        self.system_message = system_message
        self.memory = memory
        self.graph = None
        self.tools = tools
        self.model_with_tools = model.bind_tools(self.tools)
        self.conversation_started = False
        self.set_graph(StateGraph(State))

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

    def prepare_messages(self, user_input, messages, in_context_examples=False):
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
