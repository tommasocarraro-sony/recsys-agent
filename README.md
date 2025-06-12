# LLM-based Recommendation System Agents

## Prerequisites

You should have Python, Docker, and Conda installed.
You must have an OpenAI subscription as this application needs an OpenAI API key.

## Installation instructions

First of all, clone this repository.

Then, run the following command:

`conda create --name <env> --file requirements.txt`

Create a `.env` file and put it inside the root directory of the project. Add an OpenAI API key to the .env file, for example, `OPENAI_API_KEY=<your_key>`.

## Execution instructions

After you followed the installation instructions, you can run the application using:

`python app_main.py`
