import sys
import copy
import Orange.data.table
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui, settings
from orangecontrib.datafusion.movielens import hide_data
from orangecontrib.datafusion.table import Relation
from skfusion import fusion

import numpy as np


class Output:
    REMAINING_DATA = "Remaining Data"
    HIDDEN_DATA = "Hidden Data"


class OWHideData(OWWidget):
    name = "Hide Data"
    icon = "icons/sampling.svg"
    want_main_area = False
    description = "Hide part of relation data"
    inputs = [("Data", Orange.data.table.Table, "set_data", widget.Default)]
    outputs = [(Output.REMAINING_DATA, Relation, widget.Default),
               (Output.HIDDEN_DATA, Relation, widget.Default)]

    percent = settings.Setting(10)
    method = settings.Setting(0)
    bools = settings.Setting([])

    METHOD_NAMES = ["Rows", "Columns", "Rows and columns", "Entries"]

    def __init__(self):
        super().__init__()
        self.relation = None

        form = QtGui.QGridLayout()
        methodbox = gui.radioButtonsInBox(
            self.controlArea, self, "method", [],
            box=self.tr("Sampling method"), orientation=form)

        rows = gui.appendRadioButton(methodbox, "Rows", addToLayout=False)
        form.addWidget(rows, 0, 0, Qt.AlignLeft)

        cols = gui.appendRadioButton(methodbox, "Columns", addToLayout=False)
        form.addWidget(cols, 0, 1, Qt.AlignLeft)

        rows_and_cols = gui.appendRadioButton(methodbox, "Rows and columns", addToLayout=False)
        form.addWidget(rows_and_cols, 1, 0, Qt.AlignLeft)

        entries = gui.appendRadioButton(methodbox, "Entries", addToLayout=False)
        form.addWidget(entries, 1, 1, Qt.AlignLeft)

        sample_size = gui.widgetBox(self.controlArea, "Sample size")
        percent = gui.hSlider(
            sample_size, self, 'percent', minValue=1, maxValue=100, step=1,
            ticks=10, labelFormat=" %d%%")

        gui.button(self.controlArea, self, "&Apply",
                   callback=self.send_output, default=True)

        self.setSizePolicy(
            QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                              QtGui.QSizePolicy.Fixed))

        self.setMinimumWidth(250)
        self.send_output()

    def set_data(self, data):
        self.relation = data
        self.send_output()

    def send_output(self):
        if self.relation is not None:
            remaining_mask, hidden_mask = hide_data(self.relation, percentage=self.percent,
                                                    sampling_type=self.METHOD_NAMES[self.method])

            remaining_data = copy.copy(self.relation.relation)
            remaining_data.data = np.ma.array(remaining_data.data, mask=remaining_mask)
            hidden_data = copy.copy(self.relation.relation)
            hidden_data.data = np.ma.array(hidden_data.data, mask=hidden_mask)

            self.send(Output.REMAINING_DATA, Relation(remaining_data))
            self.send(Output.HIDDEN_DATA, Relation(hidden_data))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWHideData()
    # ow.set_data(Orange.data.Table("housing.tab"))
    ow.send_output()
    ow.show()
    app.exec_()
