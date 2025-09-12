from langchain.chat_models import init_chat_model
import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from src.constants import LONG_SYSTEM_MESSAGE_ENHANCED
from langgraph.checkpoint.memory import MemorySaver
from src.agents.utils import create_agent_envinroment
from src.tools.get_user_metadata import get_user_metadata_tool
from src.tools.get_interacted_items import get_interacted_items_tool
from src.tools.item_filter import item_filter_tool
from src.tools.get_item_metadata import get_item_metadata_tool
from src.tools.get_like_percentage import get_like_percentage_tool
from src.tools.get_top_k_recommendations import get_top_k_recommendations_tool
from src.tools.get_popular_items import get_popular_items_tool
from src.tools.vector_store_search import vector_store_search_tool

load_dotenv()

checkpointer = MemorySaver()

create_agent_envinroment(in_context_examples=False)

api_key = os.getenv("OPENAI_API_KEY")

# llm = init_chat_model("openai:gpt-4.1", api_key=api_key)

llm = ChatOllama(
    # model="qwen2.5:72b-instruct-q6_K",
    model="qwen2.5:72b-instruct-q6_K",
    temperature=0,
    base_url="http://localhost:11434"
)

agent = create_react_agent(
    model=llm,
    tools=[get_item_metadata_tool, get_interacted_items_tool, get_like_percentage_tool, get_top_k_recommendations_tool,
           get_popular_items_tool, get_user_metadata_tool, item_filter_tool, vector_store_search_tool,],
    prompt=LONG_SYSTEM_MESSAGE_ENHANCED[0]["content"],
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
