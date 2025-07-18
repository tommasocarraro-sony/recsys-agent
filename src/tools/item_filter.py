import os
import json
import hashlib
from typing import List, Optional, Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from src.tools.utils import execute_sql_query, define_sql_query
from src.constants import JSON_GENERATION_ERROR
from src.utils import get_time


AllowedComparison = Literal["higher", "lower", "exact"]

class ComparisonFilter(BaseModel):
    """
    Comparison filter for numeric fields.
    Must be a dict object with:
      - request: one of 'higher', 'lower', 'exact'
      - threshold: an integer
    """
    request: AllowedComparison = Field(
        ..., description='Type of comparison: "higher", "lower", or "exact".'
    )
    threshold: int = Field(
        ..., description="Numeric threshold to compare against (e.g., rating > 7)."
    )


class ItemFilterInput(BaseModel):
    actors: Optional[List[str]] = Field(default=None, description="List of actor names to filter by.")
    genres: Optional[List[str]] = Field(default=None, description="List of movie genres to filter by.")
    director: Optional[List[str]] = Field(default=None, description="List of director names to filter by.")
    producer: Optional[List[str]] = Field(default=None, description="List of producer names to filter by.")
    imdb_rating: Optional[ComparisonFilter] = Field(
        default=None, description="IMDb rating filter using a comparison (e.g., higher/lower than 7) or exact rating."
                                  "Must be an object "
        "with fields `request` ('higher' | 'lower' | 'exact') and "
        "`threshold` (integer)."
    )
    duration: Optional[ComparisonFilter] = Field(
        default=None, description="Duration filter in minutes using a comparison (e.g., less/more than 120) or "
                                  "exact duration."
                                  "Must be an object "
        "with fields `request` ('higher' | 'lower' | 'exact') and "
        "`threshold` (integer)."
    )
    release_date: Optional[ComparisonFilter] = Field(
        default=None, description="Release year filter using a comparison (e.g., after/prior to 2000) or exact release "
                                  "year."
                                  "Must be an object "
        "with fields `request` ('higher' | 'lower' | 'exact') and "
        "`threshold` (integer)."
    )
    release_month: Optional[int] = Field(default=None, description="Release month in MM format to filter by.")
    country: Optional[str] = Field(default=None, description="Country of origin to filter by.")


# LangChain-compatible tool
@tool(args_schema=ItemFilterInput)
def item_filter_tool(actors: Optional[List[str]] = None, genres: Optional[List[str]] = None,
                     director: Optional[List[str]] = None, producer: Optional[List[str]] = None,
                     imdb_rating: Optional[ComparisonFilter] = None, duration: Optional[ComparisonFilter] = None,
                     release_date: Optional[ComparisonFilter] = None, release_month: Optional[int] = None,
                     country: Optional[int] = None) -> str:
    """
    Returns the path to a temporary file containing the IDs of the items that satisfy the given conditions.
    """
    print(f"\n{get_time()} - item_filter has been triggered!!!\n")

    matched = False

    # Build the filters dict
    filters = {
        key: value
        for key, value in {
            "actors": actors,
            "genres": genres,
            "director": director,
            "producer": producer,
            "imdb_rating": {"request": imdb_rating.request, "threshold": imdb_rating.threshold} if imdb_rating else None,
            "duration": {"request": duration.request, "threshold": duration.threshold} if duration else None,
            "release_date": {"request": release_date.request, "threshold": release_date.threshold} if release_date else None,
            "release_month": release_month,
            "country": country,
        }.items()
        if value is not None
    }

    if not filters:
        return json.dumps(JSON_GENERATION_ERROR)

    sql_query, corrections, failed_corrections = define_sql_query("items", filters)
    mess = ""
    file_path = None

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
                "The IDs of the items satisfying the given conditions have been saved to the returned file path."
                "If another tool call is needed, you can now proceed to the next tool call. It is enough you pass "
                "this path to the \"items\" parameter of the next tool call."
            )
            matched = True

    # Construct the message for LLM
    failed_corr_text = (
        f"Note that corrections for these user conditions have been tried but failed: {failed_corrections}, "
        f"so the final recommendation output will not take the failed conditions into consideration."
        if failed_corrections else ""
    )

    correction_text = (
        f"Note that, in order to retrieve the items, the following corrections on the user conditions have been made: {corrections}. {failed_corr_text}"
        if corrections else ""
    )

    no_match_text = (
        "Unfortunately, the given conditions did not match any item in the database, so it is not possible to proceed "
        "with the next step. You do not have to perform other tool calls."
        if not matched else mess
    )

    if matched or corrections or failed_corrections:

        print(f"\n{get_time()} - Returned path {file_path}\n")

        return json.dumps({
            "status": "success",
            "message": correction_text + no_match_text,
            "data": file_path if matched else None,
        })

    return json.dumps(JSON_GENERATION_ERROR)