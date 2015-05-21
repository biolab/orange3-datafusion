import sys
import copy
import Orange.data.table
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from Orange.widgets.widget import OWWidget
from Orange.widgets import widget, gui, settings
from orangecontrib.datafusion.movielens import sample_matrix
from orangecontrib.datafusion.table import Relation


class OWSample(OWWidget):
    name = "Sample"
    icon = "icons/sampling.svg"
    want_main_area = False
    description = "Sample a Relation"
    inputs = [("Data", Orange.data.table.Table, "set_data", widget.Default)]
    outputs = [("Sample data", Relation, widget.Default),
               ("Out of sample data", Relation, widget.Default)]

    percent = settings.Setting(10)
    method = settings.Setting(0)
    bools = settings.Setting([])

    METHOD_NAMES = ["Rows", "Columns", "Rows and columns", "Entries"]

    def __init__(self):
        super().__init__()
        self.data = None

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
            ticks=False, labelFormat=" %d%%")

        gui.button(self.controlArea, self, "&Apply",
                   callback=self.send_output, default=True)

        self.setSizePolicy(
            QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                              QtGui.QSizePolicy.Fixed))

        self.setMinimumWidth(350)
        self.send_output()

    def set_data(self, data):
        self.data = data
        self.send_output()

    def send_output(self):
        if self.data is not None:
            sample_mask, oos_mask = sample_matrix(self.data, percentage=self.percent,
                                                  sampling_type=self.METHOD_NAMES[self.method])

            relation_sample, relation_oos = copy.deepcopy(self.data), copy.deepcopy(self.data)
            relation_sample.relation.mask = sample_mask
            relation_oos.relation.mask = oos_mask

            self.send("Sample data", relation_sample)
            self.send("Out of sample data", relation_oos)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    ow = OWSample()
    #ow.set_data(Orange.data.Table("housing.tab"))
    ow.send_output()
    ow.show()
    app.exec_()