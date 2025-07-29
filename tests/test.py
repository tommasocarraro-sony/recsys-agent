from langchain.chains.constitutional_ai.prompts import examples
from langsmith import Client
import json
import uuid

client = Client()

# Create a dataset
with open('./test/evaluation_examples.json', 'r') as file:
    data = json.load(file)

example_pairs = []
for example in examples:
    example_pairs.append((example["query"], example["output"]))

dataset_name = "Recommendation agent response"
if not client.has_dataset(dataset_name=dataset_name):
    dataset = client.create_dataset(dataset_name=dataset_name)
    inputs, outputs = zip(
        *[({"input": text}, {"output": label}) for text, label in example_pairs]
    )
    client.create_examples(inputs=inputs, outputs=outputs, dataset_id=dataset.id)


_printed = set()
thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        # Checkpoints are accessed by thread_id
        "thread_id": thread_id,
    }
}

def predict_sql_agent_answer(example: dict):
    """Use this for answer evaluation"""
    # todo I need to predict here using my model so we have to make it modular in some way
    msg = {"messages": ("user", example["input"])}
    messages = graph.invoke(msg, config)
    return {"response": messages['messages'][-1].content}