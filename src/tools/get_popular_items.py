from langchain.tools import tool
import json
import numpy as np
from src.tools.utils import execute_sql_query, define_sql_query, convert_to_list
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


from typing import List, Union, Optional, Literal
from pydantic import BaseModel, Field

class GetPopularItemsInput(BaseModel):
    items: Optional[Union[List[int], str]] = Field(
        default=None,
        description="Item ID(s) for which the popularity has to be computed, either directly as a list or as a path to a JSON file."
    )
    popularity: Literal["standard", "by_user_group"] = Field(
        ...,
        description="Whether to compute standard popularity or by user group."
    )
    user_group: Optional[List[str]] = Field(
        default=None,
        description="User groups for computing popularity: 'kid', 'teenager', 'young_adult', 'adult', 'senior', 'male', 'female'."
    )
    get: Literal["all", "top3"] = Field(
        ...,
        description="Whether to return all the popular items or just the top 3."
    )

@tool
def get_popular_items_tool(input: GetPopularItemsInput) -> str:
    """
    Returns the IDs of the popular items based on ratings, optionally filtered by user group (i.e., age category) and
    capped to top 3 popular items if requested.
    """
    print(f"\n{get_time()} - get_popular_items has been triggered!!!\n")

    try:
        popularity = input.popularity
        get_type = input.get
        items = input.items
        user_group = input.user_group
    except Exception:
        return json.dumps(JSON_GENERATION_ERROR)

    # SQL query building
    if popularity == "standard":
        if items:
            try:
                items = convert_to_list(items)
            except Exception:
                return json.dumps({
                    "status": "failure",
                    "message": "There are issues with the temporary file containing the "
                               "item IDs.",
                })
            items = [int(i) for i in items]
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id", "n_ratings"], "items": items})
        else:
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id", "n_ratings"]})
    else:
        if not user_group:
            return json.dumps(JSON_GENERATION_ERROR)
        user_group_cols = [f"n_ratings_{group}" for group in user_group]
        if items:
            try:
                items = convert_to_list(items)
            except Exception:
                return json.dumps({
                    "status": "failure",
                    "message": "There are issues with the temporary file containing the "
                               "item IDs.",
                })
            items = [int(i) for i in items]
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id"] + user_group_cols, "items": items})
        else:
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id"] + user_group_cols})

    # Execute and process result
    if sql_query:
        result = execute_sql_query(sql_query)
        ids_with_count = [(str(row[0]), sum(row[1:])) for row in result]
        ids_with_count_sorted = sorted(ids_with_count, key=lambda x: x[1], reverse=True)

        q75 = np.quantile([count for _, count in ids_with_count_sorted], 0.75)
        item_ids = [item_id for item_id, count in ids_with_count_sorted if count > q75]

        filtered = False
        if get_type == "top3":
            item_ids = item_ids[:3]
        elif len(item_ids) > 20:
            item_ids = item_ids[:20]
            filtered = True

        return json.dumps({
            "status": "success",
            "message": (
                f"These are the IDs of the {len(item_ids)} most popular items: {item_ids}. "
                f"{'Explain the user that more than 20 popular items were retrieved by the tool. However, to avoid verbosity and for efficient use of tokens, the IDs of the 20 most popular items are generated.' if filtered else ''}"
            )
        })
    else:
        return json.dumps({
            "status": "failure",
            "message": "The SQL query did not produce any result"
        })