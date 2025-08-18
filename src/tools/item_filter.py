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
        default="higher", description='Type of comparison: "higher", "lower", or "exact".'
    )
    threshold: int = Field(
        default=0, description="Numeric threshold to compare against (e.g., rating > 7 or duration > 90)."
    )


class ItemFilterInput(BaseModel):
    actors: List[str] = Field(default_factory=list, description="List of actor names to filter by.")
    genres: List[str] = Field(default_factory=list, description="List of movie genres to filter by.")
    director: List[str] = Field(default_factory=list, description="List of director names to filter by.")
    producer: List[str] = Field(default_factory=list, description="List of producer names to filter by.")
    imdb_rating: ComparisonFilter = Field(
        default_factory=lambda: ComparisonFilter(request="higher", threshold=0), description="IMDb rating filter using a comparison (e.g., higher/lower than 7) or exact rating."
                                  "Must be an object "
        "with fields `request` ('higher' | 'lower' | 'exact') and "
        "`threshold` (integer)."
    )
    duration: ComparisonFilter = Field(
        default_factory=lambda: ComparisonFilter(request="higher", threshold=0), description="Duration filter in minutes using a comparison (e.g., less/more than 120) or "
                                  "exact duration."
                                  "Must be an object "
        "with fields `request` ('higher' | 'lower' | 'exact') and "
        "`threshold` (integer)."
    )
    release_date: ComparisonFilter = Field(
        default_factory=lambda: ComparisonFilter(request="higher", threshold=0), description="Release year filter using a comparison (e.g., after/prior to 2000) or exact release "
                                  "year."
                                  "Must be an object "
        "with fields `request` ('higher' | 'lower' | 'exact') and "
        "`threshold` (integer)."
    )
    release_month: int = Field(default=00, description="Release month in MM format to filter by.")
    country: str = Field(default="unk", description="Country of origin to filter by.")


# LangChain-compatible tool
@tool(args_schema=ItemFilterInput)
def item_filter_tool(actors: Optional[List[str]] = None, genres: Optional[List[str]] = None,
                     director: Optional[List[str]] = None, producer: Optional[List[str]] = None,
                     imdb_rating: Optional[ComparisonFilter] = None, duration: Optional[ComparisonFilter] = None,
                     release_date: Optional[ComparisonFilter] = None, release_month: Optional[int] = None,
                     country: Optional[str] = None) -> dict:
    """
    Returns the list of IDs of the items that satisfy the given conditions.
    """
    print(f"\n{get_time()} - item_filter has been triggered!!!\n")

    # convert dict to Pydantic objects if they are not already -> this is especially useful for the test
    if isinstance(imdb_rating, dict):
        imdb_rating = ComparisonFilter(**imdb_rating)
    if isinstance(duration, dict):
        duration = ComparisonFilter(**duration)
    if isinstance(release_date, dict):
        release_date = ComparisonFilter(**release_date)

    # Build the filters dict
    filters = {
        key: value
        for key, value in {
            "actors": actors,
            "genres": genres,
            "director": director,
            "producer": producer,
            "imdb_rating": {"request": imdb_rating.request, "threshold": imdb_rating.threshold} if imdb_rating is not None and imdb_rating.threshold != 0 else None,
            "duration": {"request": duration.request, "threshold": duration.threshold} if duration is not None and duration.threshold != 0 else None,
            "release_date": {"request": release_date.request, "threshold": release_date.threshold} if release_date is not None and release_date.threshold != 0 else None,
            "release_month": release_month if release_month is not None and release_month != 00 else None,
            "country": country if country is not None and country != "unk" else None,
        }.items()
        if value is not None
    }

    if not filters:
        return JSON_GENERATION_ERROR

    sql_query, corrections, failed_corrections = define_sql_query("items", filters)
    mess = ""
    item_ids = []

    if sql_query is not None:
        result = execute_sql_query(sql_query)
        item_ids = [str(row[0]) for row in result]

        if item_ids:
            mess = (
                "The IDs of the items satisfying the given conditions are returned."
                "If another tool call is needed, you can now proceed to the next tool call. It is enough you pass "
                "this list to the \"items\" parameter of the next tool call."
            )

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
    )

    print(f"\n{get_time()} - Returned item IDs: {item_ids}")

    if item_ids:
        return {
            "status": "success",
            "message": correction_text + mess,
            "data": item_ids
        }
    else:
        return {
            "status": "failure",
            "message": no_match_text,
            "data": None
        }
