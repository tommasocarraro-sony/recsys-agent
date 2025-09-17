import json
import os
from typing import Dict, Any, List, Callable
from src.tools.estimate_like_percentage import estimate_like_percentage
from src.tools.filter_items_by_attributes import filter_items_by_attributes
from src.tools.filter_items_by_popularity import filter_items_by_popularity
from src.tools.get_item_info import get_item_info
from src.tools.recommend_items import recommend_items, create_recbole_environment
from src.tools.get_user_info import get_user_info
from src.tools.semantic_search_items import semantic_search_items
from src.tools.get_user_history import get_user_history
from src.tools.utils import create_lists_for_fuzzy_matching
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--evaluation", default="easy", help="Type of evaluation: easy, medium, or hard")
args = parser.parse_args()

create_lists_for_fuzzy_matching()
create_recbole_environment(os.getenv("RECSYS_MODEL_PATH"))

tool_functions = {
    "filter_items_by_attributes": filter_items_by_attributes,
    "recommend_items": recommend_items,
    "get_item_info": get_item_info,
    "get_user_info": get_user_info,
    "estimate_like_percentage": estimate_like_percentage,
    "filter_items_by_popularity": filter_items_by_popularity,
    "semantic_search_items": semantic_search_items,
    "get_user_history": get_user_history,
}


def resolve_argument_placeholders(arg, previous_results, tool_calls=None):
    """Recursively resolve <...> placeholders in the arguments using tool call context."""
    if isinstance(arg, str):
        if arg.startswith("<") and arg.endswith(">"):
            placeholder = arg.strip("<>")
            # Go backwards through the tool calls to find the relevant result
            for i in range(len(previous_results) - 1, -1, -1):
                if tool_calls:
                    tool_name = tool_calls[i]["name"]
                    if tool_name.replace("_", " ") in placeholder or tool_name in placeholder:
                        result = previous_results[i]
                        if "storyline" in placeholder.lower() and 'storyline' in result[0]:
                            return result[0]['storyline']
                        if "age category" in placeholder.lower() and isinstance(result, dict) and "age_category" in result:
                            return [result["age_category"]]
                        if "gender" in placeholder.lower() and isinstance(result, dict) and "gender" in result:
                            return [result["gender"]]
                        if "file path" in placeholder.lower() and isinstance(result, str):
                            return result
                        if "list" in placeholder.lower() and isinstance(result, list):
                            return result
                        if "string" in placeholder.lower() and isinstance(result, str):
                            return result
                        if "dictionary" in placeholder.lower() and isinstance(result, dict):
                            return result
        else:
            return arg
    elif isinstance(arg, list):
        return [resolve_argument_placeholders(a, previous_results, tool_calls) for a in arg]
    elif isinstance(arg, dict):
        return {k: resolve_argument_placeholders(v, previous_results, tool_calls) for k, v in arg.items()}
    else:
        return arg


def process_example(example_path: str, tool_functions: Dict[str, Callable]) -> Dict[str, Any]:
    with open(example_path, "r") as f:
        example = json.load(f)

    query = example["query"]
    tool_calls = example["calls"]

    previous_results = []
    actual_tool_trace = []

    for step in tool_calls:
        tool_name = step["name"]
        raw_args = step["arguments"]
        resolved_args = resolve_argument_placeholders(raw_args, previous_results, tool_calls)

        if tool_name not in tool_functions:
            raise ValueError(f"Tool '{tool_name}' is not implemented.")

        result = tool_functions[tool_name].func(**resolved_args)
        previous_results.append(result["data"])

        actual_tool_trace.append({
            "tool_name": tool_name,
            "arguments": resolved_args,
            "result": result
        })

    output = ""
    if isinstance(previous_results[-1], list):
        output += "Here is the list: \n\n"
        for i, result in enumerate(previous_results[-1]):
            output += f"{i + 1}. \n"
            output += "\n".join([f"{k}: {v}" for k, v in result.items()])

    elif isinstance(previous_results[-1], dict):
        output += "\n".join(f"{k}: {v}" for k, v in previous_results[-1].items())

    else:
        output = previous_results[-1]

    return {
        "query": query,
        "output": output,
        "tool_calls": actual_tool_trace
    }

def save_as_json(data: list, output_path: str, prefix: str = "example"):
    """
    Save a list of dicts into a single JSON file, keyed by example name.

    Args:
        data (list): List of examples (dicts).
        output_path (str): Path to save the JSON file.
        prefix (str): Prefix for the keys (default: "example").
    """
    indexed_data = {f"{prefix}_{i}": entry for i, entry in enumerate(data)}

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(indexed_data, f, indent=4, ensure_ascii=False)


def process_folder(folder_path: str, output_path: str):
    """
    Process all JSON files inside a folder and save aggregated results.
    """
    result_rows = []

    if not os.path.isdir(folder_path):
        print(f"⚠️ Skipping missing folder {folder_path}")
        return

    for fname in sorted(os.listdir(folder_path)):
        if "filtering" in fname or "vector_store_search" in fname:
            continue
        if fname.endswith(".json"):
            file_path = os.path.join(folder_path, fname)
            print(f"\n\n --- \n\nProcessing {file_path}")
            result = process_example(file_path, tool_functions)
            result_rows.append(result)

    save_as_json(result_rows, output_path)
    print(f"✅ Evaluation data written to {output_path}")


def main(input_folder: str):
    # We only care about recommendation and statistics
    domains = ["recommendation", "statistics"]
    variants = ["standard", "semantic"]

    for domain in domains:
        for variant in variants:
            folder_path = os.path.join(input_folder, domain, variant)
            output_path = f"./tests/by_type/evaluation_{domain}_{variant}.json"
            process_folder(folder_path, output_path)


if __name__ == "__main__":
    input_folder = f"./src/examples/by_type"
    main(input_folder=input_folder)
