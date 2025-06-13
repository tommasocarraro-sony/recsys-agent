# LLM-based Recommendation System Agents

## Prerequisites

You should have Docker and Conda installed.
You must have an OpenAI subscription as this application needs an OpenAI API key.

## Installation instructions

First of all, clone this repository.

Then, run the following commands in the root directory of the project:

1. `conda create --name <env> python=3.12`
2. `conda activate <env>`
3. `pip install -r requirements.txt`

Create a `.env` file and put it inside the root directory of the project. Add an OpenAI API key to the .env file, for example, `OPENAI_API_KEY=<your_key>`.

## Execution instructions

First of all, you need to perform the training of the recommendation system on the MovieLens-100k dataset. This is done by using the RecBole framework. This step should take a few minutes as the recommender is a basic Matrix Factorization model. 

To train the recommendation model, just run the following command from the folder `./data/ml-100k/`:

`python recsys_training.py`

After the successful training of the model, you must start Docker.

Finally, you can run the application by running the following command from the root folder of the project:

`python app_main.py`
