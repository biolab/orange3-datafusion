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
    IN_SAMPLE_DATA = "In-sample Data"
    OUT_OF_SAMPLE_DATA = "Out-of-sample Data"


class OWSampleMatrix(OWWidget):
    name = "Matrix Sampler"
    priority = 90000
    icon = "icons/MatrixSampler.svg"
    want_main_area = False
    description = "Sample a data matrix"
    inputs = [("Data", Orange.data.table.Table, "set_data", widget.Default)]
    outputs = [(Output.IN_SAMPLE_DATA, Relation),
               (Output.OUT_OF_SAMPLE_DATA, Relation)]

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

        sample_size = gui.widgetBox(self.controlArea, "Proportion of data in the sample")
        percent = gui.hSlider(
            sample_size, self, 'percent', minValue=1, maxValue=100, step=5,
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
            oos_mask_mask, is_mask = hide_data(self.relation, percentage=self.percent,
                                                    sampling_type=self.METHOD_NAMES[self.method])

            out_of_sample_data = copy.deepcopy(self.relation.relation)
            if np.ma.is_masked(out_of_sample_data.data):
                oos_mask_mask = np.logical_or(oos_mask_mask, out_of_sample_data.data.mask)
            oos_mask_mask = np.logical_or(oos_mask_mask, np.isnan(out_of_sample_data.data))
            out_of_sample_data.data = np.ma.array(out_of_sample_data.data, mask=oos_mask_mask)

            in_sample_data = copy.deepcopy(self.relation.relation)
            if np.ma.is_masked(in_sample_data.data):
                is_mask = np.logical_or(is_mask, in_sample_data.data.mask)
            is_mask = np.logical_or(is_mask, np.isnan(in_sample_data.data))
            in_sample_data.data = np.ma.array(in_sample_data.data, mask=is_mask)

            self.send(Output.IN_SAMPLE_DATA, Relation(in_sample_data))
            self.send(Output.OUT_OF_SAMPLE_DATA, Relation(out_of_sample_data))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWSampleMatrix()
    # ow.set_data(Orange.data.Table("housing.tab"))
    ow.send_output()
    ow.show()
    app.exec_()
