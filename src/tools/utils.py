import sqlite3
import pandas as pd
import ast
from rapidfuzz import process
from src.constants import DATABASE_NAME
import os
import json
from src.utils import get_time


def create_lists_for_fuzzy_matching():
    # create the lists of actors, directors, producers, and genres for fuzzy matching
    global actors_list, producers_list, directors_list, genres_list, countries_list
    actors_list = extract_unique_names("./data/ml-100k/final_ml-100k.csv", "actors_list")
    producers_list = extract_unique_names("./data/ml-100k/final_ml-100k.csv",
                                          "producers_list")
    directors_list = extract_unique_names("./data/ml-100k/final_ml-100k.csv",
                                          "directors_list")
    genres_list = extract_unique_names("./data/ml-100k/final_ml-100k.csv", "genres_list")
    countries_list = extract_unique_names("./data/ml-100k/final_ml-100k.csv", "country")


def execute_sql_query(sql_query):
    """
    This function executes the given SQL query and returns the result.

    :param sql_query: SQL query string
    :return: result of the query
    """
    conn = sqlite3.connect(f'{DATABASE_NAME}.db')
    cursor = conn.cursor()
    cursor.execute(sql_query)
    result = cursor.fetchall()
    conn.close()
    print(f"\n{get_time()} - The result of the query {sql_query} is: \n{str(result)}\n")
    return result


def define_sql_query(table, conditions):
    """
    This function defines a SQL query given the passed conditions (filter
    argument in the LLM-generated JSON for function calling)
    :param table: database table name
    :param conditions: filters to create SQL query
    :return: SQL query string ready to be executed
    """
    query_parts = []
    corrections, failed_corrections = [], []
    requested_field = None
    if table == "interactions":
        if 'user' in conditions:
            user_id = conditions['user']
            query_parts.append(f'user_id = {user_id}')
            requested_field = "items"
        else:
            return None
    elif table == "items" and ('genres' in conditions or 'actors' in conditions or
                               'director' in conditions or 'producer' in conditions or
                               'release_date' in conditions or 'duration' in conditions or
                               'imdb_rating' in conditions or 'release_month' in conditions or
                               'country' in conditions):
        # process textual features
        process_textual("genres", conditions, genres_list, query_parts, corrections, failed_corrections)
        process_textual("actors", conditions, actors_list, query_parts, corrections, failed_corrections)
        process_textual("director", conditions, directors_list, query_parts, corrections, failed_corrections)
        process_textual("producer", conditions, producers_list, query_parts, corrections, failed_corrections)
        process_textual("country", conditions, countries_list, query_parts, corrections, failed_corrections)

        # process numerical features
        process_numerical("release_date", conditions, query_parts)
        process_numerical("release_month", conditions, query_parts)
        process_numerical("duration", conditions, query_parts)
        process_numerical("imdb_rating", conditions, query_parts)

        requested_field = "item_id"
    elif table == "items" and 'specification' in conditions and 'items' in conditions:
        specification = conditions['specification']
        items = conditions['items']
        requested_field = ", ".join(specification)
        query_parts.append(f"item_id IN ({', '.join([str(i) for i in items])})")
    elif table == "items" and "select" in conditions:
        if "items" in conditions:
            query_parts.append(f"item_id IN ({', '.join([str(i) for i in conditions['items']])})")
        requested_field = ", ".join(conditions['select'])
    elif table == "users" and "specification" in conditions and "user" in conditions:
        specification = conditions['specification']
        user = [conditions['user']] if not isinstance(conditions['user'], list) else conditions['user']
        requested_field = ", ".join(specification)
        query_parts.append(f"user_id IN ({', '.join([str(i) for i in user])})")
    else:
        return None, corrections, failed_corrections
    if requested_field is not None and query_parts:
        sql_query = f"SELECT {requested_field} FROM {table} WHERE {' AND '.join(query_parts)}"
        print(f"\n{get_time()} - Generated query: {sql_query}\n")
        return sql_query, corrections, failed_corrections
    elif requested_field is not None and not query_parts and "select" in conditions:
        sql_query = f"SELECT {requested_field} FROM {table}"
        print(f"\n{get_time()} - Generated query: {sql_query}\n")
        return sql_query, corrections, failed_corrections
    else:
        return None, corrections, failed_corrections


def extract_unique_names(csv_path, column):
    """
    This function extracts unique names from a column of the dataset CSV file. The returned list
    is used to implement fuzzy matching when performing SQL queries. Note fuzzy matching is only
    performed for textual features.

    :param csv_path: path to the CSV file
    :param column: column name
    :return: list of unique names
    """
    df = pd.read_csv(csv_path, sep='\t')

    all_names = set()

    for row in df[column].dropna():
        try:
            # check if it is list
            if "[" in row and "]" in row:
                # if it is a list inside a string, we need to evaluate it to get the real list
                name_list = ast.literal_eval(row)
                if not isinstance(name_list, list):
                    name_list = [name_list]
            else:
                name_list = [row]
            all_names.update(name.strip() for name in name_list)
        except Exception as e:
            print(f"Error parsing row: {row}\n{e}")

    return sorted(all_names)


def process_textual(feature, conditions, names_list, query_parts, corrections, failed_corrections):
    """
    Process a textual feature for creating the SQL query.

    :param feature: name of the feature to be processed
    :param conditions: the filters provided by the user in the prompt
    :param names_list: list of valid names
    :param query_parts: str where to append the query part processed by this functions
    :param corrections: list of corrections performed thanks to fuzzy matching
    :param failed_corrections: list of failed corrections
    """
    if feature in conditions:
        f = conditions[feature]
        # check if a string is passed. If yes, we need to convert it in a list for the next cycle to work properly
        if isinstance(f, str):
            f = [f]
        for f_ in f:
            # perform fuzzy matching
            f_corrected = correct_name(f_, names_list)
            if f_corrected is None:
                print(f"ERROR: {f_} is not a valid label for feature {feature}")
                failed_corrections.append(f_)
                continue  # if the name is not valid, we do not perform the query with that name
            if f_corrected != f_:
                print(f"Corrected name {f_} with name {f_corrected}")
                corrections.append(f"{f_} -> {f_corrected}")
            query_parts.append(f"LOWER({feature}) LIKE '%{f_corrected.lower()}%'")


def correct_name(input_name, candidates, threshold=70):
    """
    Returns the best fuzzy match if above threshold; otherwise returns None.
    """
    print(f"Trying correcting name {input_name}")
    match, score, _ = process.extractOne(input_name, candidates)
    if score >= threshold:
        return match
    print(f"Failed to correct name {input_name}")
    return None


def process_numerical(feature, conditions, query_parts):
    """
    Process a numerical feature for creating the SQL query.

    :param feature: name of the feature to be processed
    :param conditions: conditions provided by the user in the prompt
    :param query_parts: str where to append the query part processed by this functions
    """
    if feature in conditions:
        f = conditions[feature]
        request = None
        if isinstance(f, dict):
            request = f['request']
            f = f['threshold']
        if request is not None:
            query_parts.append(
                f"{feature} > {f}") if request == "higher" else query_parts.append(
                f"{feature} < {f}")
        else:
            query_parts.append(f"{feature} = {f}")
