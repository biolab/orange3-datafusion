import numpy as np

from PyQt4 import QtCore, QtGui
from Orange.widgets import widget, gui, settings

from skfusion import fusion
from orangecontrib.datafusion.models import Relation, FittedFusionGraph
from orangecontrib.datafusion.widgets import owlatentfactors
from orangecontrib.datafusion.widgets.owfusiongraph import rel_cols, bold_item


class Output:
    RELATION = 'Relation'


class OWChaining(owlatentfactors.OWLatentFactors):
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
        self.in_selection_mode = False

    def _create_layout(self):
        self.controlArea = self
        box = gui.widgetBox(self.controlArea, margin=7)
        box.layout().addWidget(self.webview)
        box = gui.widgetBox(self.controlArea, 'Latent chains')
        self.table = gui.TableWidget(box, select_rows=True)
        self.table.setColumnFilter(bold_item, lambda col: col % 2)

        def selectionChanged(selected, _):
            if not selected:
                data = None
            else:
                chain = self.table.rowData(selected[0].top())
                self.webview.evalJS('dehighlight(ELEMENTS);')
                self._highlight_relations(chain)
                data = self.fuser.compute_chain(chain, self.pref_complete)
            self.send(Output.RELATION, data)

        self.table.selectionChanged = selectionChanged
        self.controlArea.layout().addWidget(box)

        def on_change_pref_complete():
            ranges = self.table.selectedRanges()
            self._populate_table(self.chains)
            # Re-apply selection
            if ranges:
                self.table.selectRow(ranges[0].topRow())

        gui.radioButtons(box, self, 'pref_complete',
                         label='Complete chain to:',
                         btnLabels=('latent space', 'feature space'),
                         callback=on_change_pref_complete)
        self.controlArea.layout().addStretch(1)

    def _highlight_relations(self, relations):
        escape = lambda s: s.replace(' ', r'\\ ')
        selectors = set()
        for rel in relations:
            row_name, col_name = escape(rel.row_type.name), escape(rel.col_type.name)
            selectors.add('.node[id*={}]'.format(row_name))
            selectors.add('.node[id*={}]'.format(col_name))
            selectors.add('.edge[id*={}][id*={}]'.format(row_name, col_name))
        self.webview.evalJS('highlight("{}");'.format(','.join(selectors)))

    def _populate_table(self, chains=[]):
        self.table.clear()
        self.send(Output.RELATION, None)
        for chain in chains:
            columns = [str(self.selected_start)]
            for rel in chain:
                columns += rel_cols(rel)[1:]
            assert columns[-1] == str(self.selected_end)
            shape = (chain[0]. data.shape[0],
                     chain[-1].data.shape[1] if self.pref_complete else chain[-1].col_type.rank)
            self.table.addRow(['{}×{}'.format(*shape)] + columns, data=chain)
            self._highlight_relations(chain)

    def on_fuser_change(self, fuser):
        self.fuser = fuser
        self._populate_table()
        self.repaint()

    def on_graph_element_selected(self, element_id):
        if not element_id:
            self.in_selection_mode = False
            return self._populate_table()
        nodes = self.fuser.get_selected_nodes(element_id)
        selected_is_edge = len(nodes) > 1
        if selected_is_edge:
            self.webview.evalJS('dehighlight(ELEMENTS);')
            self.in_selection_mode = False
            return self._populate_table()
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
        chains = _get_chains(self.selected_start, self.selected_end)

        # Populate the listview
        self.chains = chains
        self._populate_table(chains)

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
    w.on_fuser_change(FittedFusionGraph(fuser))
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
