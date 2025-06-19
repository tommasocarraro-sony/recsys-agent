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
