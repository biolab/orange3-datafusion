import sys
from orangecontrib.datafusion import movielens
import numpy as np
from PyQt4 import QtGui
from PyQt4.QtGui import QGridLayout
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui
from orangecontrib.datafusion.models import Relation

from skfusion import fusion


class OWMovieGenres(OWWidget):
    name = "Movie Genres"
    description = "Construct movies-genres or actors-genres relation matrix."
    priority = 90000
    icon = "icons/MovieGenres.svg"
    want_main_area = False
    resizing_enabled = False

    inputs = [("Row Type", Relation, "set_data", widget.Default)]
    outputs = [("Genres", Relation, widget.Default)]

    def __init__(self):
        super().__init__()
        self.data = None
        self.matrix = None
        self.genres = None
        self.row_names = None
        self.labels = []
        self.row_type = None
        self.relation_name = ""

        self.layout = QGridLayout()
        self.genrebox = gui.widgetBox(self.controlArea, "Genres")

        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                           QtGui.QSizePolicy.Fixed))
        self.setMinimumWidth(250)

    def update_genres(self):
        #print("updating", len(self.genres))
        if self.genres is not None:
            for label in self.labels:
                label.hide()
            size = int(np.ceil(np.sqrt(len(self.genres))))
            for i in range(len(self.genres)):
                self.labels.append(gui.widgetLabel(self.genrebox, self.genres[i]))

    def set_data(self, data):
        self.data = data
        if self.data is not None:
            for type_, names in [(data.relation.row_type, data.relation.row_names),
                                 (data.relation.col_type, data.relation.col_names)]:
                if type_.name == "Actors":
                    self.row_type = type_
                    self.row_names = names
                    self.relation_name = "prefer"
                    self.matrix, self.genres = movielens.actor_genre_matrix(actors=self.row_names)
                    break
                elif type_.name == "Movies":
                    self.row_type = type_
                    self.row_names = names
                    self.relation_name = "fit in"
                    self.matrix, self.genres = movielens.movie_concept_matrix(self.row_names, concept="genre")
                    break
            else:
                raise ValueError("Can produce genres only for movies or actors.")

            self.update_genres()
            self.send_output()

    def send_output(self):
        if self.data is not None:
            relation = fusion.Relation(self.matrix, name=self.relation_name,
                                       row_type=self.row_type, row_names=self.row_names,
                                       col_type=fusion.ObjectType("Genres"), col_names=self.genres)
            self.send("Genres", Relation(relation))

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWMovieGenres()
    #ow.set_data(movies)
    ow.show()
    app.exec_()
