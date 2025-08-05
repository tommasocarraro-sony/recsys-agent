import pandas as pd
import ast
from src.my_app.utils import convert_age_to_string

# Genre mapping
genre_map = {
    0: "Action", 1: "Adventure", 2: "Animation", 3: "Children's",
    4: "Comedy", 5: "Crime", 6: "Documentary", 7: "Drama",
    8: "Fantasy", 9: "Film-Noir", 10: "Horror", 12: "Musical",
    13: "Mystery", 14: "Romance", 15: "Sci-Fi", 16: "Thriller", 17: "unknown",
    18: "War", 19: "Western"
}

# Read your original CSV
df = pd.read_csv('movielens100k_details.csv')

# Rename columns
df = df.rename(columns={
    'movie_genres': 'genres',
    'writer': 'producer',
    'cast': 'actors',
    'movie_length': 'duration',
    'rating': 'imdb_rating',
    'num_review': 'imdb_num_reviews',
    'release_date': 'release_month',
    'year': 'release_date',
    'movie_id': 'item_id',
    'movie_title': 'title',
    'country': 'country'
})

# Drop unwanted columns
df = df.drop(columns=['poster_url', 'movie_url', 'genre'])


# Convert genre IDs to names
def map_genre_ids(genre_id_string, as_list=False):
    try:
        ids = ast.literal_eval(genre_id_string)
        genres = [genre_map.get(int(i), f"Unknown({i})") for i in ids]
        if as_list:
            return genres
        else:
            if len(genres) == 1:
                return genres[0]
            elif len(genres) == 2:
                return f"{genres[0]} and {genres[1]}"
            else:
                return ", ".join(genres[:-1]) + ", and " + genres[-1]
    except (ValueError, SyntaxError):
        return "unknown"


def format_names(name_list):
    name_list = ast.literal_eval(name_list)
    if not name_list:
        return "unknown"
    elif len(name_list) == 1:
        return name_list[0]
    elif len(name_list) == 2:
        return f"{name_list[0]} and {name_list[1]}"
    else:
        return ", ".join(name_list[:-1]) + ", and " + name_list[-1]


def compute_n_ratings(rating_file_path, user_meta_path=None, category=None):
    """
    Loads a ratings CSV and counts the number of ratings per item.

    It optionally computes the number of ratings per user age group or gender group, if
    user_meta_path and category are provided.

    Args:
        rating_file_path (str): Path to the CSV file.
        user_meta_path (str): Path to user metadata file
        category (str): kid, teenager, young_adult, adult, senior, male, female

    Returns:
        number of ratings per item
    """
    # Load CSV
    df = pd.read_csv(rating_file_path, sep='\t')

    if user_meta_path is not None and category is not None:
        # Load user metadata
        user_df = pd.read_csv(user_meta_path, sep='\t')

        if category not in ('M', 'F'):
            # Convert age to age category
            user_df['age_category'] = user_df['age:token'].apply(convert_age_to_string)

        # Filter users by age category
        filtered_users = user_df[user_df['age_category' if category not in ('M', 'F') else 'gender:token'] == category]

        # Filter ratings by users in the selected category
        df = df[df['user_id:token'].isin(filtered_users['user_id:token'])]

    # Count number of ratings per item
    item_rating_counts = df['item_id:token'].value_counts()

    return item_rating_counts


df['genres_list'] = df['genres'].apply(map_genre_ids, args=(True, ))
df['genres'] = df['genres'].apply(map_genre_ids)
df['release_date'] = df['release_date'].str.extract(r'(\d{4})')
df['release_month'] = df['release_month'].str.extract(r'^\d{2}-(\d{2})-\d{4}$')
df['directors_list'] = df['director']
df['director'] = df['director'].apply(format_names)
df['actors_list'] = df['actors']
df['actors'] = df['actors'].apply(format_names)
df['producers_list'] = df['producer']
df['producer'] = df['producer'].apply(format_names)
n_ratings = compute_n_ratings("ml-100k.inter")
df['n_ratings'] = df['item_id'].map(n_ratings)
n_ratings_kid = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="kid")
df['n_ratings_kid'] = df['item_id'].map(n_ratings_kid).fillna(0).astype(int)
n_ratings_teenager = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="teenager")
df['n_ratings_teenager'] = df['item_id'].map(n_ratings_teenager).fillna(0).astype(int)
n_ratings_young_adult = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="young adult")
df['n_ratings_young_adult'] = df['item_id'].map(n_ratings_young_adult).fillna(0).astype(int)
n_ratings_adult = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="adult")
df['n_ratings_adult'] = df['item_id'].map(n_ratings_adult).fillna(0).astype(int)
n_ratings_senior = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="senior")
df['n_ratings_senior'] = df['item_id'].map(n_ratings_senior).fillna(0).astype(int)
n_ratings_male = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="M")
df['n_ratings_male'] = df['item_id'].map(n_ratings_male).fillna(0).astype(int)
n_ratings_female = compute_n_ratings("ml-100k.inter", user_meta_path="./ml-100k.user", category="F")
df['n_ratings_female'] = df['item_id'].map(n_ratings_female).fillna(0).astype(int)
ordered_columns = ['item_id', 'title', 'genres', 'director', 'producer', 'actors', 'release_date', 'release_month', 'country', 'duration', 'age_rating', 'imdb_rating', 'imdb_num_reviews', 'n_ratings', 'description', 'n_ratings_kid', 'n_ratings_teenager', 'n_ratings_young_adult', 'n_ratings_adult', 'n_ratings_senior', 'n_ratings_male', 'n_ratings_female', 'storyline', 'genres_list', 'directors_list', 'producers_list', 'actors_list']

# fill remaining NaN values with unknown
df.fillna("unknown", inplace=True)

# Save the final CSV
df.to_csv('final_ml-100k.csv', index=False, sep='\t', columns=ordered_columns)

print("Final CSV saved as 'final_movies.csv'")
