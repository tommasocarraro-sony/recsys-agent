import subprocess
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--self_host", action="store_true", help="Use locally hosted model via Ollama")
parser.add_argument("--llm", default="qwen2.5:7b", help="Ollama model to be used")
args = parser.parse_args()

cmd = ["chainlit", "run", "chainlit_example.py"]

if args.llm and not args.self_host:
    raise Exception("You must specify --self_host when using --llm")

if args.self_host:
    os.environ["SELF_HOST"] = "true"
    os.environ["LLM"] = args.llm

subprocess.run(cmd)
