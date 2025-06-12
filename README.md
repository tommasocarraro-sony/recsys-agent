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

To train the recommendation model, just run the following command:

`python recsys_training.py`

During the first executions, you will encounter some RecBole problems related to Numpy. Fix the issues by following what is printed. You should change some types in RecBole and put a `weights_only=False` in a `torch.load` command. Just follow what is printed.

After fixing all the problems, your training should end correctly.

Then, you must start Docker.

Finally, you can run the application using:

`python app_main.py`
