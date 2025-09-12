from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


AllowedFeatures = Literal["age_category", "gender"]

class GetUserInfoInput(BaseModel):
    """Schema for retrieving user metadata."""
    user_id: int = Field(..., description="User ID of the user for which information is requested.")
    attributes: List[AllowedFeatures] = Field(
        ...,
        description='List of attributes to be retrieved. Available attributes are: "age_category", "gender".'
    )


@tool(args_schema=GetUserInfoInput)
def get_user_info(user_id: int, attributes: List[AllowedFeatures]) -> dict:
    """
    Returns the requested information of the given user.
    """
    print(f"\n{get_time()} - get_user_info(user_id={user_id}, attributes={attributes})\n")

    if user_id is None or attributes is None:
        return JSON_GENERATION_ERROR

    specification = attributes

    sql_query, _, _ = define_sql_query("users", {"user": user_id, "specification": specification})
    result = execute_sql_query(sql_query)

    if result:
        return_dict = {}
        for i, spec in enumerate(specification):
            return_dict[spec] = result[0][i] if result[0][i] is not None else 'unknown'

        print(f"\n{get_time()} - Returned dictionary: {return_dict}\n")

        return {
            "status": "success",
            "message": f"The requested attributes for user {user_id} are returned.",
            "data": return_dict
        }
    else:
        return {
            "status": "failure",
            "message": f"No information found for user {user_id}.",
            "data": None
        }
