import json
from typing import List, Union
from pydantic import BaseModel, Field, root_validator
from langchain.tools import tool

from src.constants import JSON_GENERATION_ERROR
from src.tools.utils import convert_to_list
from src.utils import get_time, read_ml100k_ratings


class GetLikePercentageInput(BaseModel):
    items: Union[List[int], str] = Field(
        ...,
        description="A list of item IDs or a path to a JSON file containing them."
    )


@tool(args_schema=GetLikePercentageInput)
def get_like_percentage_tool(items: Union[List[int], str]) -> str:
    """
    Returns the percentage of users that like the given item IDs.
    """
    print(f"\n{get_time()} - get_like_percentage has been triggered!!!\n")

    if items is None:
        return json.dumps(JSON_GENERATION_ERROR)

    try:
        items = convert_to_list(items)
    except Exception:
        return json.dumps({
            "status": "failure",
            "message": "There are issues with the temporary file containing the item IDs.",
        })


    items = [int(i) for i in items]
    # Load rating file
    user_interactions = read_ml100k_ratings()
    n_users = len(set(int(inter[0]) for inter in user_interactions))
    n_users_by_items = len(set(int(inter[0]) for inter in user_interactions if inter[1] in items))
    perc = n_users_by_items / n_users * 100

    return json.dumps({
        "status": "success",
        "message": "This is the percentage of users that might like the given items.",
        "data": f"{perc:.2f}%"
    })
