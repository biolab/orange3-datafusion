Movie Ratings
=============

.. figure:: icons/movie-ratings.png
   :alt: Movie ratings widget icon

   Movie ratings widget icon
Constructs a relation matrix of user ratings for movies.

Signals
-------

**Inputs**:

-  (None)

**Outputs**:

-  **Ratings**

Movie ratings relation matrix.

Description
-----------

**Movie Ratings** widget gives you access to data on user ratings for
more than 8500 movies from the `Movielens <https://movielens.org/>`__
database. The data set contains 1 to 5-star ratings representing
user-movie preferences. This is a good widget to try out data fusion as
it gives you instant access to the data.

.. figure:: images/MovieRatings-stamped.png
   :alt: Movie Ratings widget

   Movie Ratings widget

1. Select a subset of movies for which you would like to obtain user
   ratings:

-  **fraction of movies** will output a specified fraction of movies
   selected uniformly at random from the entire database.
-  **time period** will output all the movies released in a specified
   time period

2. Click *Apply* to commit the changes.

Example
-------

**Movie Ratings** will output users-by-movies data matrix for further
analysis. Feed it into the **Fusion Graph** to decompose data matrix
into the product of smaller latent data matrices or view the data in a
**Data Table**.
