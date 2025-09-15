from langchain.tools import tool
import numpy as np
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


from typing import List, Optional, Literal
from pydantic import BaseModel, Field

AllowedGroups = Literal['kid', 'teenager', 'young_adult', 'adult', 'senior', 'male', 'female']

class GetPopularItemsInput(BaseModel):
    k: Literal[3, 20] = Field(
        default=3,
        description="Number of popular items to be returned. Use 3 when popularity is requested in the context of statistics queries (e.g., best genre, ideal duration). Use 20 when popularity is requested in the context of recommendation queries."
    )
    item_ids: List[int] = Field(
        default_factory=list,
        description="Optional List of item ID(s) for which the popularity has to be computed. If provided, popularity computation is restricted to these items."
    )
    user_group: List[AllowedGroups] = Field(
        default_factory=list,
        description="Optional list of user groups for computing popularity. Available groups are: 'kid', 'teenager', 'young_adult', 'adult', 'senior', 'male', "
                    "'female'. If provided, popularity is based only on the items liked by users in these groups."
    )


@tool(args_schema=GetPopularItemsInput)
def filter_items_by_popularity(k: Literal[3, 20] = 3, item_ids: Optional[List[int]] = None,
                                user_group: Optional[List[AllowedGroups]] = None) -> dict:
    """
    Filters items by their popularity (i.e., number of ratings).
    """
    print(f"\n{get_time()} - filter_items_by_popularity(k={k}, item_ids={item_ids}, user_group={user_group})\n")

    if k is None:
        return JSON_GENERATION_ERROR

    # SQL query building
    if not user_group:
        if item_ids:
            items = [int(i) for i in item_ids]
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id", "n_ratings"], "items": items})
        else:
            sql_query, _, _ = define_sql_query("items", {"select": ["item_id", "n_ratings"]})
    else:
        user_group_cols = [f"n_ratings_{group}" for group in user_group]
        if item_ids:
            items = [int(i) for i in item_ids]
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

        return {
            "status": "success",
            "message": f"The IDs of the {len(item_ids)} most popular items are returned.",
            "data": item_ids
        }
    else:
        return {
            "status": "failure",
            "message": "The SQL query did not produce any result",
            "data": None
        }
