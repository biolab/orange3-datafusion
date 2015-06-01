
from PyQt4 import QtGui
from Orange.widgets import widget, gui, settings

from skfusion import fusion
from orangecontrib.datafusion.table import Relation
from orangecontrib.datafusion.widgets.owfusiongraph import relation_str

import numpy as np


class Output:
    FUSER = 'Mean-fitted fusion graph'
    RELATION = 'Relation'


class MeanBy:
    ROWS = 'Rows'
    COLUMNS = 'Columns'
    VALUES = 'All values'
    all = (ROWS, COLUMNS, VALUES)


class MeanFuser:
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
        A = relation.data
        if not np.ma.is_masked(A):
            return A
        mean = np.nanmean(A, axis=self.axis)
        A = A.copy()
        A[A.mask] = mean if self.axis is None else np.take(mean, A.mask.nonzero()[not self.axis])
        return A


class OWMeanFuser(widget.OWWidget):
    name = 'Mean Fuser'
    icon = 'icons/mean-fuser.svg'
    inputs = [
        ('Fusion graph', fusion.FusionGraph, 'on_fusion_graph_change'),
    ]
    outputs = [
        (Output.FUSER, MeanFuser, widget.Default),
        (Output.RELATION, Relation)
    ]

    want_main_area = False

    mean_by = settings.Setting(0)
    selected_relation = settings.Setting([])
    relations = settings.Setting([])


    def __init__(self):
        super().__init__()
        self._relations = []
        self._create_layout()
        self.commit()

    def _create_layout(self):
        self.controlArea.layout().addWidget(
            gui.comboBox(self.controlArea, self, 'mean_by',
                box='Mean fuser',
                label='Calculate masked values as mean by:',
                items=MeanBy.all, callback=self.commit))
        self.controlArea.layout().addWidget(
            gui.listBox(self.controlArea, self, 'selected_relation',
                box='Output completed relation',
                labels='relations',
                callback=self.commit))
        self.controlArea.layout().addStretch(1)

    def commit(self):
        self.fuser = MeanFuser(self.mean_by)
        self.send(Output.FUSER, self.fuser)
        if self.selected_relation and self._relations:
            relation = self._relations[self.selected_relation[0]]
            self.send(Output.RELATION, self.fuser.complete(relation))

    def on_fusion_graph_change(self, graph):
        self._relations = [rel for rel in graph.relations]
        self.relations = [relation_str(rel) +
                          (' (not masked)' if not np.ma.is_masked(rel.data) else '')
                          for rel in self._relations]
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
