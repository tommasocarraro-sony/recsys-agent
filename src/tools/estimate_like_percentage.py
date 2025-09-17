from typing import List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from langchain.tools import tool

from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time, read_ml100k_ratings


class EstimateLikePercentageInput(BaseModel):
    item_ids: List[int] = Field(
        ...,
        description="List of items for percentage estimation."
    )


def estimate_like_percentage(item_ids: List[int]) -> dict:
    """
    Estimates the percentage of users that like the given items.
    """
    print(f"\n{get_time()} - estimate_like_percentage(item_ids={item_ids})\n")

    if item_ids is None:
        return JSON_GENERATION_ERROR

    if not item_ids:
        return {
            "status": "failure",
            "message": "The given list of items is empty.",
            "data": None
        }

    items = [int(i) for i in item_ids]
    # Load rating file
    user_interactions = read_ml100k_ratings()
    n_users = len(set(int(inter[0]) for inter in user_interactions))
    n_users_by_items = len(set(int(inter[0]) for inter in user_interactions if inter[1] in items))
    perc = n_users_by_items / n_users * 100

    print(f"\n{get_time()} - Returned percentage: {perc:.2f}%\n")

    return {
        "status": "success",
        "message": "The percentage of users that might like the given items is returned.",
        "data": f"{perc:.2f}%"
    }

estimate_like_percentage_tool = StructuredTool.from_function(
    func=estimate_like_percentage,
    args_schema=EstimateLikePercentageInput,
    handle_tool_errors=True
)
