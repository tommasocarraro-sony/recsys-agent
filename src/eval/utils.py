from langchain_openai import ChatOpenAI
from typing_extensions import Annotated, TypedDict
from src.eval.constants import GRADER_SYSTEM_PROMPT
import json
from langsmith.evaluation import evaluate


class CorrectnessGrade(TypedDict):
    """Pydantic schema for the output of LLM grader. The output must satisfy this schema"""
    explanation: Annotated[str, ..., "Explain your reasoning for the score"]
    correct: Annotated[bool, ..., "True if the answer is correct, False otherwise."]

# Grader LLM - this has to determine whether the output of our LLM is similar to the ground truth
grader_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(CorrectnessGrade, method="json_schema", strict=True)


def correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Evaluates one single example by measuring the semantic/factual similarity between our LLM answer and the ground
    truth reply we prepared. The result is a boolean. 1 means high similarity, 0 means the answer is not correct.

    :param inputs: the query
    :param outputs: the answer of our LLM model
    :param reference_outputs: the ground truth reply we prepared
    """
    answers = f"""\
        QUESTION: {inputs['input']}
        GROUND TRUTH ANSWER: {reference_outputs['output']}
        STUDENT ANSWER: {outputs['response']}"""

    # Run evaluator
    grade = grader_llm.invoke([
        {"role": "system", "content": GRADER_SYSTEM_PROMPT},
        {"role": "user", "content": answers}
    ])
    return grade["correct"]


def create_langsmith_dataset(langsmith_client, dataset_path, dataset_name):
    """
    Creates a dataset for the evaluation of the LLM agent.

    :param langsmith_client: client for langsmith
    :param dataset_path: where the dataset is located on local PC
    :param dataset_name: name of the dataset in langsmith
    """
    # Create a dataset
    with open(dataset_path, 'r') as file:
        examples = json.load(file)

    example_pairs = []
    for k, example in examples.items():
        example_pairs.append((example["query"], example["output"]))

    if not langsmith_client.has_dataset(dataset_name=dataset_name):
        dataset = langsmith_client.create_dataset(dataset_name=dataset_name)
        inputs, outputs = zip(
            *[({"input": text}, {"output": label}) for text, label in example_pairs]
        )
        langsmith_client.create_examples(inputs=inputs, outputs=outputs, dataset_id=dataset.id)


def evaluate_model(agent, dataset_name, in_context_examples):
    """
    Performs evaluation on the given dataset of the given LLM agent. All results will be logged to LangSmith.

    :param agent: LLM agent that needs to be evaluated
    :param dataset_name: name of the dataset in langsmith
    :param in_context_examples: whether the model can receive in-context examples or not. This is to facilitate the model
    and is beneficial for small language models
    """

    def predict_recommendation_agent_answer(example: dict):
        """Use this for answer evaluation"""
        messages = agent.graph_invoke(example["input"], in_context_examples)
        return {"response": messages['messages'][-1].content}

    evaluate(
        predict_recommendation_agent_answer,
        data=dataset_name,
        evaluators=[correctness],
        num_repetitions=3
    )
