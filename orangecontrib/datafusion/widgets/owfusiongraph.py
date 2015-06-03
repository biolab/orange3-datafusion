from io import BytesIO
from collections import defaultdict

from PyQt4 import QtCore, QtGui, QtSvg, QtWebKit
from Orange.widgets import widget, gui, settings

from skfusion import fusion
from orangecontrib.datafusion.table import Relation

from os import path
JS_GRAPH = open(path.join(path.dirname(__file__), 'graph_script.js')).read()

import re

DECOMPOSITION_ALGO = [
    ('Matrix tri-factorization', fusion.Dfmf),
    ('Matrix tri-completion', fusion.Dfmc),
]
INITIALIZATION_ALGO = [
    'Random',
    'Random C',
    'Random Vcol'
]


class Output:
    RELATION = 'Relation'
    FUSION_GRAPH = 'Fusion Graph'
    FUSER = 'Fitted Fusion Graph'


def rel_shape(relation):
    return '{}×{}'.format(*relation.shape)

def rel_cols(relation):
    return [relation.row_type.name,
            relation.name or '→',
            relation.col_type.name]

def relation_str(relation):
    return '[{}] {}'.format(rel_shape(relation), ' '.join(rel_cols(relation)))

def _get_selected_nodes(element_id, graph):
    """ Return ObjectTypes from FusionGraph `graph` that correspond to
        selected `element_id` in the webview.
    """
    selected_is_edge = element_id.startswith('edge ')
    assert element_id.startswith('edge ') or element_id.startswith('node ')
    # Assumes SVG element's id attributes specify nodes `-delimited
    node_names = re.findall('`([^`]+)`', element_id)
    nodes = [graph.get_object_type(name) for name in node_names]
    assert len(nodes) == 2 if selected_is_edge else len(nodes) == 1
    return nodes


class WebviewWidget(QtWebKit.QWebView):
    def __init__(self, parent):
        super().__init__(parent)
        parent.layout().addWidget(self)
        settings = self.settings()
        if __debug__:  # TODO
            settings.setAttribute(settings.DeveloperExtrasEnabled, True)
        else:
            self.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def sizeHint(self):
        return QtCore.QSize(500, 500)

    def evalJS(self, javascript):
        self.page().mainFrame().evaluateJavaScript(javascript)

    def repaint(self, graph, parent):
        stream = BytesIO()
        graph.draw_graphviz(stream, 'svg')
        stream.seek(0)
        stream = QtCore.QByteArray(stream.read())
        self.setContent(stream, 'image/svg+xml')
        webframe = self.page().mainFrame()
        webframe.addToJavaScriptWindowObject('pybridge', parent)
        webframe.evaluateJavaScript(JS_GRAPH)


class SimpleTableWidget(QtGui.QTableWidget):
    """ A wrapper around QTableWidget """
    def __init__(self, parent=None, callback=None):
        """`callback` is a function that accepts first selected row item"""
        super().__init__(parent)
        self.callback = callback
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.setSelectionMode(self.SingleSelection)
        self.setSelectionBehavior(self.SelectRows)
        self.setEditTriggers(self.NoEditTriggers);
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.currentItemChanged.connect(self._on_currentItemChanged)
        if parent: parent.layout().addWidget(self)

    def add(self, items, bold=()):
        """Appends iterable of `items` as the next row.

        `bold` is a list of columns that are to be set in bold face.
        """
        row = self.rowCount()
        self.insertRow(row)
        self.setColumnCount(max(len(items), self.columnCount()))
        for col, data in enumerate(items):
            try: name, data = data
            except ValueError: name = str(data)
            item = QtGui.QTableWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, data)
            if col in bold:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.setItem(row, col, item)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def clear(self):
        super().clear()
        self.setRowCount(0)
        self.setColumnCount(0)

    def select_first(self):
        if self.rowCount() > 0:
            self.selectRow(0)

    def _on_currentItemChanged(self, current, previous):
        if self.callback and current:
            item = self.item(current.row(), 0)
            return self.callback(item)


