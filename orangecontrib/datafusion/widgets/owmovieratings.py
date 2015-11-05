import sys
from PyQt4 import QtGui
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui, settings
from orangecontrib.datafusion.models import Relation
from orangecontrib.datafusion import movielens

from skfusion import fusion

class OWMovieRatings(OWWidget):
    name = "Movie Ratings"
    description = "Construct a relation matrix of user ratings for movies."
    priority = 70000
    icon = "icons/MovieRatings.svg"
    want_main_area = False
    resizing_enabled = False

    outputs = [("Ratings", Relation, widget.Default)]

    percent = settings.Setting(10)  # 10: default is 10% of data
    start = settings.Setting(2005)  # from year 2005 (default)
    end = settings.Setting(2007)    # to year 2007 (default)
    method = settings.Setting(0)    # 0: percentage, 1: years

    def __init__(self):
        super().__init__()

        box = gui.widgetBox(self.controlArea, "Movie Selection (from %d)" % \
            len(movielens.get_all_movie_names()))
        methodbox = gui.radioButtons(
            box, self, "method", callback=self._on_method_changed)

        gui.appendRadioButton(methodbox, "Fraction of movies")
        percent = gui.hSlider(
            gui.indentedBox(methodbox), self, "percent",
            minValue=1, maxValue=100, step=1, ticks=10, labelFormat="%d %%")

        gui.appendRadioButton(methodbox, "Time period:")
        ibox = gui.indentedBox(methodbox)
        start = gui.spin(
            ibox, self, "start", 1907, 2015, 1, label="Starting year: ")
        end = gui.spin(
            ibox, self, "end", 1907, 2015, 1, label="Ending year: ")

        self.method_params = [percent, start, end]

        gui.button(self.controlArea, self, "&Apply",
                   callback=self.send_output, default=True)

        self.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                           QtGui.QSizePolicy.Fixed))

        self.setMinimumWidth(250)
        self.setMaximumWidth(250)
        self._on_method_changed()
        self.send_output()

    def _on_method_changed(self):
        enabled = [[True, False, False], [False, True, True]]
        mask = enabled[self.method]
        for param, enabled in zip(self.method_params, mask):
            param.setEnabled(enabled)

    def send_output(self):
        if self.method == 0:
            matrix, movies, users = movielens.movie_user_matrix(percentage=self.percent)
        else:
            try:
                matrix, movies, users = movielens.movie_user_matrix(start_year=self.start, end_year=self.end)
            except ValueError:
                self.error(0, "Invalid starting years")
                self.send("Ratings", None)

        relation = fusion.Relation(matrix.T, name='rate',
                                   row_type=movielens.ObjectType.Users, row_names=users,
                                   col_type=movielens.ObjectType.Movies, col_names=movies)
        self.send("Ratings", Relation(relation))

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWMovieRatings()
    ow.show()
    app.exec_()
