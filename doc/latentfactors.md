Latent Factors
==============

![Latent factors widget icon](icons/latent-factors.png)

Draws data fusion graph with latent factors. Outputs latent factors for further analysis.

Signals
-------

**Inputs**:

- **Fitted fusion graph**

  Fitted collective matrix.

**Outputs**:

- **Relation**

  Relations between two groups of objects.

Description
-----------

**Latent Factors** widget displays relations between latent factors from the matrix
decomposition and arranges groups these factors by function. Selecting a latent factor
will place it in the output channel, where you can futher feed the data into other widget - for example a **Data Table**.

![Latent factors widget](images/LatentFactors1-stamped.png)

1. Information on the input (object types are nodes, relations are links between the nodes).
2. A list of **recipe factors** (compressed matrix of the object type).
3. A list of **backbone factors** (interactions between latent components).
4. A list of **completed relations** (full relation matrix).

Example
-------



<img src="images/GEODataSets-Example2.png" alt="image" width="600">
