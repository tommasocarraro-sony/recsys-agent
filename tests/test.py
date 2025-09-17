import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from src.agents.utils import create_agent_envinroment
from src.tools.estimate_like_percentage import estimate_like_percentage
from src.tools.filter_items_by_attributes import filter_items_by_attributes
from src.tools.filter_items_by_popularity import filter_items_by_popularity
from src.tools.get_item_info import get_item_info
from src.tools.get_user_history import get_user_history
from src.tools.get_user_info import get_user_info
from src.tools.recommend_items import recommend_items
from src.tools.semantic_search_items import semantic_search_items

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "recommendation-agent"
os.environ["LANGCHAIN_ENDPOINT"]="https://eu.api.smith.langchain.com/"
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client
from langchain.chat_models import init_chat_model
from langchain_ollama.chat_models import ChatOllama
from src.eval.utils import create_langsmith_dataset, evaluate_model
import argparse

create_agent_envinroment(in_context_examples=False)


parser = argparse.ArgumentParser()
parser.add_argument("--llm", default="openai:gpt-4.1", help="Model to be evaluated")
parser.add_argument("--evaluation", default="recommendation_standard", help="Dataset to be evaluated")
args = parser.parse_args()

client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

if args.llm == "openai:gpt-4.1":
    llm = init_chat_model("openai:gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
else:
    llm = ChatOllama(model=args.llm, temperature=0, base_url="http://localhost:11434")

checkpointer = MemorySaver()

agent = create_react_agent(
    model=llm,
    tools=[get_item_info, get_user_history, estimate_like_percentage, recommend_items,
           filter_items_by_popularity, get_user_info, filter_items_by_attributes, semantic_search_items],
    prompt="""
    You are a helpful streaming platform assistant.

    STRICT RULES:
    1. To answer user queries, you MUST use the available tools.
    2. You cannot perform any logic on your own. You can just reason about tool results or display them.
    3. You need to present a tool call plan (e.g., Step i: I will call <tool> for <reason>.) before answering **EACH** query.
    4. For recommendation queries, you **MUST** always call the recommendation tool, among the others.
    5. When listing items, always include their IDs.
    6. Never change tool results! Always show them as they are retuned from the tools.

    Before recommending items, you can optionally:
    1. Filter items.
    2. Search items by description/storyline.
    3. Search items by keywords (useful for mood-based queries).

    After performing recommendation, you need to:
    1. Get useful information to list the recommended items.
    2. Ask the user whether an explanation is needed.

    To compute statistics, you can:
    1. Filter items.
    2. Get the **THREE** most popular items out of the filtered ones.
    3. Get useful information about these items and reason about it.

    To explain recommendations, you can:
    1. Get the history of the user.
    2. Get information about items in the history of the user.
    3. Compare this information with the information of the recommended items.
    """,
    checkpointer=checkpointer
)

create_langsmith_dataset(client, f"./tests/by_type/evaluation_{args.evaluation}.json", f"{args.evaluation} evaluation")

evaluate_model(agent, f"{args.evaluation} evaluation")

# todo take into consideration that there are some prompts that should not be deterministic and we gave too detailed instruction to the model that could probably no generalize due to this problems
# todo let's see tomorrow
# todo prompts with vector store search are not really deterministic -> we will investigate generalization capabilities of these prompts
# todo maybe we should avoid asking the model to generate a tool call plan

# todo remove non-deterministic examples from evaluation or make it better for Qwen in some way -> if these fail on the medium evaluation then we understand the reason -> we need to create the examples by hand again because we need tool calls for generating the results of them
# todo save this prompt somewhere as it is 70% accuracy and fix other in-context examples


# todo see if it is necessary to delete the history of the conversation each time so the model does not make confusion