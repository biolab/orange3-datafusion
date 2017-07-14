import os
import csv
import random
import numpy as np
from skfusion import fusion


class ObjectType:
    Actors = fusion.ObjectType('Actors')
    Movies = fusion.ObjectType('Movies')
    Users = fusion.ObjectType('Users')
    Genres = fusion.ObjectType('Genres')


def actor_genre_matrix(actors):
    movies_genres, genres = movie_concept_matrix(input_movies=None, concept="genre")
    movies_actors, actors = movie_concept_matrix(input_movies=None, concept="actor", actors=actors)

    actors_genres = np.zeros((movies_actors.shape[1], movies_genres.shape[1]))
    for i in range(movies_actors.shape[0]):
        for j in np.nonzero(movies_actors[i]):
            actors_genres[j, :] += movies_genres[i, :]
    return actors_genres, genres


def movie_concept_matrix(input_movies, concept, actors=None):
    if input_movies is None:
        input_movies = get_all_movie_names()

    if concept == "genre":
        filename = "movies.csv"
    elif concept == "actor":
        filename = "actors.csv"
    else:
        raise ValueError("Wrong concept, must be genre or actor")
    filename = get_valid_file_path(filename)

    with open(filename, 'r', encoding="utf8") as f:
        items, all_movies = csv.reader(f, delimiter=','), set(input_movies)
        next(items)
        concepts = {line[1]: line[2].split('|') for line in items if line[1] in all_movies}

    if actors is not None:
        if isinstance(actors, int):
            all_actors = np.array(list(set(x for y in concepts.values() for x in y)))
            idx = set(random.sample(range(len(all_actors)), int(len(all_actors) * actors / 100.0)))
            actors = all_actors[sorted(idx)]

        actors = set(actors)
        for key, val in concepts.items():
            concepts[key] = list(set(val) & actors)

    all_concepts = sorted(list(set(x for y in concepts.values() for x in y)))
    idx = {name: index for name, index in zip(all_concepts, range(len(all_concepts)))}

    mov_gen = np.zeros((len(input_movies), len(all_concepts)))
    for i in range(len(input_movies)):
        for genre in concepts[input_movies[i]]:
            mov_gen[i, idx[genre]] = 1

    return mov_gen, all_concepts


def actor_matrix(mat):
    actors = np.zeros((mat.shape[1], mat.shape[1]))
    for row in mat:
        for i in np.nonzero(row)[0]:
            for j in np.nonzero(row)[0]:
                actors[i, j] += 1 if i != j else 0
    return actors


def movie_user_matrix(percentage=None, start_year=None, end_year=None):
    filename = get_valid_file_path("ratings.csv")
    users, movies, ratings, timestamps = np.loadtxt(filename, skiprows=1, delimiter=",", unpack=True)
    unique_users, unique_movies = np.unique(users.astype(int)), np.unique(movies.astype(int))
    users = users.astype(int)

    if percentage is not None:
        idx = set(random.sample(range(len(unique_movies)), int(len(unique_movies) * percentage / 100.0)))
        filtered_movies = unique_movies[sorted(idx)]
    elif start_year is not None and end_year is not None and start_year <= end_year:
        years = get_all_movie_years()
        filtered_movies = [movie for movie, year in zip(unique_movies, years) if start_year <= year <= end_year]
    else:
        raise ValueError

    movie_idx = {movieId: index for index, movieId in enumerate(filtered_movies)}
    matrix = np.tile(np.nan, (len(filtered_movies), len(unique_users)))

    for i in range(len(ratings)):
        if movies[i] in movie_idx:
            matrix[movie_idx[movies[i]], users[i] - 1] = ratings[i]

    matrix = np.ma.masked_invalid(matrix, copy=False)
    return matrix, names_of_movies(map(str, filtered_movies)), list(map(str, list(unique_users)))


def get_all_movies():
    filename = get_valid_file_path("movies.csv")
    with open(filename, 'r', encoding="utf8") as f:
        items = csv.reader(f, delimiter=',')
        next(items)
        ids = [line[0] for line in items]
    return sorted(set(ids))


def get_all_movie_names():
    filename = get_valid_file_path("movies.csv")
    with open(filename, 'r', encoding="utf8") as f:
        items = csv.reader(f, delimiter=',')
        next(items)
        names = [line[1] for line in items]
    return names


def names_of_movies(movies):
    filename = get_valid_file_path("movies.csv")
    with open(filename, 'r', encoding="utf8") as f:
        items = csv.reader(f, delimiter=',')
        next(items)
        names = {line[0]: line[1] for line in items}
    return [names[movie] for movie in movies]


def get_all_movie_years():
    movie_names = get_all_movie_names()
    return [int(x[-5:-1]) if x[-5:-1].isdigit() else 0 for x in movie_names]


def get_valid_file_path(filename):
    return os.path.join(os.path.dirname(__file__), 'datasets', filename)


if __name__ == '__main__':
    pass
