import numpy as np

from PyQt4 import QtCore, QtGui, QtSvg, QtWebKit
from Orange.widgets import widget, gui, settings

from skfusion import fusion
from orangecontrib.datafusion.table import Relation
from orangecontrib.datafusion.widgets.owlatentfactors import (
    OWLatentFactors, to_orange_data_table
)
from orangecontrib.datafusion.widgets.owfusiongraph import OWFusionGraph


class OWChaining(OWLatentFactors):
    name = "Chaining"
    icon = "icons/latent-chaining.svg"
    inputs = [("Fusion graph", fusion.FusionFit, "on_fuser_change")]
    outputs = [("Data", Relation)]

    def __init__(self):
        super().__init__()
        self.in_selection_mode = False

    def _create_layout(self):
        super()._create_layout()
        def send(data):
            if data:
                result = self.fuser.factor(data[0].row_type)
                for rel in data:
                    result = np.dot(result, self.fuser.backbone(rel))
                data = to_orange_data_table(result)
            self.send('Data', data)
        def _on_currentItemChanged(current,
                                   previous,
                                   oldhandler=self.listview.on_currentItemChanged):
            data = oldhandler(current, previous)
            if not data: return
            OWFusionGraph.evalJS(self, 'dehighlight(ELEMENTS);')
            self._highlight_relations(data)
        self.listview.send = send
        self.listview.on_currentItemChanged = _on_currentItemChanged

    def _highlight_relations(self, relations):
        selectors = set()
        for rel in relations:
            selectors.add('.node[id*={}]'.format(rel.row_type.name))
            selectors.add('.node[id*={}]'.format(rel.col_type.name))
            selectors.add('.edge[id*={}][id*={}]'.format(rel.row_type.name,
                                                             rel.col_type.name))
        OWFusionGraph.evalJS(self, 'highlight("{}");'.format(','.join(selectors)))

    def on_fuser_change(self, fuser):
        super().on_fuser_change(fuser)
        self.listview.clear()

    def on_graph_element_selected(self, element_id):
        if not element_id:
            self.listview.clear()
            self.in_selection_mode = False
            return
        nodes = OWFusionGraph._get_selected_nodes(element_id, self.fuser.fusion_graph)
        selected_is_edge = len(nodes) > 1
        if selected_is_edge:
            OWFusionGraph.evalJS(self, 'dehighlight(ELEMENTS);')
            self.listview.clear()
            self.in_selection_mode = False
            return
        if not self.in_selection_mode:
            self.selected_start, self.selected_end = nodes[0], None
            self.in_selection_mode = True
        else:
            self.selected_end = nodes[0]
            self.in_selection_mode = False
        if not (self.selected_start and self.selected_end):
            return

        def _get_chains(ot1, ot2):
            """ Return all chains of relations that lead from ObjectType `ot1`
                to `ot2`.
            """
            G = self.fuser.fusion_graph
            results, paths = [], [(ot1, [])]
            while paths:
                cur, path = paths.pop()
                if cur == ot2:
                    results.append(path)
                    continue
                for rel in G.out_relations(cur):
                    # Discount types that are already in path (=prevent cycles)
                    if any(rel.col_type in r for r in path):
                        continue
                    paths.append((rel.col_type, path + [rel]))
            results.sort(key=len)
            return results
        chains = _get_chains(self.selected_start, self.selected_end)

        # Populate the listview
        self.listview.clear()
        for chain in chains:
            parts = [str(self.selected_start)]
            for rel in chain:
                parts.append(rel.name or '→')
                parts.append(str(rel.col_type))
            assert parts[-1] == str(self.selected_end)
            self.listview.add_item(chain, ' '.join(parts))
            self._highlight_relations(chain)

        # If no chains lead from start to end, reinterpret end as start
        if not chains:
            self.on_graph_element_selected(element_id)


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
    w.on_fuser_change(fuser)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
