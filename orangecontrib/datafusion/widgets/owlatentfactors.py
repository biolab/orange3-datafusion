from os import path

from PyQt4 import QtCore, QtGui

from Orange.widgets import widget, gui, settings
from skfusion import fusion
from orangecontrib.datafusion.widgets.owfusiongraph import \
    redraw_graph, rel_shape, rel_cols, bold_item
from orangecontrib.datafusion.models import Relation, FittedFusionGraph


JS_FACTORS = open(path.join(path.dirname(__file__), 'factors_script.js'), encoding='utf-8').read()


def is_constraint(relation):
    """Skip constraint (Theta) relations"""
    return relation.row_type == relation.col_type


class Output:
    RELATION = 'Relation'


class OWLatentFactors(widget.OWWidget):
    name = "Latent Factors"
    description = "Visualize data fusion graph with latent factors. Can " \
                  "select a latent factor for further analysis."
    priority = 20000
    icon = "icons/LatentFactors.svg"
    inputs = [("Fitted fusion graph", FittedFusionGraph, "on_fuser_change")]
    outputs = [(Output.RELATION, Relation)]

    # Signal emitted when a node in the SVG is selected, carrying its id
    graph_element_selected = QtCore.pyqtSignal(str)
    # Signal to communicate the sizes of matrices on a node / along an edge
    graph_element_get_size = QtCore.pyqtSignal(str)

    autorun = settings.Setting(True)

    completions = settings.Setting([])
    selected_completions = settings.Setting([])
    factors = settings.Setting([])
    selected_factors = settings.Setting([])
    backbones = settings.Setting([])
    selected_backbones = settings.Setting([])

    def __init__(self):
        super().__init__()
        self.n_relations = 0
        self.n_object_types = 0
        self.graph_element_selected.connect(self._on_graph_element_selected)
        self.graph_element_get_size.connect(self.on_graph_element_get_size)
        self.webview = gui.WebviewWidget(self.mainArea, self)
        self._create_layout()

    @QtCore.pyqtSlot(str)
    def on_graph_element_get_size(self, element_id):
        """ Return the list of matrix.shape[0] for the selected element(s)
            (node(=factor) or edge(=backbone)).
        """
        selected_is_edge = element_id.startswith('edge ')
        nodes = self.fuser.get_selected_nodes(element_id)
        from math import log2

        def _norm(s):
            return min(max(1.3**log2(s), 8), 20)

        if selected_is_edge:
            rels = self.fuser.get_relations(nodes[0], nodes[1])
            sizes = [_norm(self.fuser.backbone(rel).shape[0])
                     for rel in rels
                     if not is_constraint(rel)]
        else:
            sizes = [_norm(self.fuser.factor(nodes[0]).shape[0])]
        self.webview.evalJS('SIZES = {};'.format(repr(sizes)))

    @QtCore.pyqtSlot(str)
    def _on_graph_element_selected(self, element_id):
        self.on_graph_element_selected(element_id)

    def on_graph_element_selected(self, element_id):
        """Handle graph_element_selected signal, and update the info boxen"""
        if not element_id:
            return self._populate_tables(reset=True)
        selected_is_edge = element_id.startswith('edge ')
        nodes = self.fuser.get_selected_nodes(element_id)
        # Update the control listview table
        if selected_is_edge:
            backbones = [(rel, (self.fuser.backbone(rel),))
                         for rel in self.fuser.get_relations(*nodes)
                         if not is_constraint(rel)]
            self._populate_tables(backbones=backbones)
            self.table_backbones.selectFirstRow()
        else:
            self._populate_tables(factors=[(nodes[0], (self.fuser.factor(nodes[0]),))])
            self.table_factors.selectFirstRow()

    def _create_layout(self):
        info = gui.widgetBox(self.controlArea, 'Info')
        gui.label(info, self, '%(n_object_types)d object types')
        gui.label(info, self, '%(n_relations)d relations')

        box = gui.widgetBox(self.controlArea, 'Recipe factors')
        self.table_factors = gui.TableWidget(box, select_rows=True)
        self.table_factors.setColumnFilter(bold_item, 1)
        self.controlArea.layout().addWidget(box)

        box = gui.widgetBox(self.controlArea, 'Backbone factors')
        self.table_backbones = gui.TableWidget(box, select_rows=True)
        self.table_backbones.setColumnFilter(bold_item, (1, 3))
        self.controlArea.layout().addWidget(box)

        box = gui.widgetBox(self.controlArea, 'Completed relations')
        self.table_completions = gui.TableWidget(box, select_rows=True)
        self.table_completions.setColumnFilter(bold_item, (1, 3))
        self.controlArea.layout().addWidget(box)

        self.controlArea.layout().addStretch(1)

        def _on_selected_factor(item):
            self.table_completions.clearSelection()
            self.table_backbones.clearSelection()
            self.commit(item)

        def _on_selected_backbone(item):
            self.table_completions.clearSelection()
            self.table_factors.clearSelection()
            self.commit(item)

        def _on_selected_completion(item):
            self.table_factors.clearSelection()
            self.table_backbones.clearSelection()
            self.commit(item)

        def on_selection_changed(table, itemChanged_handler):
            def _f(selected, deselected):
                if not selected:
                    return self.commit(None)
                itemChanged_handler(table.item(selected[0].top(), 0))
            return _f

        self.table_factors.selectionChanged = on_selection_changed(self.table_factors, _on_selected_factor)
        self.table_backbones.selectionChanged = on_selection_changed(self.table_backbones, _on_selected_backbone)
        self.table_completions.selectionChanged = on_selection_changed(self.table_completions, _on_selected_completion)

    def commit(self, item):
        data = Relation.create(*item.tableWidget().rowData(item.row()), graph=self.fuser) if item else None
        self.send(Output.RELATION, data)

    def _populate_tables(self, factors=None, backbones=None, reset=False):
        self.table_factors.clear()
        self.table_backbones.clear()
        self.send(Output.RELATION, None)
        if factors or reset:
            for otype, matrices in factors or self.fuser.factors_.items():
                M = matrices[0]
                self.table_factors.addRow((rel_shape(M.data), otype.name), data=(M, otype, None))
        if backbones or reset:
            for relation, matrices in backbones or self.fuser.backbones_.items():
                M = matrices[0]
                self.table_backbones.addRow([rel_shape(M.data)] + rel_cols(relation), data=(M, None, None))
        if reset:
            self.table_completions.clear()
            for rel, matrices in self.fuser.backbones_.items():
                M = self.fuser.complete(rel)
                self.table_completions.addRow([rel_shape(M.data)] + rel_cols(rel), data=(M, rel.row_type, rel.col_type))

    def on_fuser_change(self, fuser):
        self.fuser = fuser
        self._populate_tables(reset=True)
        self.repaint()
        # this ensures gui.label-s get updated
        self.n_object_types = fuser.n_object_types
        self.n_relations = fuser.n_relations

    def repaint(self):
        redraw_graph(self.webview, self.fuser)
        self.webview.evalJS(JS_FACTORS)


def main():
    # example from https://github.com/marinkaz/scikit-fusion
    import numpy as np
    R12 = np.random.rand(50, 100)
    R32 = np.random.rand(150, 100)
    R33 = np.random.rand(150, 150)
    t1 = fusion.ObjectType('Users', 10)
    t2 = fusion.ObjectType('Movies', 30)
    t3 = fusion.ObjectType('Actors', 40)
    relations = [fusion.Relation(R12, t1, t2, name='like'),
                 fusion.Relation(R12, t1, t2, name='don\'t like'),
                 fusion.Relation(R33, t3, t3, name='married to'),
                 fusion.Relation(R32, t3, t2, name='play in')]
    G = fusion.FusionGraph()
    for rel in relations:
        G.add_relation(rel)
    fuser = fusion.Dfmf()
    fuser.fuse(G)
    app = QtGui.QApplication([])
    w = OWLatentFactors()
    w.on_fuser_change(FittedFusionGraph(fuser))
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
