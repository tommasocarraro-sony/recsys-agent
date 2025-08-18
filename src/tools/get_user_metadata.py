from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


AllowedFeatures = Literal["age_category", "gender"]

class GetUserMetadataInput(BaseModel):
    """Schema for retrieving user metadata."""
    user: int = Field(..., description="User ID.")
    get: List[AllowedFeatures] = Field(
        ...,
        description='List of user metadata features to be retrieved. Available features are: "age_category", "gender".'
    )


@tool(args_schema=GetUserMetadataInput)
def get_user_metadata_tool(user: int, get: List[AllowedFeatures]) -> dict:
    """
    Returns the requested user metadata given the user ID.
    """
    print(f"\n{get_time()} - get_user_metadata_tool(user={user}, get={get})\n")

    if user is None or get is None:
        return JSON_GENERATION_ERROR

    specification = get

    sql_query, _, _ = define_sql_query("users", {"user": user, "specification": specification})
    result = execute_sql_query(sql_query)

    if result:
        return_dict = {}
        for i, spec in enumerate(specification):
            return_dict[spec] = result[0][i] if result[0][i] is not None else 'unknown'

        print(f"\n{get_time()} - Returned dictionary: {return_dict}\n")

        return {
            "status": "success",
            "message": f"The requested metadata for user {user} is returned.",
            "data": return_dict
        }
    else:
        return {
            "status": "failure",
            "message": f"No information found for user {user}.",
            "data": None
        }