LIMIT_RANK_THRESHOLD = 1000  # If so many objects or more, limit maximum rank


class OWFusionGraph(widget.OWWidget):
    name = "Fusion Graph"
    priority = 10000
    icon = "icons/fusion-graph.svg"
    inputs = [("Relation", Relation, "on_relation_change", widget.Multiple)]
    outputs = [
        (Output.RELATION, Relation),
        (Output.FUSER, fusion.FusionFit, widget.Default),
        (Output.FUSION_GRAPH, fusion.FusionGraph),
    ]

    # Signal emitted when a node in the SVG is selected, carrying its name
    graph_element_selected = QtCore.pyqtSignal(str)

    pref_algo_name = settings.Setting('')
    pref_algorithm = settings.Setting(0)
    pref_initialization = settings.Setting(0)
    pref_n_iterations = settings.Setting(10)
    pref_rank = settings.Setting(10)
    autorun = settings.Setting(False)

    def __init__(self):
        super().__init__()
        self.n_object_types = 0
        self.n_relations = 0
        self.relations = {}  # id-->relation map
        self.graph_element_selected.connect(self.on_graph_element_selected)
        self.graph = fusion.FusionGraph()
        self.webview = WebviewWidget(self.mainArea)
        self._create_layout()

    @QtCore.pyqtSlot(str)
    def on_graph_element_selected(self, element_id):
        """Handle self.graph_element_selected signal, and highlight also:
           * if edge was selected, the two related nodes,
           * if node was selected, all its edges.
           Additionally, update the info box.
        """
        if not element_id:
            return self._populate_table()
        selected_is_edge = element_id.startswith('edge ')
        nodes = _get_selected_nodes(element_id, self.graph)
        # CSS selector query for selection-relevant nodes
        selector = ','.join('[id^="node "][id*="`%s`"]' % n.name for n in nodes)
        # If a node was selected, include the edges that connect to it
        if not selected_is_edge:
            selector += ',[id^="edge "][id*="`%s`"]' % nodes[0].name
        # Highlight these additional elements
        self.webview.evalJS("highlight('%s');" % selector)
        # Update the control table table
        if selected_is_edge:
            relations = self.graph.get_relations(*nodes)
        else:
            relations = (set(i for i in self.graph.in_relations(nodes[0])) |
                         set(i for i in self.graph.out_relations(nodes[0])))
        self._populate_table(relations)

    def _create_layout(self):
        info = gui.widgetBox(self.controlArea, 'Info')
        gui.label(info, self, '%(n_object_types)d object types')
        gui.label(info, self, '%(n_relations)d relations')
        # Table view of relation details
        info = gui.widgetBox(self.controlArea, 'Relations')
        def send_relation(item):
            data = item.data(QtCore.Qt.UserRole)
            self.send(Output.RELATION, Relation(data))
        self.table = SimpleTableWidget(info, callback=send_relation)
        self.controlArea.layout().addStretch(1)
        gui.lineEdit(self.controlArea,
                     self, 'pref_algo_name', 'Fuser name',
                     callback=self.checkcommit, enterPlaceholder=True)
        gui.radioButtons(self.controlArea,
                         self, 'pref_algorithm', [i[0] for i in DECOMPOSITION_ALGO],
                         box='Decomposition algorithm',
                         callback=self.checkcommit)
        gui.radioButtons(self.controlArea,
                         self, 'pref_initialization', INITIALIZATION_ALGO,
                         box='Initialization algorithm',
                         callback=self.checkcommit)
        gui.hSlider(self.controlArea, self, 'pref_n_iterations',
                    'Maximum number of iterations',
                    minValue=10, maxValue=500, createLabel=True,
                    callback=self.checkcommit)
        self.slider_rank = gui.hSlider(self.controlArea, self, 'pref_rank',
                    'Factorization rank',
                    minValue=1, maxValue=100, createLabel=True, labelFormat=" %d%%",
                    callback=self.checkcommit)
        gui.auto_commit(self.controlArea, self, "autorun", "Run",
                        checkbox_label="Run after any change  ")

    def checkcommit(self):
        return self.commit()

    def commit(self):
        Algo = DECOMPOSITION_ALGO[self.pref_algorithm][1]
        init_type = INITIALIZATION_ALGO[self.pref_initialization].lower().replace(' ', '_')
        # Update rank on object-types
        maxrank = defaultdict(int)
        for rel in self.graph.relations:
            rows, cols = rel.data.shape
            row_type, col_type = rel.row_type, rel.col_type
            if rows > maxrank[row_type]:
                maxrank[row_type] = row_type.rank = max(5, int(rows * (self.pref_rank / 100)))
            if cols > maxrank[col_type]:
                maxrank[col_type] = col_type.rank = max(5, int(cols * (self.pref_rank / 100)))
        # Run the algo ...
        self.fuser = Algo(init_type=init_type,
                          max_iter=self.pref_n_iterations).fuse(self.graph)
        self.fuser.name = self.pref_algo_name
        self.send(Output.FUSER, self.fuser)

    def _populate_table(self, relations=None):
        self.table.clear()
        for i in relations or self.graph.relations:
            self.table.add([(rel_shape(i.data), i)] + rel_cols(i), bold=(1,3))
        self.table.select_first()

    def on_relation_change(self, relation, id):
        def _on_remove_relation(id):
            try: relation = self.relations.pop(id)
            except KeyError: return
            self.graph.remove_relation(relation)

        def _on_add_relation(relation, id):
            _on_remove_relation(id)
            self.relations[id] = relation
            self.graph.add_relation(relation)

        if relation:
            _on_add_relation(relation.relation, id)
        else:
            _on_remove_relation(id)
        self._populate_table()
        self.slider_rank.setMaximum(30
                                    if any(max(rel.data.shape) > LIMIT_RANK_THRESHOLD
                                           for rel in self.graph.relations)
                                    else
                                    100)
        self.webview.repaint(self.graph, self)
        self.send(Output.FUSION_GRAPH, self.graph)
        # this ensures gui.label-s get updated
        self.n_object_types = self.graph.n_object_types
        self.n_relations = self.graph.n_relations


