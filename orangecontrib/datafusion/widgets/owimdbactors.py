import sys
import skfusion
from PyQt4 import QtGui
from orangecontrib.datafusion.table import Relation
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui, settings
from orangecontrib.datafusion.movielens import movie_concept_matrix, actor_matrix
from skfusion.fusion import ObjectType


class OWIMDbActors(OWWidget):
    name = "IMDb Actors"
    icon = "icons/imdb.svg"
    want_main_area = False
    description = "Get a movie-actor and actor-actor matrix"
    inputs = [("Filter", Relation, "set_data", widget.Default)]
    outputs = [("Movies Actors", Relation, widget.Default), ("Actors Actors", Relation, widget.Default)]

    percent = settings.Setting(10)

    def __init__(self):
        super().__init__()
        self.data = None
        self.row_names = None
        self.movie_actor_mat = None
        self.actor_actor_mat = None
        self.actors = None
        self.infobox = gui.widgetBox(self.controlArea, "Select Actors")

        percent = gui.hSlider(
            gui.indentedBox(self.infobox), self, "percent",
            minValue=1, maxValue=100, step=1, ticks=10, labelFormat="%d %%")

        gui.button(self.controlArea, self, "&Apply",
                   callback=self.send_output, default=True)

        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                           QtGui.QSizePolicy.Fixed))

        self.setMinimumWidth(250)
        self.setMaximumWidth(250)

    def set_data(self, data):
        self.row_names = data.relation.row_names
        self.send_output()

    def send_output(self):
        if self.row_names is not None:
            self.movie_actor_mat, self.actors = movie_concept_matrix(self.row_names, concept="actor",
                                                                     actors=self.percent)
            self.actor_actor_mat = actor_matrix(self.movie_actor_mat)

            movies_actors = skfusion.fusion.Relation(self.movie_actor_mat, ObjectType("Movies"),
                                                     ObjectType("Actors"), row_names=self.row_names,
                                                     col_names=self.actors)
            self.send("Movies Actors", Relation(movies_actors))

            actors_actors = skfusion.fusion.Relation(self.actor_actor_mat, ObjectType("Actors"),
                                                     ObjectType("Actors"), row_names=self.actors,
                                                     col_names=self.actors)
            self.send("Actors Actors", Relation(actors_actors))

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWIMDbActors()
    #ow.set_data(movies_users)
    ow.show()
    app.exec_()
