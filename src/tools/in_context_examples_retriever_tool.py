from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.tools import tool
from src.utils import get_time
from src.constants import JSON_GENERATION_ERROR
from src.utils import in_context_vector_store_search

load_dotenv()


class InContextExamplesRetrieverParams(BaseModel):
    query: str = Field(..., description="Query to search for in-context examples in the vector store. This is usually the entire user query.")


@tool(args_schema=InContextExamplesRetrieverParams)
def in_context_examples_retriever_tool(query: str) -> dict:
    """
    Performs a vector store search in the vector store containing in-context examples and returns the 2 top matching in-context examples (structured inside a dictionary).
    Each example includes a user query, a tool call plan to answer the user query, and a set of instructions to call the tools in the tool call plan.
    """
    print(f"\n{get_time()} - in_context_examples_retriever_tool(query={query})\n")

    if query is None:
        return JSON_GENERATION_ERROR

    try:
        print(f"\n{get_time()} - Performing vector store search (for in-context examples) with query: {query}.\n")

        in_context_examples = in_context_vector_store_search(query)

        return {
            "status": "success",
            "message": f"The two top matching in-context examples are returned. You can use them to organize the tool call plan to answer the target user query: '{query}'.",
            "data": in_context_examples
        }

    except Exception as e:
        return {
            "status": "failure",
            "message": f"Vector store search failed due to: {str(e)}",
            "data": None
        }
