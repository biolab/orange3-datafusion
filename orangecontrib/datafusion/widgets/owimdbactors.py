import sys
from PyQt4 import QtGui
from orangecontrib.datafusion.models import Relation
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui, settings
from orangecontrib.datafusion import movielens

from skfusion import fusion

MOVIE_ACTORS = "Movie Actors"
ACTORS_ACTORS = "Costarring Actors"


class OWIMDbActors(OWWidget):
    name = "IMDb Actors"
    description = "Construct a movie-actor and actor-actor relation matrix."
    priority = 80000
    icon = "icons/IMDbActors.svg"
    want_main_area = False
    resizing_enabled = False

    inputs = [("Filter", Relation, "set_data")]
    outputs = [(MOVIE_ACTORS, Relation),
               (ACTORS_ACTORS, Relation)]

    percent = settings.Setting(10)

    def __init__(self):
        super().__init__()
        self.movies = None
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

        self.movies = None

    def set_data(self, relation):
        if relation is not None:
            assert isinstance(relation, Relation)
            if relation.col_type == movielens.ObjectType.Movies:
                self.movies = relation.relation.col_names
            elif relation.row_type == movielens.ObjectType.Movies:
                self.movies = relation.relation.row_names
            else:
                self.error(1, "Only relations with ObjectType Movies can be used to filter actors.")

            self.send_output()

    def send_output(self):
        if self.movies is not None:
            movie_actor_mat, actors = movielens.movie_concept_matrix(self.movies, concept="actor",
                                                                     actors=self.percent)
            actor_actor_mat = movielens.actor_matrix(movie_actor_mat)

            movies_actors = fusion.Relation(movie_actor_mat.T, name='play in',
                                            row_type=movielens.ObjectType.Actors, row_names=actors,
                                            col_type=movielens.ObjectType.Movies, col_names=self.movies)
            self.send(MOVIE_ACTORS, Relation(movies_actors))

            actors_actors = fusion.Relation(actor_actor_mat, name='costar with',
                                            row_type=movielens.ObjectType.Actors, row_names=actors,
                                            col_type=movielens.ObjectType.Actors, col_names=actors)
            self.send(ACTORS_ACTORS, Relation(actors_actors))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWIMDbActors()
    # ow.set_data(movies_users)
    ow.show()
    app.exec_()
