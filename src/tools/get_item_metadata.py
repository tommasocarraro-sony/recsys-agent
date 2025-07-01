import json
from typing import List, Union, Dict, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from src.tools.utils import execute_sql_query, define_sql_query, convert_to_list
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


AllowedFeatures = Literal[
    "title", "description", "genres", "director", "producer", "duration",
    "release_date", "release_month", "country", "actors", "imdb_rating", "storyline"
]

class GetItemMetadataInput(BaseModel):
    """Schema for retrieving item metadata."""
    items: Union[List[int], str] = Field(
        ...,
        description=(
            "Item ID(s) for which the metadata has to be retrieved, either as a list of integers "
            "or as a path to a JSON file containing the item IDs."
        )
    )
    get: List[AllowedFeatures] = Field(
        ...,
        description='List of item metadata features to retrieve. Available features: '
                    '"title", "description", "genres", "director", "producer", "duration", '
                    '"release_date", "release_month", "country", "actors", "imdb_rating", '
                    '"storyline".'
    )


@tool(args_schema=GetItemMetadataInput)
def get_item_metadata_tool(items: Union[List[int], str], get: List[AllowedFeatures]) -> str:
    """
    Returns the requested item metadata given the item ID(s).
    """
    print(f"\n{get_time()} - get_item_metadata_tool has been triggered!!!\n")

    if items is None or get is None:
        return json.dumps(JSON_GENERATION_ERROR)

    specification = ["item_id"] + get

    try:
        items = convert_to_list(items)
    except Exception:
        return json.dumps({
            "status": "failure",
            "message": "There are issues with the temporary file containing the item IDs.",
        })

    sql_query, _, _ = define_sql_query("items", {"items": items, "specification": specification})
    result = execute_sql_query(sql_query)

    if result:
        return_dict = {}
        for j in range(len(result)):
            return_dict[result[j][0]] = {}
            for i, spec in enumerate(specification):
                if spec != "item_id":
                    return_dict[result[j][0]][spec] = result[j][i] if result[j][i] is not None else 'unknown'

        print(f"\n{get_time()} - Returned dictionary: {return_dict}\n")

        return json.dumps({
            "status": "success",
            "message": "The requested metadata for the given item IDs is returned.",
            "data": return_dict
        })
    else:
        return json.dumps({
            "status": "failure",
            "message": f"No information found for the given items: {items}.",
        })


def get_item_metadata_dict(input: GetItemMetadataInput) -> Union[Dict[int, Dict[str, str]], None]:
    """
    Helper function to retrieve item metadata and return it as a dictionary instead of JSON string.

    :param input: Pydantic input model with 'items' and 'get' keys
    :return: Dictionary {item_id: {field: value}} or None if nothing is found
    """
    print(f"\n{get_time()} - get_item_metadata_dict has been triggered!!!\n")

    try:
        items = convert_to_list(input['items'])
    except Exception:
        return None

    specification = input['get']
    sql_query, _, _ = define_sql_query("items", {"items": items, "specification": specification})
    result = execute_sql_query(sql_query)

    if result:
        r_dict = {}
        for j in range(len(result)):
            item_id = result[j][0]
            r_dict[item_id] = {}
            for i, spec in enumerate(specification):
                r_dict[item_id][spec] = result[j][i] if result[j][i] is not None else "unknown"
        return r_dict
    else:
        return None