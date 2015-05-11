from io import BytesIO

from PyQt4 import QtCore, QtGui, QtSvg, QtWebKit
from Orange.widgets import widget, gui

from skfusion import fusion

from os import path
CSS_FILE = path.join(path.dirname(__file__), 'graph_style.css')
JAVASCRIPT_FILE = path.join(path.dirname(__file__), 'graph_script.js')
assert path.exists(CSS_FILE)
JAVASCRIPT_CONTENT = open(JAVASCRIPT_FILE).read()

import re


class OWFusionGraph(widget.OWWidget):
    name = "Fusion Graph"
    icon = "icons/fusion-graph.svg"
    inputs = [("fusion.Relation", fusion.Relation, "on_add_relation", widget.Multiple)]
    outputs = [("fusion.Relation", fusion.Relation)]

    # Signal emitted when a node in the SVG is selected, carrying its name
    graph_element_selected = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.n_object_types = 0
        self.n_relations = 0
        self.graph_element_selected.connect(self.on_graph_element_selected)
        self.graph = fusion.FusionGraph()
        self.webview = QtWebKit.QWebView(self.mainArea)
        settings = self.webview.settings()
        def _path2url(path):
            from urllib.parse import urljoin
            from urllib.request import pathname2url
            return urljoin('file:', pathname2url(path))
        settings.setUserStyleSheetUrl(QtCore.QUrl(_path2url(CSS_FILE)))
        if __debug__:  # TODO
            settings.setAttribute(settings.DeveloperExtrasEnabled, True)
        else:
            self.webview.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self._create_layout()

    @QtCore.pyqtSlot(str)
    def on_graph_element_selected(self, element_id):
        """Handle self.graph_element_selected signal, and highlight also:
           * if edge was selected, the two related nodes,
           * if node was selected, all its edges.
           Additionally, update the info box.
        """
        selected_is_edge = element_id.startswith('edge ')
        assert element_id.startswith('edge ') or element_id.startswith('node ')
        node_names = re.findall('`([^`]+)`', element_id)
        nodes = [self.graph.get_object_type(name) for name in node_names]
        assert len(nodes) == 2 if selected_is_edge else len(nodes) == 1
        # CSS selector query for selection-relevant nodes
        selector = ','.join('[id^="node "][id*="`%s`"]' % n.name for n in nodes)
        # If a node was selected, include the edges that connect to it
        if not selected_is_edge:
            selector += ',[id^="edge "][id*="`%s`"]' % nodes[0].name
        # Highlight these additional elements
        self.evalJS("highlight('%s');" % selector)
        # Update the control listview table
        if selected_is_edge:
            selected_relations = set(self.graph.get_relations(*nodes))
        else:
            selected_relations = (set(self.graph.in_relations(nodes[0])) |
                                  set(self.graph.out_relations(nodes[0])))
        self.listview.show_only(selected_relations)

    def _create_layout(self):
        self.mainArea.layout().addWidget(self.webview)
        info = gui.widgetBox(self.controlArea, 'Info')
        gui.label(info, self, '%(n_object_types)d object types')
        gui.label(info, self, '%(n_relations)d relations')
        # Table view of relation details
        info = gui.widgetBox(self.controlArea, 'Relations')
        class OurListWidget(QtGui.QListWidget):
            def __init__(self, parent):
                super().__init__(parent)
                self.setHorizontalScrollMode(self.ScrollPerPixel)
                self.setSelectionMode(self.SingleSelection)
                self.setAlternatingRowColors(True)
            def new_item_from(self, relation):
                name = '%6d %s %s %d %s' % (relation.data.shape[0],
                                            relation.row_type.name,
                                            relation.name or '→',
                                            relation.data.shape[1],
                                            relation.col_type.name)
                item = QtGui.QListWidgetItem(name, self)
                item.setData(QtCore.Qt.UserRole, relation)
                self.addItem(item)
            def show_only(self, shown):
                for i in range(self.count()):
                    item = self.item(i)
                    item.setHidden(item.data(QtCore.Qt.UserRole) not in shown)
            def currentItemChanged(_, current, previous):
                relation = current.getData(QtCore.Qt.UserRole)
                self.send(self.outputs[0][0], relation)
        self.listview = OurListWidget(info)
        info.layout().addWidget(self.listview)
        self.controlArea.layout().addStretch(1)

    def on_add_relation(self, relation):
        self.graph.add_relation(relation)
        self.repaint(self.graph)
        self.listview.new_item_from(relation)
        # this ensures gui.label-s get updated
        self.n_object_types = self.graph.n_object_types
        self.n_relations = self.graph.n_relations

    def evalJS(self, javascript):
        self.webview.page().mainFrame().evaluateJavaScript(javascript)

    def repaint(self, graph):
        stream = BytesIO()
        graph.draw_graphviz(stream, 'svg')
        stream.seek(0)
        stream = QtCore.QByteArray(stream.read())
        self.webview.setContent(stream, 'image/svg+xml')
        webframe = self.webview.page().mainFrame()
        webframe.addToJavaScriptWindowObject('pybridge', self)
        webframe.evaluateJavaScript(JAVASCRIPT_CONTENT)
        super().repaint()


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
    def _add_next_relation(event, relation=iter(relations)):
        try: w.on_add_relation(next(relation))
        except StopIteration: w.killTimer(w.timer_id)
    w.timerEvent = _add_next_relation
    w.timer_id = w.startTimer(500)
    app.exec()


if __name__ == "__main__":
    main()
