Movie Genres
============

![Movie Genres widget icon](icons/movie-genres.png)

Constructs movies-genres or actors-genres relation matrix.

Signals
-------

**Inputs**:

- **Row type**

  Instances from the input data.

**Outputs**:

- **Genres**

  Data-to-genres relation matrix.

Description
-----------

This widget matches movies or actors to movie genre and forms a relation matrix.
It is used for filtering the data and getting a more precise reconstruction result.

![Movie Genres widget](images/MovieGenres-stamped.png)

1. A list of movie genres that are match with the input data.

Example
-------

This example shows how we refined the results of our data fusion by
adding **Movie Genres** in the equation. You can see in the **Data Table**
that all movies are matched by genre.

<img src="images/MovieGenres-Example.png" alt="image" width="600">
