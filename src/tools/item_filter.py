import os
import json
import hashlib
from typing import List, Optional, Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


# Pydantic schemas

class ComparisonFilter(BaseModel):
    request: Literal["higher", "lower", "exact"]
    threshold: int


class FiltersSchema(BaseModel):
    actors: Optional[List[str]] = Field(default=None, description="List of actor names to filter by.")
    genres: Optional[List[str]] = Field(default=None, description="List of movie genres to filter by.")
    director: Optional[List[str]] = Field(default=None, description="List of director names to filter by.")
    producer: Optional[List[str]] = Field(default=None, description="List of producer names to filter by.")
    imdb_rating: Optional[ComparisonFilter] = None
    duration: Optional[ComparisonFilter] = None
    release_date: Optional[ComparisonFilter] = None
    release_month: Optional[int] = Field(default=None, description="Release month in MM format.")
    country: Optional[str] = Field(default=None, description="Country of origin.")


class ItemFilterInput(BaseModel):
    filters: FiltersSchema


# LangChain-compatible tool
@tool("item_filter", args_schema=ItemFilterInput)
def item_filter_tool(filters: ItemFilterInput) -> str:
    """
    Returns the path to a temporary file containing the IDs of the items that satisfy the given conditions.
    """
    print(f"\n{get_time()} - item_filter has been triggered!!!\n")

    matched = False
    filters = filters.dict(exclude_none=True)
    sql_query, corrections, failed_corrections = define_sql_query("items", filters)
    mess = ""

    if sql_query is not None:
        result = execute_sql_query(sql_query)
        item_ids = [str(row[0]) for row in result]

        if item_ids:
            # Hash-based filename
            hash_input = ','.join(item_ids).encode('utf-8')
            filename_hash = hashlib.md5(hash_input).hexdigest()
            file_path = f"./temp/{filename_hash}.json"

            # Save item IDs to file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                json.dump({"items": item_ids}, f)

            print(f"Saved item IDs to {file_path}")
            mess = (
                f"The IDs of the items satisfying the given conditions have been saved to this file path: {file_path}. "
                f"You can now proceed to the next step. It is enough you pass this path to the \"items\" parameter of the next tool call."
            )
            matched = True

    # Construct the message for LLM
    failed_corr_text = (
        f"Note that corrections for these fields have been tried but failed: {failed_corrections}, "
        f"so the final recommendation output will not take the failed filters into consideration."
        if failed_corrections else ""
    )

    correction_text = (
        f"Note that the following corrections have been made to retrieve the items: {corrections}. "
        f"Please, remember to explain the user these corrections. {failed_corr_text}"
        if corrections else ""
    )

    no_match_text = (
        "Unfortunately, the given conditions did not match any item in the database, so it is not possible to proceed with the next step. "
        "You do not have to perform other tool calls."
        if not matched else mess
    )

    if matched or corrections or failed_corrections:
        return json.dumps({
            "status": "success",
            "message": correction_text + no_match_text
        })

    return json.dumps(JSON_GENERATION_ERROR)