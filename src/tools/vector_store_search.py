import json
from typing import List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, SearchParams
from sentence_transformers import SentenceTransformer
from src.tools.utils import convert_to_list
from src.utils import get_time
from src.constants import JSON_GENERATION_ERROR, COLLECTION_NAME

load_dotenv()


class VectorStoreSearchParams(BaseModel):
    query: str = Field(..., description="Query to perform the vector store search.")
    items: Optional[Union[List[int], str]] = Field(
        None,
        description="Item ID(s) that have to be included in the vector store search, either directly as a list or as "
                    "a path to a JSON file."
    )


@tool(args_schema=VectorStoreSearchParams)
def vector_store_search_tool(query: str, items: Optional[Union[List[int], str]] = None) -> str:
    """
    Performs a vector store search and returns the 10 top matching item IDs.
    """
    print(f"\n{get_time()} - vector_store_search_tool has been triggered!!!\n")

    if query is None:
        return json.dumps(JSON_GENERATION_ERROR)

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
        if items is not None and items:
            try:
                items = convert_to_list(items)
            except Exception:
                return json.dumps({
                    "status": "failure",
                    "message": "There are issues with the temporary file containing the item IDs."
                })
            items = [int(i) for i in items]
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

        return json.dumps({
            "status": "success",
            "message": "These are the IDs of the best matching items produced by the vector store search.",
            "data": item_ids
        })

    except Exception as e:
        return json.dumps({
            "status": "failure",
            "message": f"Vector store search failed due to: {str(e)}"
        })
