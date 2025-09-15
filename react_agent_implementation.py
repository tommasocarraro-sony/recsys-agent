from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from src.constants import LONG_SYSTEM_MESSAGE_ENHANCED
from langgraph.checkpoint.memory import MemorySaver
from src.agents.utils import create_agent_envinroment
from src.tools.get_user_info import get_user_info
from src.tools.get_user_history import get_user_history
from src.tools.filter_items_by_attributes import filter_items_by_attributes
from src.tools.get_item_info import get_item_info
from src.tools.estimate_like_percentage import estimate_like_percentage
from src.tools.recommend_items import recommend_items
from src.tools.filter_items_by_popularity import filter_items_by_popularity
from src.tools.semantic_search_items import semantic_search_items

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

agent = create_react_agent(
    model=llm,
    tools=[get_item_info, get_user_history, estimate_like_percentage, recommend_items,
           filter_items_by_popularity, get_user_info, filter_items_by_attributes, semantic_search_items],
    prompt="""
    You are a helpful recommendation assistant. You can answer questions about recommendation or statistics. You NEED to call MULTIPLE tools to answer these questions.

    Before recommending items, you can:
    1. Filter items by attribute values and/or popularity.
    2. Search items by description/storyline. Note: It might be necessary to fetch the description before searching.
    3. Search items by keywords. Useful for user mood-based queries.

    After performing recommendation, you need to:
    1. Get useful information to list the recommended items.
    2. Ask the user whether an explanation is needed.

    To compute statistics (e.g., best genre, ideal duration), you can:
    1. Filter items based on the user specified attributes.
    2. Get the **THREE** most popular items out of the filtered ones.
    3. Get useful information about these items and reason about it.

    To explain recommendations, you can:
    1. Get the history of the user.
    2. Get information about items in the history of the user.
    3. Compare this information with the information of the recommended items.
    """,
    checkpointer=checkpointer
)

while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break

    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]},
                          config={"configurable": {"thread_id": "1"}})

    for m in result["messages"]:
        m.pretty_print()

# todo come back to previous version and save it in the dev branch, then push the new version to the new_tools branch and start tweaking the system prompt
