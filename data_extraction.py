# PadX/PadY pads from both sides
# Cells in rows/columns fill up, e.g. set row1 and row5 pushes row5 into the position of row2. Define the empty rows with minwidth
# Contents that overfill a cell pushes the entire column/row to be wider, not just that cell

# Visualization idead:
# Let user select two movies, produce 2D graph plot of people who have rated both movies and with their ratings
# (allows investigation of correlation between movies)
#

import pandas as pd
import numpy as np
from tkinter import *
import time


# Data extraction and filtering

def read_dataset():
    # Read the movielens dataset in using pandas
    nrows = 10000 #TEMP, for testing
    movies = pd.read_csv('movielens_dataset/movies.csv', nrows=nrows)
    tags = pd.read_csv('movielens_dataset/tags.csv', nrows=nrows)
    ratings = pd.read_csv('movielens_dataset/ratings.csv', nrows=nrows)

    # Clean the data - only tags has some null values
    tags = tags.dropna()

    # Separate the movies titles into titles and years
    movies['year'] = movies['title'].str.extract('.*\(([0-9]*)\).*', expand = False)
    movies['title'] = movies['title'].str.extract('(.*) \([0-9]*\).*', expand = False)

    # Convert the genres field from a string to a list of strings
    movies['genres'] = movies['genres'].apply(lambda genres: list(genres.split('|')))

    # Delete timestamps
    del tags['timestamp'], ratings['timestamp']

    return movies, tags, ratings

# Count occurrences of each genre
def genre_occurrences(movies):
    # Get a list of all genres
    genre_labels = set()
    for g_list in movies['genres'].values:
        for g in g_list:
            genre_labels = genre_labels.union(set([g]))

    # Dict of genre occurences
    genre_occurrences = {}
    for g in genre_labels:
        genre_occurrences[g] = 0

    for g_list in movies['genres'].values:
        for g in g_list:
            genre_occurrences[g] += 1

    # Convert the dict into a list of genre, occurrences pairs, sorted by occurrences
    genre_list = list([key, val] for key, val in genre_occurrences.items())
    genre_list.sort(key = lambda x:x[1], reverse=True)

    return genre_list

# Produce lowest, highest, mean, median, stddev, and number of movie ratings for each movie
def get_ratings_stats(movies, ratings):
    # Generate a new dataframe to store the aggregate ratings in
    aggregate_ratings = pd.DataFrame()
    aggregate_ratings['movieId'] = movies['movieId']

    # Create a list of rankings for each movie by looping over the rankings
    rating_list = {i:[] for i in aggregate_ratings['movieId'].values}

    iprint = 10
    for index, row in ratings.iterrows():
        # Check that this movie Id exists in the movies database
        if row['movieId'] in rating_list.keys():
            rating_list[row['movieId']].append(row['rating'])
    
    # Create the aggregate values for each movie with at least 1 rating
    for key, val in rating_list.items():
        # Skip this film if it has no rankings
        if len(val) < 1:
            aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'number_of_ratings'] = 0
            continue
        # Get the lowest and highest values
        lowest = min(val)
        highest = max(val)
        # Get the mean and median
        mean = np.mean(val)
        median = np.median(val)
        # Get the std dev
        stddev = np.std(val)
        # Insert the values
        aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'min_rating'] = lowest
        aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'max_rating'] = highest
        aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'mean_rating'] = mean
        aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'median_rating'] = median
        aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'std_dev'] = stddev
        aggregate_ratings.loc[aggregate_ratings['movieId'] == key, 'number_of_ratings'] = len(val)

    # Return the new dataframe holding aggregated ratings data
    return aggregate_ratings

