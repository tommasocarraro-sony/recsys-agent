from langchain.tools import tool
import json
import numpy as np
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


from typing import List, Optional, Literal
from pydantic import BaseModel, Field

AllowedGroups = Literal['kid', 'teenager', 'young_adult', 'adult', 'senior', 'male', 'female']
AllowedPopularity = Literal["standard", "by_user_group"]

class GetPopularItemsInput(BaseModel):
    popularity: AllowedPopularity = Field(
        ...,
        description="Whether to compute standard popularity or by user group."
    )
    k: int = Field(
        default=20,
        description="Number of popular items to be returned."
    )
    items: List[int] = Field(
        default_factory=list,
        description="List of item ID(s) for which the popularity has to be computed."
    )
    user_group: List[AllowedGroups] = Field(
        default_factory=list,
        description="User groups for computing popularity: 'kid', 'teenager', 'young_adult', 'adult', 'senior', 'male', "
                    "'female'."
    )


@tool(args_schema=GetPopularItemsInput)
def get_popular_items_tool(popularity: AllowedPopularity, k: int = 20, items: Optional[List[int]] = None,
                           user_group: Optional[List[AllowedGroups]] = None) -> str:
    """
    Returns the IDs of the k most popular items based on the number of ratings they received. If a list of item IDs is
    given, the popularity computation will be restricted to those items only.
    The popularity can optionally be computed based on a user group.
    """
    print(f"\n{get_time()} - get_popular_items has been triggered!!!\n")

    if popularity is None or k is None:
        return json.dumps(JSON_GENERATION_ERROR)

    # SQL query building
    if popularity == "standard":
        if items:
            items = [int(i) for i in items]
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id", "n_ratings"], "items": items})
        else:
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id", "n_ratings"]})
    else:
        if not user_group:
            return json.dumps(JSON_GENERATION_ERROR)
        user_group_cols = [f"n_ratings_{group}" for group in user_group]
        if items:
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

        if len(item_ids) > k:
            item_ids = item_ids[:k]

        print(f"\n{get_time()} - Returned list: {item_ids}\n")

        return json.dumps({
            "status": "success",
            "message": f"The IDs of the {len(item_ids)} most popular items are returned.",
            "data": item_ids
        })
    else:
        return json.dumps({
            "status": "failure",
            "message": "The SQL query did not produce any result",
            "data": None
        })
