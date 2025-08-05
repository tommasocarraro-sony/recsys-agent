"""
EASY EVALUATION:

This is for comparing GPT4.1 and Qwen2.5 on a very simple dataset that is composed of examples that:
1. Are included in the system prompt of GPT4.1
2. Are given as in-context examples to Qwen2.5

This is very useful to evaluate whether these models are able to call the right tools and in the right order.

MEDIUM EVALUATION:

This is for comparing GPT4.1 and Qwen2.5 on a dataset similar to the easy one. Examples will be very similar to examples that:
1. Are included in the system prompt of GPT4.1
2. Are given as in-context examples to Qwen2.5

This is very useful to evaluate whether these models are able to slightly generalize. Examples will be mainly based on different user IDs.

HARD EVALUATION:

This is for comparing GPT4.1 and Qwen2.5 on a dataset completely different to the examples that:
1. Are included in the system prompt of GPT4.1
2. Are given as in-context examples to Qwen2.5

This is very useful to evaluate whether these models are able to provide incredible generalization. Examples will be
designed so that the combination of tools needed to reply to user queries will be very different from the combinations
seen in the examples provided in the system prompt or as in-context examples.
"""

import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "recommendation-agent"
os.environ["LANGCHAIN_ENDPOINT"]="https://eu.api.smith.langchain.com/"
from dotenv import load_dotenv
load_dotenv()
from langsmith import Client
from src.agent import Agent
from langchain.chat_models import init_chat_model
from langchain_ollama.chat_models import ChatOllama
from src.constants import SYSTEM_MESSAGE_ENHANCED, SHORT_SYSTEM_MESSAGE
from src.eval.utils import create_langsmith_dataset, evaluate_model
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--llm", default="openai:gpt-4.1", help="Model to be evaluated")
parser.add_argument("--evaluation", default="easy", help="Type of evaluation: easy, medium, or hard")
args = parser.parse_args()

assert args.evaluation in ["easy", "medium", "hard"], "Wrong evaluation type"

client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))

if args.llm == "openai:gpt-4.1":
    llm = init_chat_model("openai:gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
    llm_agent = Agent(llm, SYSTEM_MESSAGE_ENHANCED)
else:
    llm = ChatOllama(model=args.llm, temperature=0, base_url="http://localhost:11434")
    llm_agent = Agent(llm, SHORT_SYSTEM_MESSAGE)

create_langsmith_dataset(client, f"./tests/evaluation_{args.evaluation}.json", f"{args.evaluation} evaluation")
# GPT does not use in-context examples because the model is capable enough to read a long system prompt that can contain all the examples
# Qwen needs in-context examples because is not capable enough to deal with long system prompts

evaluate_model(llm_agent, f"{args.evaluation} evaluation", in_context_examples=False if args.llm == "openai:gpt-4.1" else True)

# todo take into consideration that there are some prompts that should not be deterministic and we gave too detailed instruction to the model that could probably no generalize due to this problems
# todo let's see tomorrow
# todo prompts with vector store search are not really deterministic -> we will investigate generalization capabilities of these prompts
# todo maybe we should avoid asking the model to generate a tool call plan

# todo remove non-deterministic examples from evaluation or make it better for Qwen in some way -> if these fail on the medium evaluation then we understand the reason -> we need to create the examples by hand again because we need tool calls for generating the results of them
# todo save this prompt somewhere as it is 70% accuracy and fix other in-context examples