from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import List, Union
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


class GetInteractedItemsInput(BaseModel):
    """Schema for retrieving items a user has interacted with."""
    user: int = Field(..., description="User ID.")


@tool(args_schema=GetInteractedItemsInput)
def get_interacted_items_tool(user: int) -> dict:
    """
    Retrieves the list of the twenty most recent items a user has previously interacted with.
    """
    print(f"\n{get_time()} - get_interacted_items_tool has been triggered!!!\n")

    if user is None:
        return JSON_GENERATION_ERROR

    # Define SQL query to get interacted items for user
    sql_query, _, _ = define_sql_query("interactions", {"user": user})
    result = execute_sql_query(sql_query)

    if not result or not result[0] or not result[0][0]:
        return {
            "status": "failure",
            "message": f"No interaction information found for user {user}.",
            "data": None
        }

    # Extract interacted item IDs from query result
    interacted_items = result[0][0].split(",")

    # Limit to most recent 20 if more than 20 interactions
    if len(interacted_items) > 20:
        interacted_items = interacted_items[-20:]
        message = f"User {user} has interacted with more than 20 items. The most recent 20 are returned."
    else:
        message = f"All items user {user} interacted with are returned."

    print(f"\n{get_time()} - Returned list: {interacted_items}\n")

    return {
        "status": "success",
        "message": message,
        "data": interacted_items
    }


def get_interacted_items_list(input: GetInteractedItemsInput) -> Union[List[int], None]:
    """
    Tool to retrieve the list of items a user has previously interacted with,
    returning detailed metadata for those items.
    """
    print(f"\n{get_time()} - get_interacted_items_list has been triggered!!!\n")
    try:
        user = input["user"]
    except Exception:
        return None

    # Define SQL query to get interacted items for user
    sql_query, _, _ = define_sql_query("interactions", {"user": user})
    result = execute_sql_query(sql_query)

    # Extract interacted item IDs from query result
    if result:
        return result[0][0].split(",")
    else:
        return None