def get_rating_stats_by_genre(movies, aggregate_ratings):
    # Construct a list of number of movies for each genre in each rating 'bucket' (0.5 to 1, 1 to 1.5, ..., 4.5 to 5.0), inclusive below (except 4.5 to 5.0 range which is inclusive on both sides)
    # Get a list of all genres
    genre_labels = set()
    for g_list in movies['genres'].values:
        for g in g_list:
            genre_labels = genre_labels.union(set([g]))

    metrics = ['min_rating', 'max_rating', 'mean_rating', 'median_rating']

    # Dict of genre score distributions
    genre_counts = {}
    for g in genre_labels:
        genre_counts[g] = {}
        for metric in metrics:
            genre_counts[g][metric] = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    # Join movies and aggregate_ratings on movie Id
    movies = movies.join(aggregate_ratings.set_index('movieId'), on='movieId')

    # Loop over each movie
    for index, row in movies.iterrows():
        # Skip if movie has no ratings
        if row['number_of_ratings'] == 0:
            continue
        # Repeat for each metric
        for metric in metrics:
            # Get this movie's mbucket for this metric
            rating = row[metric]
        index = int(((rating*2)//1)) - 1# This doubles the rating, then floors it, i.e. (0.5->0.99... become 1, 1.0-> 1.499.. become 2, etc.), then subtracts 1 so indices are 0, 1, ...
        if index == 9:
            index -= 1 # Fixes a rating of 5 returning an out of range index of 9
        # Add one at this index for each genre tag this movie has
        for g in row['genres']:
                genre_counts[g][metric][index] += 1

    # Normalise the list to produce proportional results
    for genre in genre_counts.keys():
        for metric in metrics:
            if sum(genre_counts[genre][metric]) > 0:
                genre_counts[genre][metric] = [genre_counts[genre][metric][i]/sum(genre_counts[genre][metric]) for i in range(len(genre_counts[genre][metric]))]

    # Return the list of score distributions by genre
    return genre_counts


# Count occurrences of each tag
def tag_occurrences(movies, tags):
    # Get a list of all tags
    tag_labels = set()
    for tag in tags['tag'].values:
        tag_labels = tag_labels.union(set([tag]))

    # Dict of tag occurences
    tag_occurrences = {}
    for t in tag_labels:
        tag_occurrences[t] = 0

    for tag in tags['tag'].values:
            tag_occurrences[tag] += 1

    # Convert the dict into a list of tag, occurrences pairs, sorted by occurrences
    tag_list = list([key, val] for key, val in tag_occurrences.items())
    tag_list.sort(key = lambda x:x[1], reverse=True)

    return tag_list

# For a given genre, get the top movies from that genre by mean rating (where number of ratings > 1)
def get_top_movies_by_genre(movies, aggregate_ratings, genre, number=10):
    # Get the list of movies of this genre
    genre_movies = movies.loc[movies['genres'].apply(lambda x: genre in x)]

    # Join this list with the aggregate_ratings list
    genre_movies = genre_movies.join(aggregate_ratings.set_index('movieId'), on='movieId')

    # Only consider movies with at least 2 ratings
    genre_movies = genre_movies.loc[genre_movies['number_of_ratings'].apply(lambda x: x >= 2)]

    # Sort the new dataframe by the mean rating, descending
    genre_movies = genre_movies.sort_values('mean_rating', ascending=False)

    # Return the top 10 from this list
    return genre_movies.head(number)
    
    
if __name__ == '__main__':
    movies, tags, ratings = read_dataset()

    aggregate_ratings = get_ratings_stats(movies, ratings)
    print(aggregate_ratings.loc[aggregate_ratings['mean_rating'] > 0].head(10))
    print()

    movies, tags, ratings = read_dataset()
    genre_list = genre_occurrences(movies)
    print(genre_list[:10])
    print()
    tag_list = tag_occurrences(movies, tags)
    print(tag_list[:10])

    genre_scores = get_rating_dist_by_genre(movies, aggregate_ratings)
    print(genre_scores)

    top_10 = get_top_movies_by_genre(movies, aggregate_ratings, genre_list[0][0], 10)
    print(genre_list[0][0])
    print(top_10)
