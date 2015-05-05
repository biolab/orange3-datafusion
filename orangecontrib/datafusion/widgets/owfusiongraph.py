from io import BytesIO

from PyQt4 import QtCore, QtGui, QtSvg, QtWebKit
from Orange.widgets import widget, gui

from skfusion import fusion


class OWFusionGraph(widget.OWWidget):
    name = "Fusion Graph"
    icon = "icons/fusion-graph.svg"
    inputs = [("Relation", fusion.Relation, "add_relation", widget.Multiple)]


    def __init__(self):
        super().__init__()
        self.graph = fusion.FusionGraph()
        self.webview = QtWebKit.QWebView(self.mainArea)
        self.mainArea.layout().addWidget(self.webview)

    def add_relation(self, relation):
        self.graph.add_relation(relation)
        self.repaint(self.graph)

    def repaint(self, graph):
        stream = BytesIO()
        graph.draw_graphviz(stream, 'svg')
        stream.seek(0)
        stream = QtCore.QByteArray(stream.read())
        self.webview.setContent(stream, 'image/svg+xml')
        super().repaint()


def main():
    # example from https://github.com/marinkaz/scikit-fusion
    import numpy as np
    R12 = np.random.rand(50, 100)
    R13 = np.random.rand(50, 40)
    R31 = np.random.rand(150, 20)
    R23 = np.random.rand(100, 40)
    R23 = np.random.rand(100, 40)
    t1 = fusion.ObjectType('Type 1', 10)
    t2 = fusion.ObjectType('Type 2', 20)
    t3 = fusion.ObjectType('Type 3', 30)
    relations = [fusion.Relation(R12, t1, t2),
                 fusion.Relation(R13, t1, t3),
                 fusion.Relation(R23, t2, t3),
                 fusion.Relation(R31, t3, t1),
                 fusion.Relation(R13, t3, t1),
                 fusion.Relation(R13, t1, t1)]

    app = QtGui.QApplication(['asdf'])
    w = OWFusionGraph()
    w.show()
    def _add_next_relation(event, relation=iter(relations)):
        try: w.add_relation(next(relation))
        except StopIteration: w.killTimer(w.timer_id)
    w.timerEvent = _add_next_relation
    w.timer_id = w.startTimer(1000)
    app.exec()


if __name__ == "__main__":
    main()
