import json
from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


class GetUserMetadataInput(BaseModel):
    """Schema for retrieving user metadata."""
    user: int = Field(..., description="User ID.")
    get: List[str] = Field(
        ...,
        description='List of user metadata features to be retrieved. Available features are: "age_category", "gender".'
    )


@tool
def get_user_metadata_tool(input: GetUserMetadataInput) -> str:
    """
    Returns the requested user metadata given the user ID.
    """
    print(f"\n{get_time()} - get_user_metadata_tool has been triggered!!!\n")

    try:
        user = input.user
        specification = input.get
    except Exception:
        return json.dumps(JSON_GENERATION_ERROR)
    sql_query, _, _ = define_sql_query("users", {"user": user, "specification": specification})
    result = execute_sql_query(sql_query)

    if result:
        return_dict = {}
        for i, spec in enumerate(specification):
            return_dict[spec] = result[0][i] if result[0][i] is not None else 'unknown'

        return json.dumps({
            "status": "success",
            "message": f"This is the requested metadata for user {user}",
            "data": return_dict
        })
    else:
        return json.dumps({
            "status": "failure",
            "message": f"No information found for user {user}.",
        })