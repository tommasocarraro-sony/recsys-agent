from recbole.quick_start import run_recbole
from pathlib import Path

def set_env_variable(key, value, env_file_path="../../.env"):
    env_path = Path(env_file_path)
    env_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

    lines = []
    found = False

    if env_path.exists():
        with env_path.open("r") as file:
            lines = file.readlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):  # strip in case of leading spaces
                lines[i] = f"{key}={value}\n"
                found = True
                break

    if not found:
        lines.append(f"{key}={value}\n")

    with env_path.open("w") as file:
        file.writelines(lines)

run_recbole(model='BPR', dataset='ml-100k', config_file_list=['./bprmf-100k.yaml'])

saved_dir = Path("./saved")
saved_file = next(saved_dir.glob("*"), None)  # Get the first file in the ./saved/ directory

if saved_file and saved_file.is_file():
    full_path = saved_file.resolve()
    set_env_variable("RECSYS_MODEL_PATH", str(full_path))
    print(f"Added to .env: RECSYS_MODEL_PATH={full_path}")
else:
    print("No file found in ./saved/")
