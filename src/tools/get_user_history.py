from pydantic import BaseModel, Field
from langchain_core.tools import tool, StructuredTool
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


class GetUserHistoryInput(BaseModel):
    """Schema for retrieving the history of a user."""
    user_id: int = Field(..., description="User ID for which the history is requested.")


def get_user_history(user_id: int) -> dict:
    """
    Returns the history of a user.
    """
    print(f"\n{get_time()} - get_user_history(user_id={user_id})\n")

    if user_id is None:
        return JSON_GENERATION_ERROR

    # Define SQL query to get interacted items for user
    sql_query, _, _ = define_sql_query("interactions", {"user": user_id})
    result = execute_sql_query(sql_query)

    if not result or not result[0] or not result[0][0]:
        return {
            "status": "failure",
            "message": f"No history found for user {user_id}.",
            "data": None
        }

    # Extract interacted item IDs from query result
    interacted_items = result[0][0].split(",")

    # Limit to most recent 20 if more than 20 interactions
    if len(interacted_items) > 20:
        interacted_items = interacted_items[-20:]

    print(f"\n{get_time()} - Returned list: {interacted_items}\n")

    return {
        "status": "success",
        "message": f"The IDs of the {len(interacted_items)} most recent items user {user_id} interacted with are returned.",
        "data": interacted_items
    }

get_user_history_tool = StructuredTool.from_function(
    func=get_user_history,
    args_schema=GetUserHistoryInput,
    handle_tool_errors=True
)

