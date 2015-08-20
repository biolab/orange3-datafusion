IMDb Actors
===========

![IMDB Actors widget icon](icons/imdb-actors.png)

Constructs a movie-actor and actor-actor relation matrix.

Signals
-------

**Inputs**:

- **Filter**

  Data filter.

**Outputs**:

- **Movie Actors**

  A movie-actor relation matrix.

- **Costarring Actors**

  An actor-actor relation matrix.

Description
-----------

This widget gives you the access IMDb data sets on actors and movies. It outputs either a
movie-actor relation matrix, an actor-actor relation matrix or both.

![IMDb widget](images/IMDbActors-stamped.png)

1. Set the percentage of the actors you want to source from the IMDb database.
2. Click *Apply* to commit your data.

Example
-------

This simple widget is great for learning how data fusion works since it enables immediate
access to [IMDb database](https://en.wikipedia.org/wiki/Internet_Movie_DatabaseI. To use it, 
you need to connect it to **Movie Ratings** widget in the
inpupt and with **Fusion Graph** in the output. This will add the information on actors in relation
to movies. You can view this new data in the **Data Table** widget.

<img src="images/IMDbActors-Example.png" alt="image" width="600">