def main():
    # example from https://github.com/marinkaz/scikit-fusion
    import numpy as np
    R12 = np.random.rand(50, 100)
    R22 = np.random.rand(100, 100)
    R13 = np.random.rand(50, 40)
    R31 = np.random.rand(40, 50)
    R23 = np.random.rand(100, 40)
    R23 = np.random.rand(100, 40)
    R24 = np.random.rand(100, 400)
    R34 = np.random.rand(40, 400)
    t1 = fusion.ObjectType('Users', 10)
    t2 = fusion.ObjectType('Actors', 20)
    t3 = fusion.ObjectType('Movies', 30)
    t4 = fusion.ObjectType('Genres', 40)
    relations = [fusion.Relation(R12, t1, t2, name='like'),
                 fusion.Relation(R13, t1, t3, name='rated'),
                 fusion.Relation(R23, t2, t3, name='play in'),
                 fusion.Relation(R31, t3, t1),
                 fusion.Relation(R24, t2, t4, name='prefer'),
                 fusion.Relation(R34, t3, t4, name='belong to'),
                 fusion.Relation(R22, t2, t2, name='married to')]

    app = QtGui.QApplication(['asdf'])
    w = OWFusionGraph()
    w.show()

    def _add_next_relation(event,
                           id=iter(range(len(relations))),
                           relation=iter(map(Relation, relations))):
        try: w.on_relation_change(next(relation), next(id))
        except StopIteration:
            w.killTimer(w.timer_id)
            w.on_relation_change(None, 4)  # Remove relation #4
    w.timerEvent = _add_next_relation
    w.timer_id = w.startTimer(500)
    app.exec()


if __name__ == "__main__":
    main()
