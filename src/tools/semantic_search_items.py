from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, SearchParams
from sentence_transformers import SentenceTransformer
from src.utils import get_time
from src.constants import JSON_GENERATION_ERROR, COLLECTION_NAME

load_dotenv()


class SemanticSearchItemsParams(BaseModel):
    query: str = Field(..., description="Natural language query describing the item(s) to search for. Can be an item description, storyline, or some keywords (for mood-based search).")
    items: List[int] = Field(
        default_factory=list,
        description="Optional list of items. If provided, the search will only consider these items."
    )


@tool(args_schema=SemanticSearchItemsParams)
def semantic_search_items(query: str, item_ids: Optional[List[int]] = None) -> dict:
    """
    Search items in a vector store and returns the 10 top matching items.
    """
    print(f"\n{get_time()} - semantic_search_items(query={query}, item_ids={item_ids})\n")

    if query is None:
        return JSON_GENERATION_ERROR

    try:
        # Load env variables
        collection_name = COLLECTION_NAME
        top_k = 11

        # Connect to local Qdrant instance
        client = QdrantClient(url="http://localhost:6333")

        # Encode query
        embedder = SentenceTransformer("paraphrase-MiniLM-L6-v2")
        query_vector = embedder.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()
        print(f"\n{get_time()} - Performing vector store search with query: {query}.\n")
        # Build optional filters
        qdrant_filter = None
        if item_ids:
            items = [int(i) for i in item_ids]
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="item_id",
                        match=MatchAny(any=items)
                    )
                ]
            )


        # Perform the search
        hits = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            search_params=SearchParams(hnsw_ef=128),
            with_payload=True
        ).model_dump()

        # Collect metadata
        item_metadata = {
            str(hit["payload"]["item_id"]): {
                "item_id": str(hit["payload"]["item_id"]),
                "storyline": hit["payload"].get("storyline", None)
            }
            for hit in hits["points"] if "payload" in hit.keys() and "item_id" in hit["payload"]
        }

        # Filter out self-matches
        item_metadata = {
            k: v for k, v in item_metadata.items()
            if v['storyline'] is not None and v['storyline'] != query
        }

        item_ids = list(item_metadata.keys())

        print(f"\n{get_time()} - Returned list: {item_ids}\n")

        return {
            "status": "success",
            "message": f"The IDs of the {len(item_ids)} best matching items are returned.",
            "data": item_ids
        }

    except Exception as e:
        return {
            "status": "failure",
            "message": f"Vector store search failed due to: {str(e)}",
            "data": None
        }
