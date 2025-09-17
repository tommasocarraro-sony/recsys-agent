from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from src.agents.utils import create_agent_envinroment
from src.tools.get_user_info import get_user_info_tool
from src.tools.get_user_history import get_user_history_tool
from src.tools.filter_items_by_attributes import filter_items_by_attributes_tool
from src.tools.get_item_info import get_item_info_tool
from src.tools.estimate_like_percentage import estimate_like_percentage_tool
from src.tools.recommend_items import recommend_items_tool
from src.tools.filter_items_by_popularity import filter_items_by_popularity_tool
from src.tools.semantic_search_items import semantic_search_items_tool

load_dotenv()

checkpointer = MemorySaver()

create_agent_envinroment(in_context_examples=False)

api_key = os.getenv("OPENAI_API_KEY")

# llm = init_chat_model("openai:gpt-4.1", api_key=api_key)

llm = ChatOllama(
    # model="qwen2.5:72b-instruct-q6_K",
    model="gpt-oss:120b",
    temperature=0,
    base_url="http://localhost:11434"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful streaming platform assistant.
    
    STRICT RULES:
    1. To answer user queries, you MUST use the available tools. Do not perform any logic or computation on your own.
    2. You need to present a tool call plan before answering **EACH** query (e.g., Step i: I will call <tool> for <reason>).
    3. For recommendation queries, you **MUST** always call the recommendation tool, among the others.
    4. When listing items, always include their IDs.
    5. Never change or hallucinate tool results, even if you feel they are wrong! Always show them as they are returned from the tools!

    Before recommending items, you can optionally:
    1. Filter items.
    2. Search items by description/storyline.
    3. Search items by keywords (useful for mood-based queries).

    After performing recommendation, you need to:
    1. Get useful information to list the recommended items.
    2. Ask the user whether an explanation is needed.

    To compute statistics (e.g., best genre, ideal duration), you can:
    1. Filter items.
    2. Get the **THREE** most popular items out of the filtered ones.
    3. Get useful information about these items and reason about it.

    To explain recommendations, you can:
    1. Get the history of the user.
    2. Get information about items in the history of the user.
    3. Compare this information with the information of the recommended items.
    """),
    ("placeholder", "{history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

tools = [get_item_info_tool, get_user_history_tool, estimate_like_percentage_tool, recommend_items_tool,
           filter_items_by_popularity_tool, get_user_info_tool, filter_items_by_attributes_tool, semantic_search_items_tool]

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_ex = AgentExecutor(agent=agent, tools=tools, verbose=True)

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

agent_ex_w_mem = RunnableWithMessageHistory(
    agent_ex,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)


while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break

    result = agent_ex.invoke({"input": user_input}, config={"configurable": {"session_id": "1"}})

    # for m in result["messages"]:
    #     m.pretty_print()
