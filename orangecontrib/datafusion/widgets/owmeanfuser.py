
from collections import defaultdict

from PyQt4 import QtGui, QtCore
from Orange.widgets import widget, gui, settings

from skfusion import fusion
from orangecontrib.datafusion.table import Relation
from orangecontrib.datafusion.widgets.owfusiongraph import \
    SimpleTableWidget, rel_shape, rel_cols, RelationCompleter

import numpy as np


class Output:
    FUSER = 'Mean-fitted fusion graph'
    RELATION = 'Relation'


class MeanBy:
    ROWS = 'Rows'
    COLUMNS = 'Columns'
    VALUES = 'All values'
    all = (ROWS, COLUMNS, VALUES)


class MeanFuser(RelationCompleter):
    def __init__(self, mean_by):
        self.axis = {
            MeanBy.ROWS: 0,
            MeanBy.COLUMNS: 1,
            MeanBy.VALUES: None}[MeanBy.all[mean_by]]
        self.mean_by = mean_by

    @property
    def name(self):
        return 'Mean by ' + MeanBy.all[self.mean_by].lower()

    def __getattr__(self, attr):
        return self

    def fuse(self, graph):
        """Mock ``skfusion.fusion.FusionFit.fuse```ensures
           comparison with any relation succeeds.
        """
        return self

    def get_relations(self, *args):
        """Mock ``skfusion.fusion.FusionGraph.get_relations```ensures
           comparison with any relation succeeds.
        """
        class AlwaysEqual:
            def __getattr__(self, attr):
                return self
            def __eq__(self, other):
                return True
        return [AlwaysEqual()]

    def complete(self, relation):
        """Mock ``skfusion.fusion.FusionFit.complete()``"""
        assert isinstance(relation, fusion.Relation)
        A = relation.data.copy()
        if not np.ma.is_masked(A):
            return A
        mean_value = np.nanmean(A, axis=None)
        if self.axis is None:
            # Replace the mask with mean of the matrix
            A[A.mask] = mean_value
        else:
            # Replace the mask with mean by axes
            mean = np.nanmean(A, axis=self.axis)
            # Replace any NaNs in mean with mean of the matrix
            mean[np.isnan(mean)] = mean_value
            A[A.mask] = np.take(mean, A.mask.nonzero()[not self.axis])
        return A


class OWMeanFuser(widget.OWWidget):
    name = 'Mean Fuser'
    priority = 55000
    icon = 'icons/MeanFuser.svg'
    inputs = [
        ('Fusion graph', fusion.FusionGraph, 'on_fusion_graph_change'),
        ('Relation', Relation, 'on_relation_change', widget.Multiple),
    ]
    outputs = [
        (Output.FUSER, MeanFuser, widget.Default),
        (Output.RELATION, Relation)
    ]

    want_main_area = False

    mean_by = settings.Setting(0)
    selected_relation = settings.Setting(0)

    def __init__(self):
        super().__init__()
        self.relations = defaultdict(int)
        self.id_relations = {}
        self._create_layout()
        self.commit()

    def _create_layout(self):
        self.controlArea.layout().addWidget(
            gui.comboBox(self.controlArea, self, 'mean_by',
                         box='Mean fuser',
                         label='Calculate masked values as mean by:',
                         items=MeanBy.all, callback=self.commit))
        box = gui.widgetBox(self.controlArea, 'Output completed relation')
        self.table = SimpleTableWidget(box, callback=self.commit)
        self.controlArea.layout().addStretch(1)

    def commit(self, item=None):
        self.fuser = MeanFuser(self.mean_by)
        self.send(Output.FUSER, self.fuser)
        selection = self.table.selectedRanges()
        if item or self.table.rowCount() and selection:
            if not item:
                row = selection[0].topRow()
                item = self.table.item(row, 0)
            else:
                item = item.tableWidget().item(item.row(), 0)
            relation = item.data(QtCore.Qt.UserRole)
            self.send(Output.RELATION, self.fuser.complete(relation))

    def update_table(self):
        self.table.clear()
        for rel in self.relations:
            self.table.add([(rel_shape(rel.data), rel)]
                           + rel_cols(rel)
                           + [('(not masked)' if not np.ma.is_masked(rel.data) else '')],
                           bold=(1, 3))

    def _add_relation(self, relation):
        self.relations[relation] += 1

    def _remove_relation(self, relation):
        self.relations[relation] -= 1
        if not self.relations[relation]:
            del self.relations[relation]

    def on_fusion_graph_change(self, graph):
        if graph:
            self.graph = graph
            for rel in graph.relations:
                self._add_relation(rel)
        else:
            for rel in self.graph.relations:
                self._remove_relation(rel)
        self.update_table()
        self.commit()

    def on_relation_change(self, relation, id):
        try: self._remove_relation(self.id_relations.pop(id))
        except KeyError: pass
        if relation:
            self.id_relations[id] = relation.relation
            self._add_relation(relation.relation)
        self.update_table()
        self.commit()



def main():
    import numpy as np
    R1 = np.ma.array(np.random.random((20, 20)))
    R2 = np.ma.array(np.random.random((40, 40)),
                     mask=np.random.random((40,40)) > .8)
    t1 = fusion.ObjectType('Users', 10)
    t2 = fusion.ObjectType('Movies', 30)
    t3 = fusion.ObjectType('Actors', 40)
    relations = [
        fusion.Relation(R1, t1, t2, name='like'),
        fusion.Relation(R2, t3, t2, name='feature in'),
    ]
    G = fusion.FusionGraph()
    G.add_relations_from(relations)
    app = QtGui.QApplication([])
    w = OWMeanFuser()
    w.on_fusion_graph_change(G)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
