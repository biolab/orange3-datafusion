Orange3 Data Fusion
===================

This is a data fusion add-on for [Orange3](http://orange.biolab.si). Add-on
wraps [scikit-fusion](http://github.com/marinkaz/scikit-fusion), a Python library for 
data fusion, and implements a set of widgets for loading of the data, definition of 
data fusion schema, collective matrix factorization and exploration of latent factors.

Installation
------------

To install the add-on, run

    python setup.py install

To register this add-on with Orange, but keep the code in the development
directory (do not copy it to Python's site-packages directory), run

    python setup.py develop

Usage
-----

Run Orange from the terminal by

    python -m Orange.canvas

Data fusion widgets are in the toolbox bar under Data Fusion section.
