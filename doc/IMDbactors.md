IMDb Actors
===========

![IMDB Actors widget icon](icons/imdb-actors.png)

Constructs a movies-by-actors and actors-by-actors relation matrix.

Signals
-------

**Inputs**:

- **Filter**

  Data filter.

**Outputs**:

- **Movie Actors**

  A movies-by-actors relation matrix.

- **Costarring Actors**

  An actors-by-actors relation matrix.

Description
-----------

This widget gives you the access [IMDb](https://en.wikipedia.org/wiki/Internet_Movie_Database)
data sets on actors and movies. It outputs either a
movies-by-actors relation matrix, an actors-by-actors relation matrix or both.

![IMDb widget](images/IMDbActors-stamped.png)

1. Select how many actors from the IMDb database would you like to consider.
2. Click *Apply* to commit your data.

Example
-------

This simple widget is great for learning how data fusion works since it enables immediate
access to [IMDb database](https://en.wikipedia.org/wiki/Internet_Movie_Database). To use it, 
you need to connect it to **Movie Ratings** widget in the
input and with **Fusion Graph** in the output. This will add the information on actors in relation
to movies. You can view this new data in the **Data Table** widget.

<img src="images/IMDbActors-Example.png" alt="image" width="600">
