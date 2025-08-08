import json
from typing import List
from pydantic import BaseModel, Field
from langchain.tools import tool

from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time, read_ml100k_ratings


class GetLikePercentageInput(BaseModel):
    items: List[int] = Field(
        ...,
        description="A list of item IDs."
    )


@tool(args_schema=GetLikePercentageInput)
def get_like_percentage_tool(items: List[int]) -> str:
    """
    Returns the percentage of users that like the given item IDs.
    """
    print(f"\n{get_time()} - get_like_percentage has been triggered!!!\n")

    if items is None:
        return json.dumps(JSON_GENERATION_ERROR)

    if not items:
        return json.dumps({
            "status": "failure",
            "message": "The given list of item IDs is empty.",
            "data": None
        })

    items = [int(i) for i in items]
    # Load rating file
    user_interactions = read_ml100k_ratings()
    n_users = len(set(int(inter[0]) for inter in user_interactions))
    n_users_by_items = len(set(int(inter[0]) for inter in user_interactions if inter[1] in items))
    perc = n_users_by_items / n_users * 100

    print(f"\n{get_time()} - Returned percentage: {perc:.2f}%\n")

    return json.dumps({
        "status": "success",
        "message": "The percentage of users that might like the given items is returned.",
        "data": f"{perc:.2f}%"
    })
