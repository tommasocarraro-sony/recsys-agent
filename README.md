# LLM-based Recommendation System Agents

## Prerequisites

You should have Python, Docker, and Conda installed.
You must have an OpenAI subscription as this application needs an OpenAI API key.

## Installation instructions

First of all, clone this repository.

Then, run the following commands in the root directory of the project:

1. `conda create --name <env> python=3.12`
2. `conda activate <env>`
3. `pip install -r requirements.txt`

Create a `.env` file and put it inside the root directory of the project. Add an OpenAI API key to the .env file, for example, `OPENAI_API_KEY=<your_key>`.

## Execution instructions

First of all, you need to start docker.

Then, you can run the application using:

`python app_main.py`
