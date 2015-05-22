from collections import OrderedDict

from PyQt4 import QtCore, QtGui
from Orange.widgets import widget, gui

from skfusion import fusion
from orangecontrib.datafusion.table import Relation
from orangecontrib.datafusion.widgets.owfusiongraph import relation_str

import numpy as np


def RMSE(A, B):
    """ NaN-skipping RMSE of masked values beetween the original relation `A`
        and fuser-completed relation `B`.
    """
    A, B, size = A.data[A.mask], B[A.mask], A.mask.sum()
    return np.sqrt(np.nansum((A - B)**2) / size)


def _find_completion(fuser, relation):
    """Returns `fuser`-completed relation that matches `relation`, or None"""
    for fuser_relation in fuser.fusion_graph.get_relations(relation.row_type,
                                                           relation.col_type):
        if fuser_relation._id == relation._id:
            return fuser.complete(fuser_relation)
    return None

class OWCompletionScoring(widget.OWWidget):
    name = 'Completion Scoring'
    icon = 'icons/completion-scoring.svg'
    inputs = [
        ('Fitted fusion graph', fusion.FusionFit, 'on_fuser_change', widget.Multiple),
        ('Relation', Relation, 'on_relation_change', widget.Multiple),
    ]

    want_main_area = True
    want_control_area = False

    def __init__(self):
        super().__init__()
        self.fusers = OrderedDict()
        self.relations = OrderedDict()
        self._create_layout()

    class SimpleTableWidget(QtGui.QTableWidget):
        def __init__(self, parent):
            super().__init__(parent)
            parent.layout().addWidget(self)
        def appendRow(self, row_values):
            self.setSortingEnabled(False)
            row = self.rowCount()
            self.insertRow(row)
            for col, value in enumerate(row_values):
                item = QtGui.QTableWidgetItem(str(data))
                self.setItem(row, col, item)
            self.setSortingEnabled(True)

    def _create_layout(self):
        box = gui.widgetBox(self.mainArea, 'Fuser completion scoring')
        grey_brush = QtGui.QBrush(QtGui.QColor('#eee'))
        BOLD_FONT = QtGui.QFont()
        BOLD_FONT.setWeight(QtGui.QFont.DemiBold)
        class HereTableWidget(self.__class__.SimpleTableWidget):
            def update_table(self, fusers, relations):
                self.clear()
                self.setRowCount(0)
                self.setColumnCount(len(fusers))
                self.setHorizontalHeaderLabels([getattr(fuser, 'name', str(id))
                                                for id, fuser in fusers.items()])
                for relation in relations.values():
                    row = self.rowCount()
                    self.insertRow(row)
                    rmses = []
                    for fuser in fusers.values():
                        completion = _find_completion(fuser, relation)
                        if completion is not None:
                            rmses.append(RMSE(relation.data, completion))
                        else:
                            rmses.append(None)
                    min_rmse = min(filter(lambda i: i is not None, rmses))
                    for col, rmse in enumerate(rmses):
                        item = QtGui.QTableWidgetItem(str(rmse or ''))
                        item.setFlags(QtCore.Qt.ItemIsEnabled)
                        if rmse == min_rmse and len(rmses) > 1:
                            item.setFont(BOLD_FONT)
                        self.setItem(row, col, item)
                self.resizeColumnsToContents()
                self.setVerticalHeaderLabels([relation_str(i, False) for i in relations.values()])

        self.table = HereTableWidget(box)

    def update(self):
        self.table.update_table(self.fusers, self.relations)

    def on_fuser_change(self, fuser, id):
        if fuser: self.fusers[id] = fuser
        else: del self.fusers[id]
        self.update()

    def on_relation_change(self, relation, id):
        if relation: self.relations[id] = relation.relation
        else:    del self.relations[id]
        self.update()


def main():
    from sklearn.datasets import make_blobs
    import numpy as np
    X, y = make_blobs(100, 3, centers=2, center_box=(-100, 100), cluster_std=10)
    X = X.astype(int)
    X += abs(X.min())
    nrows, ncols, _ = X.max(0)
    R = np.zeros((nrows + 1, ncols + 1))
    R[:,:] = 0
    R[X[:,0], X[:,1]] = X[:,2]
    R = np.ma.array((R - R.min()) / (R.max() - R.min()))

    from copy import deepcopy
    R12 = np.ma.array(np.random.rand(50, 100))
    R23 = np.ma.array(np.random.rand(150, 100))
    t1 = fusion.ObjectType('Users', 10)
    t2 = fusion.ObjectType('Movies', 30)
    t3 = fusion.ObjectType('Actors', 40)
    relations = [fusion.Relation(R, t1, t2, name='like')]
    G = fusion.FusionGraph()
    for relation in relations:
        relation.data.mask = np.random.rand(*relation.data.shape) > .8
        G.add_relation(relation)
    fuserF = fusion.Dfmf()
    fuserF.fuse(G)

    G = deepcopy(G)
    #~ G.remove_relation(relations[1])
    fuserC = fusion.Dfmc()
    fuserC.name = 'My dfmc<3'
    fuserC.fuse(G)

    app = QtGui.QApplication([])
    w = OWCompletionScoring()
    w.on_fuser_change(fuserF, fuserF.__class__.__name__)
    w.on_fuser_change(fuserC, fuserC.__class__.__name__)
    for i,relation in enumerate(relations, 1):
        w.on_relation_change(Relation(relation), i)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
