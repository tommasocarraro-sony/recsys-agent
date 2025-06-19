import json
import torch
from src.tools.utils import get_time, convert_to_list
from recbole.quick_start import load_data_and_model
from recbole.utils.case_study import full_sort_scores, full_sort_topk
from langchain_core.tools import tool
from src.constants import JSON_GENERATION_ERROR
from pydantic import BaseModel, Field
from typing import List, Union, Optional
import os


class TopKRecommendationInput(BaseModel):
    user: int = Field(..., description="User ID.")
    k: int = Field(default=5, description="Number of recommended items.")
    items: Optional[Union[List[int], str]] = Field(
        default=None,
        description="Item IDs (list) or path to a JSON file containing the item IDs."
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

@tool
def get_top_k_recommendations_tool(input: TopKRecommendationInput) -> str:
    """
    Returns a list of the IDs of the top k recommended items for the given user.
    It computes recommendations over the entire item catalog unless a list of items or a path to a temporary file
    containing a list of item is given.
    """
    print(f"\n{get_time()} - get_top_k_recommendations has been triggered!!!\n")

    try:
        user = input.user
        k = input.k
        items = input.items
    except Exception:
        return json.dumps(JSON_GENERATION_ERROR)

    if 'config' not in globals():
        create_recbole_environment(os.getenv("RECSYS_MODEL_PATH"))

    uid_series = dataset.token2id(dataset.uid_field, [str(user)])

    if items is not None:
        try:
            item_list = convert_to_list(items)
        except Exception:
            return json.dumps({
                "status": "failure",
                "message": "There are issues with the temporary file containing the item IDs.",
            })
        recommended_items = recommend_given_items(uid_series, item_list, k=k)
    else:
        recommended_items = recommend_full_catalog(uid_series, k=k)

    print(f"\n{get_time()} - These are the recommended items: {recommended_items}")

    return json.dumps({
        "status": "success",
        "message": (
            f"The top {k} recommendations for user {user} are returned."
        ),
        "data": list(recommended_items)
    })


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
