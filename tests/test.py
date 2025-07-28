import json
import csv
import os
from typing import Dict, Any, List, Callable
from src.tools.get_like_percentage import get_like_percentage_tool
from src.tools.item_filter import item_filter_tool
from src.tools.get_popular_items import get_popular_items_tool
from src.tools.get_item_metadata import get_item_metadata_tool
from src.tools.get_top_k_recommendations import get_top_k_recommendations_tool, create_recbole_environment
from src.tools.get_user_metadata import get_user_metadata_tool
from src.tools.vector_store_search import vector_store_search_tool
from src.tools.get_interacted_items import get_interacted_items_tool
from src.tools.utils import create_lists_for_fuzzy_matching

create_lists_for_fuzzy_matching()
create_recbole_environment(os.getenv("RECSYS_MODEL_PATH"))

tool_functions = {
    "item_filter_tool": item_filter_tool,
    "get_top_k_recommendations_tool": get_top_k_recommendations_tool,
    "get_item_metadata_tool": get_item_metadata_tool,
    "get_user_metadata_tool": get_user_metadata_tool,
    "get_like_percentage_tool": get_like_percentage_tool,
    "get_popular_items_tool": get_popular_items_tool,
    "vector_store_search_tool": vector_store_search_tool,
    "get_interacted_items_tool": get_interacted_items_tool
}


def resolve_argument_placeholders(arg, previous_results):
    """Recursively resolve <...> placeholders in the arguments."""
    if isinstance(arg, str):
        if arg.startswith("<") and arg.endswith(">"):
            if isinstance(previous_results[-1], dict):
                if "age_category" in previous_results[-1]:
                    return [previous_results[-1]["age_category"].replace(" ", "_")]
                if "gender" in previous_results[-1]:
                    return [previous_results[-1]["gender"]]
            if isinstance(previous_results[-1], list):
                if "description" in previous_results[-1][0]:
                    return previous_results[-1][0]["description"]
            return previous_results[-1]  # Use last tool result
        else:
            return arg
    elif isinstance(arg, list):
        return [resolve_argument_placeholders(a, previous_results) for a in arg]
    elif isinstance(arg, dict):
        return {k: resolve_argument_placeholders(v, previous_results) for k, v in arg.items()}
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
        resolved_args = resolve_argument_placeholders(raw_args, previous_results)

        if tool_name not in tool_functions:
            raise ValueError(f"Tool '{tool_name}' is not implemented.")

        result = json.loads(tool_functions[tool_name].func(**resolved_args))
        previous_results.append(result["data"])

        actual_tool_trace.append({
            "tool_name": tool_name,
            "arguments": resolved_args,
            "result": result
        })

    return {
        "query": query,
        "output": previous_results[-1],
        "tool_calls": actual_tool_trace
    }


def write_to_csv(results: List[Dict[str, Any]], out_path: str):
    keys = ["query", "output", "tool_calls"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "query": r["query"],
                "output": json.dumps(r["output"], ensure_ascii=False),
                "tool_calls": json.dumps(r["tool_calls"], ensure_ascii=False)
            })


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


def main(input_folder: str, output_file: str):
    result_rows = []
    for fname in sorted(os.listdir(input_folder)):
        if "filtering" not in fname:
            if fname.endswith(".json"):
                print(f"\n\n --- \n\nProcessing {fname}")
                path = os.path.join(input_folder, fname)
                result = process_example(path, tool_functions)
                result_rows.append(result)
    write_to_csv(result_rows, output_file + ".csv")
    save_as_json(result_rows, output_file + ".json")
    print(f"✅ Evaluation data written to {output_file}")


if __name__ == "__main__":
    main(input_folder="./src/examples", output_file="./tests/evaluation_output")