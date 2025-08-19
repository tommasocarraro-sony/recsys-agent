import os
import argparse
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from langchain_ollama.chat_models import ChatOllama
from src.agents.agent import Agent
from src.constants import SYSTEM_MESSAGE_GPT_OSS, SHORT_SYSTEM_MESSAGE_ENHANCED, LONG_SYSTEM_MESSAGE_ENHANCED
from src.agents.utils import create_agent_envinroment
from langgraph.checkpoint.memory import MemorySaver
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--self_host", action="store_true", help="Use locally hosted model via Ollama")
parser.add_argument("--llm", default="gpt-oss:20b", help="Ollama model to be used")
parser.add_argument("--in_context", action="store_true", help="Whether to use in-context RAG")
args = parser.parse_args()

create_agent_envinroment(args.in_context)

if not args.self_host and args.llm != "gpt-oss:20b":
    raise Exception("You must specify --self_host when using --llm")

llm = None

if args.self_host:
    llm = ChatOllama(
        model=args.llm,
        temperature=0,
        base_url="http://localhost:11434"
    )
else:
    api_key = os.getenv("OPENAI_API_KEY")

    llm = init_chat_model("openai:gpt-4.1", api_key=api_key)

agent = Agent(llm, SYSTEM_MESSAGE_GPT_OSS if args.self_host else LONG_SYSTEM_MESSAGE_ENHANCED, MemorySaver())

while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    agent.stream_graph_updates(user_input, in_context_examples=args.in_context)
