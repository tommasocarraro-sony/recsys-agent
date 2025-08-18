import torch
from src.tools.utils import get_time
from recbole.quick_start import load_data_and_model
from recbole.utils.case_study import full_sort_scores, full_sort_topk
from langchain_core.tools import tool
from src.constants import JSON_GENERATION_ERROR
from pydantic import BaseModel, Field
from typing import List, Optional
import os


class TopKRecommendationInput(BaseModel):
    user: int = Field(..., description="User ID.")
    k: int = Field(default=5, description="Number of recommended items. Default is 5.")
    items: List[int] = Field(
        default_factory=list,
        description="List of item IDs to be given to the recommender system."
    )


def create_recbole_environment(model_path):
    """
    This function creates a global RecBole environment that can be accessed by the functions that
    process recommendation requests.

    :param model_path: path to pre-trained recsys model
    """
    global config, model, dataset, train_data, valid_data, test_data
    config, model, dataset, train_data, valid_data, test_data = load_data_and_model(
        model_file=model_path
    )

@tool(args_schema=TopKRecommendationInput)
def get_top_k_recommendations_tool(user: int, k: int = 5, items: Optional[List[int]] = None) -> dict:
    """
    Returns a list of the IDs of the top k recommended items for the given user.
    It computes recommendations over the entire item catalog unless a list of items is given.
    """
    print(f"\n{get_time()} - get_top_k_recommendations_tool(user={user}, k={k}, items={items})\n")

    if user is None or k is None:
        return JSON_GENERATION_ERROR

    if 'config' not in globals():
        create_recbole_environment(os.getenv("RECSYS_MODEL_PATH"))

    uid_series = dataset.token2id(dataset.uid_field, [str(user)])

    if items:
        recommended_items = recommend_given_items(uid_series, items, k=k)
    else:
        recommended_items = recommend_full_catalog(uid_series, k=k)

    print(f"\n{get_time()} - Returned recommended items: {recommended_items}\n")

    return {
        "status": "success",
        "message": (
            f"The top {k} recommendations for user {user} are returned."
        ),
        "data": list(recommended_items)
    }


def recommend_full_catalog(user, k=5):
    """
    It generates a ranking for the given user on the entire item catalog using the loaded
    pre-trained model.

    :param user: user ID for which the recommendation has to be generated
    :param k: number of items to be returned (first k positions in the ranking)
    :return: ranking (of item IDs) for the given user ID
    """
    topk_score, topk_iid_list = full_sort_topk(user, model, test_data, k=k,
                                               device=config['device'])
    return dataset.id2token(dataset.iid_field, topk_iid_list.cpu())[0]


def recommend_given_items(user, item_ids, k=5):
    """
    Generates recommendations for the given user and item IDs using the pre-trained model.

    :param user: user ID for which the recommendation has to be generated
    :param item_ids: item IDs for which the recommendation has to be generated
    :param k: number of items to be returned (first k positions in the ranking)
    :return: ranking (of item IDs) for the given user ID
    """
    all_scores = full_sort_scores(user, model, test_data, device=config['device'])
    item_ids = [str(i) for i in item_ids]
    satisfying_item_scores = all_scores[
        0, dataset.token2id(dataset.iid_field, item_ids)]
    _, sorted_indices = torch.sort(satisfying_item_scores, descending=True)
    return [item_ids[i] for i in sorted_indices[:k].cpu().numpy()]
