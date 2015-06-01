from io import BytesIO

from PyQt4 import QtCore, QtGui, QtSvg, QtWebKit
from Orange.widgets import widget, gui, settings

from skfusion import fusion
from orangecontrib.datafusion.widgets import owfusiongraph
from orangecontrib.datafusion.widgets.owfusiongraph import \
    WebviewWidget, relation_str, _get_selected_nodes
from orangecontrib.datafusion.table import Relation

from os import path
JS_FACTORS = open(path.join(path.dirname(__file__), 'factors_script.js')).read()

import re

from itertools import filterfalse


def is_constraint(relation):
    """Skip constraint (Theta) relations"""
    return relation.row_type == relation.col_type


from itertools import count
GENERATE_OTYPE = (fusion.ObjectType('LatentSpace' + str(i)) for i in count())


def to_orange_data_table(data, graph):
    arr, otype = data
    col_type = next(GENERATE_OTYPE)
    row_type = otype or next(GENERATE_OTYPE)
    row_names = get_otype_names(otype, arr, graph) if otype else None
    return Relation(fusion.Relation(arr, row_type, col_type, row_names=row_names))


from itertools import chain


def get_otype_names(otype, arr, graph):
    """Return row_names from the `otype`s first shape-matching relation"""
    for rel in chain(graph.out_relations(otype), graph.in_relations(otype)):
        if rel.row_type == otype:
            if rel.data.shape[0] == arr.shape[0] and rel.row_names:
                return rel.row_names
        elif rel.col_type == otype:
            if rel.data.shape[1] == arr.shape[1] and rel.col_names:
                return rel.col_names
    return None


class OWLatentFactors(widget.OWWidget):
    name = "Latent Factors"
    priority = 20000
    icon = "icons/latent-factors.svg"
    inputs = [("Fusion graph", fusion.FusionFit, "on_fuser_change")]
    outputs = [("Data", Relation)]

    # Signal emitted when a node in the SVG is selected, carrying its id
    graph_element_selected = QtCore.pyqtSignal(str)
    # Signal to communicate the sizes of matrices on a node / along an edge
    graph_element_get_size = QtCore.pyqtSignal(str)

    autorun = settings.Setting(True)

    def __init__(self):
        super().__init__()
        self.n_relations = 0
        self.n_object_types = 0
        self.graph_element_selected.connect(self._on_graph_element_selected)
        self.graph_element_get_size.connect(self.on_graph_element_get_size)
        self.webview = WebviewWidget(self.mainArea)
        self._create_layout()

    @QtCore.pyqtSlot(str)
    def on_graph_element_get_size(self, element_id):
        """ Return the list of matrix.shape[0] for the selected element(s)
            (node(=factor) or edge(=backbone)).
        """
        selected_is_edge = element_id.startswith('edge ')
        nodes = _get_selected_nodes(element_id, self.fuser.fusion_graph)
        from math import log2

        def _norm(s):
            return min(max(1.3**log2(s), 8), 20)

        if selected_is_edge:
            rels = self.fuser.fusion_graph.get_relations(nodes[0], nodes[1])
            sizes = [_norm(self.fuser.backbone(rel).shape[0])
                     for rel in filterfalse(is_constraint, rels)]
        else:
            sizes = [_norm(self.fuser.factor(nodes[0]).shape[0])]
        self.webview.evalJS('SIZES = {};'.format(repr(sizes)))

    @QtCore.pyqtSlot(str)
    def _on_graph_element_selected(self, element_id):
        self.on_graph_element_selected(element_id)

    def on_graph_element_selected(self, element_id):
        """Handle self.graph_element_selected signal, and highlight also:
           * if edge was selected, the two related nodes,
           * if node was selected, all its edges.
           Additionally, update the info box.
        """
        if not element_id:
            return self.listview.show_all()
        selected_is_edge = element_id.startswith('edge ')
        nodes = _get_selected_nodes(element_id, self.fuser.fusion_graph)
        # Update the control listview table
        if selected_is_edge:
            selected = [self.fuser.backbone(rel)
                        for rel in filterfalse(is_constraint,
                                               self.fuser.fusion_graph.get_relations(*nodes))]
        else:
            selected = [self.fuser.factor(nodes[0])]
        selected = set(self.listview.hash((d, None)) for d in selected)
        self.listview.show_only(selected)

    def _create_layout(self):
        self.mainArea.layout().addWidget(self.webview)
        info = gui.widgetBox(self.controlArea, 'Info')
        gui.label(info, self, '%(n_object_types)d object types')
        gui.label(info, self, '%(n_relations)d relations')
        # Table view of relation details
        info = gui.widgetBox(self.controlArea, 'Factors')

        class HereListWidget(owfusiongraph.OWFusionGraph.SimpleListWidget):
            def hash(self, data):
                return hash(data[0].data.tobytes())

            def send(_, data):
                data = to_orange_data_table(data, self.fuser.fusion_graph)
                self.send('Data', data)

        self.listview = HereListWidget(info)
        self.controlArea.layout().addStretch(1)

    def on_fuser_change(self, fuser):
        self.fuser = fuser
        self.listview.clear()
        for otype, matrices in fuser.factors_.items():
            matrix = matrices[0]
            self.listview.add_item((matrix, otype),
                                   '[{}×{}] {}'.format(matrix.shape[0],
                                                       matrix.shape[1],
                                                       otype.name))
        for relation, matrices in fuser.backbones_.items():
            matrix = matrices[0]
            relation_string = relation_str(relation, False)
            self.listview.add_item((matrix, None),
                                   '[{}×{}] {}'.format(matrix.shape[0],
                                                       matrix.shape[1],
                                                       relation_string))
            matrix = fuser.complete(relation)
            self.listview.add_item((matrix, None),
                                   '[{}×{}] {} (completed)'.format(matrix.shape[0],
                                                                   matrix.shape[1],
                                                                   relation_string))
        self.repaint()
        # this ensures gui.label-s get updated
        self.n_object_types = fuser.fusion_graph.n_object_types
        self.n_relations = fuser.fusion_graph.n_relations

    def repaint(self):
        self.webview.repaint(self.fuser.fusion_graph, self)
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
    w.on_fuser_change(fuser)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
