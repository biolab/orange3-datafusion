import numpy as np

from PyQt4 import QtCore, QtGui
from Orange.widgets import widget, gui, settings
from Orange.widgets.utils.itemmodels import PyTableModel

from skfusion import fusion
from orangecontrib.datafusion.models import Relation, FittedFusionGraph
from orangecontrib.datafusion.widgets.graphview import GraphView, Edge
from orangecontrib.datafusion.widgets.owfusiongraph import rel_cols


class Output:
    RELATION = 'Relation'


class ChainingGraphView(GraphView):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent

    def nodeClicked(self, node):
        self._parent.on_graph_element_selected(node)

    def itemClicked(self, item):
        if isinstance(item, Edge): return
        super().itemClicked(item)


class OWChaining(widget.OWWidget):
    name = "Chaining"
    description = "Profile objects of one type in the feature space of " \
                  "another type through chaining of latent factors."
    priority = 30000
    icon = "icons/LatentChaining.svg"
    inputs = [("Fitted fusion graph", FittedFusionGraph, "on_fuser_change")]
    outputs = [(Output.RELATION, Relation)]

    pref_complete = settings.Setting(0)  # Complete chaining to feature space

    def __init__(self):
        super().__init__()
        self.graphview = ChainingGraphView(self)
        self.startNode = None
        self.endNode = None
        self._create_layout()

    def _create_layout(self):
        self.controlArea = self
        box = gui.widgetBox(self.controlArea, margin=7)
        box.layout().addWidget(self.graphview)
        box = gui.widgetBox(self.controlArea, 'Latent chains')

        class TableView(gui.TableView):
            selected_row = QtCore.pyqtSignal(int)

            def __init__(self, parent):
                super().__init__(parent,
                                 selectionMode=self.SingleSelection)
                self._parent = parent
                self.bold_font = self.BoldFontDelegate(self)   # member because PyQt sometimes unrefs too early
                for column in range(2, 100, 2):
                    self.setItemDelegateForColumn(column, self.bold_font)
                self.horizontalHeader().setVisible(False)

            def selectionChanged(self, selected, deselected):
                super().selectionChanged(selected, deselected)
                self.selected_row.emit(selected.indexes()[0].row() if len(selected) else -1)

        model = self.model = PyTableModel(parent=self)
        table = self.table = TableView(self)
        table.setModel(model)

        def selected_row(row):
            data = None
            if row >= 0:
                chain = self.model[row][0]
                self.graphview.clearSelection()
                self._highlight_relations(chain)
                data = self.fuser.compute_chain(chain, self.pref_complete)
            self.send(Output.RELATION, data)

        table.selected_row.connect(selected_row)
        box.layout().addWidget(table)

        self.controlArea.layout().addWidget(box)

        def on_change_pref_complete():
            rows = self.table.selectionModel().selectedRows()
            self._populate_table(self.chains)
            # Re-apply selection
            if rows:
                self.table.selectRow(rows[0].row())

        gui.radioButtons(box, self, 'pref_complete',
                         label='Complete chain to:',
                         btnLabels=('latent space', 'feature space'),
                         callback=on_change_pref_complete)
        self.controlArea.layout().addStretch(1)

    def _highlight_relations(self, relations):
        for rel in relations:
            row_name, col_name = rel.row_type.name, rel.col_type.name
            node1, node2 = self.graphview.nodes[row_name], self.graphview.nodes[col_name]
            node1.selected = True
            node2.selected = True
            for edge in node1.edges:
                if node2 in edge:
                    edge.selected = True

    def _populate_table(self, chains=[]):
        self.send(Output.RELATION, None)
        model = []
        for chain in chains:
            columns = [str(self.startNode.name)]
            for rel in chain:
                columns += rel_cols(rel)[1:]
            assert columns[-1] == str(self.endNode.name)
            shape = (chain[0]. data.shape[0],
                     chain[-1].data.shape[1] if self.pref_complete else chain[-1].col_type.rank)
            model.append([chain, '{}×{}'.format(*shape)] + columns)
            self._highlight_relations(chain)
        self.model.wrap(model)
        self.table.hideColumn(0)

    def on_fuser_change(self, fuser):
        self.fuser = fuser
        self._populate_table()
        self.graphview.fromFusionFit(fuser)

    def on_graph_element_selected(self, node):
        in_selection_mode = self.startNode and not self.endNode
        if not in_selection_mode:
            self.graphview.clearSelection()
            self.startNode, self.endNode = node, None
        else:
            self.endNode = node
        node.selected = True
        if not (self.startNode and self.endNode):
            return

        def _get_chains(ot1, ot2):
            """ Return all chains of relations that lead from ObjectType `ot1`
                to `ot2`.
            """
            G = self.fuser
            results, paths = [], [(ot1, [])]
            while paths:
                cur, path = paths.pop()
                if cur == ot2 and path:
                    results.append(path)
                    continue
                for rel in G.out_relations(cur):
                    # Discount relations to self, constraints (= prevent cycles)
                    if rel.row_type == rel.col_type: continue
                    # Discount types that are already in path (=prevent cycles)
                    if any(rel.col_type in r for r in path): continue
                    paths.append((rel.col_type, path + [rel]))
            results.sort(key=len)
            return results

        chains = _get_chains(*self.fuser.get_selected_nodes([self.startNode.name, self.endNode.name]))

        # Populate the listview
        self.chains = chains
        self._populate_table(chains)

        # If no chains lead from start to end, reinterpret end as start
        if not chains:
            return self.graphview.nodeClicked(node)


def main():
    # example from https://github.com/marinkaz/scikit-fusion
    import numpy as np
    R12 = np.random.rand(50, 100)
    R32 = np.random.rand(100, 150)
    R33 = np.random.rand(150, 150)
    R13 = np.random.rand(50, 150)
    t1 = fusion.ObjectType('Users', 10)
    t2 = fusion.ObjectType('Movies', 30)
    t3 = fusion.ObjectType('Actors', 40)
    relations = [fusion.Relation(R12, t1, t2, name='like'),
                 fusion.Relation(R13, t1, t3, name='are fans of'),
                 fusion.Relation(R12, t1, t2, name='don\'t like'),
                 fusion.Relation(R33, t3, t3, name='married to'),
                 fusion.Relation(R32, t2, t3, name='feature')]
    G = fusion.FusionGraph()
    for rel in relations:
        G.add_relation(rel)
    fuser = fusion.Dfmf()
    fuser.fuse(G)
    app = QtGui.QApplication([])
    w = OWChaining()
    w.on_fuser_change(FittedFusionGraph(fuser))
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
