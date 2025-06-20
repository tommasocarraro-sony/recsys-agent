import subprocess
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--self_host", action="store_true", help="Use locally hosted model via Ollama")
args = parser.parse_args()

cmd = ["chainlit", "run", "chainlit_example.py"]
if args.self_host:
    os.environ["SELF_HOST"] = "true"

subprocess.run(cmd)

# todo solve bug item 98
# todo put the item_id in the query always so that is always returned and the LLM does not make confusion