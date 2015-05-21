import sys
import skfusion
import numpy as np
from PyQt4 import QtGui
from PyQt4.QtGui import QGridLayout
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui
from orangecontrib.datafusion.movielens import movie_concept_matrix, actor_genre_matrix
from skfusion.fusion import ObjectType
from orangecontrib.datafusion.table import Relation


class OWMovieGenres(OWWidget):
    name = "Movie Genres"
    icon = "icons/genres.svg"
    want_main_area = False
    description = "Get a movies-genres or actors-genres matrix"
    inputs = [("Movies/Actors", Relation, "set_data", widget.Default)]
    outputs = [("Genres", Relation, widget.Default)]

    def __init__(self):
        super().__init__()
        self.data = None
        self.matrix = None
        self.genres = None
        self.row_names = None
        self.labels = []
        self.row_type = None

        self.layout = QGridLayout()
        self.genrebox = gui.widgetBox(self.controlArea, "Select Genres")

    def update_genres(self):
        if self.genres is not None:
            for label in self.labels:
                del label
            self.labels = []
            size = int(np.ceil(np.sqrt(len(self.genres))))
            for i in range(len(self.genres)):
                self.labels.append(gui.widgetLabel(self.genrebox, self.genres[i]))

    def set_data(self, data):
        self.data = data

        if data.relation.col_type.name == "Actors":
            self.row_names = data.relation.col_names
            self.row_type = data.relation.col_type
            self.matrix, self.genres = actor_genre_matrix(actors=self.row_names)

        elif data.relation.row_type.name == "Movies":
            self.row_names = data.relation.row_names
            self.row_type = data.relation.row_type
            self.matrix, self.genres = movie_concept_matrix(self.row_names, concept="genre")

        else:
            raise ValueError("Can produce genres only for movies or actors.")

        self.update_genres()
        self.send_output()

    def send_output(self):
        if self.data is not None:
            relation = skfusion.fusion.Relation(self.matrix, self.row_type, ObjectType("Genres"),
                                                row_names=self.row_names, col_names=self.genres)
            self.send("Genres", Relation(relation))

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWMovieGenres()
    #ow.set_data(movies)
    ow.show()
    app.exec_()