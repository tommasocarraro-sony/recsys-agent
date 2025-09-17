from typing import List, Union, Dict, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool, StructuredTool

from src.tools.config import TOOL_PRINTS
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


AllowedFeatures = Literal[
    "title", "description", "genres", "director", "producer", "duration",
    "release_date", "release_month", "country", "actors", "imdb_rating", "storyline"
]

class GetItemInfoInput(BaseModel):
    """Schema for retrieving item metadata."""
    item_ids: List[int] = Field(
        ...,
        description=(
            "List of items for which information has to be retrieved."
        )
    )
    attributes: List[AllowedFeatures] = Field(
        default_factory=lambda: ['title', 'genres', 'description'],
        description='List of attributes to retrieve. Available attributes are: '
                    '"title", "description", "genres", "director", "producer", "duration", '
                    '"release_date", "release_month", "country", "actors", "imdb_rating", '
                    '"storyline". By default, title, genres, and description are retrieved.'
    )


def get_item_info(item_ids: List[int], attributes: List[AllowedFeatures]) -> dict:
    """
    Returns the requested information of the given items.
    """
    if TOOL_PRINTS:
        print(f"\n{get_time()} - get_item_info(item_ids={item_ids}, attributes={attributes})\n")

    if item_ids is None or attributes is None:
        return JSON_GENERATION_ERROR

    specification = ["item_id"] + attributes

    if not item_ids:
        return {
            "status": "failure",
            "message": "The given list of item IDs is empty.",
            "data": None
        }

    sql_query, _, _ = define_sql_query("items", {"items": item_ids, "specification": specification})
    result = execute_sql_query(sql_query)

    if result:
        return_list = []
        for j in range(len(result)):
            current_dict = {}
            for i, spec in enumerate(specification):
                current_dict[spec] = result[j][i] if result[j][i] is not None else 'unknown'
            return_list.append(current_dict)

        if TOOL_PRINTS:
            print(f"\n{get_time()} - Returned list: {return_list}\n")

        return {
            "status": "success",
            "message": "The requested attributes for the given items are returned.",
            "data": return_list
        }
    else:
        return {
            "status": "failure",
            "message": f"No information found for the given items: {item_ids}.",
            "data": None
        }

get_item_info_tool = StructuredTool.from_function(
    func=get_item_info,
    args_schema=GetItemInfoInput,
    handle_tool_errors=True
)

