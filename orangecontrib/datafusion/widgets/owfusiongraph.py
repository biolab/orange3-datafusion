from collections import defaultdict

from PyQt4 import QtGui

from Orange.widgets import widget, gui, settings
from Orange.widgets.utils.itemmodels import PyTableModel
from skfusion import fusion
from orangecontrib.datafusion.models import Relation, FusionGraph, FittedFusionGraph
from orangecontrib.datafusion.widgets.graphview import GraphView, Node, Edge


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
    return '[{}] {}'.format(rel_shape(relation.data), ' '.join(rel_cols(relation)))


class FusionGraphView(GraphView):
    def nodeClicked(self, node):
        self.clearSelection()
        for edge in node.edges:
            edge.selected = True
        super().nodeClicked(node)

    def edgeClicked(self, edge):
        self.clearSelection()
        edge.source.selected = True
        edge.dest.selected = True
        super().nodeClicked(edge)


class OWFusionGraph(widget.OWWidget):
    name = "Fusion Graph"
    description = "Construct data fusion graph and run " \
                  "collective matrix factorization."
    priority = 10000
    icon = "icons/FusionGraph.svg"
    inputs = [("Relation", Relation, "on_relation_change", widget.Multiple)]
    outputs = [
        (Output.RELATION, Relation),
        (Output.FUSER, FittedFusionGraph, widget.Default),
        (Output.FUSION_GRAPH, FusionGraph),
    ]

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
        self.graph = FusionGraph(fusion.FusionGraph())
        self.graphview = FusionGraphView(self)
        self.graphview.selectionChanged.connect(self.on_graph_element_selected)
        self._create_layout()

    def on_graph_element_selected(self, selected):
        if not selected:
            return self._populate_table()
        selected_is_edge = isinstance(selected[0], Edge)
        # Update the control table table
        if selected_is_edge:
            edge = next(i for i in selected if isinstance(i, Edge))
            nodes = self.graph.get_selected_nodes([edge.source.name, edge.dest.name])
            relations = self.graph.get_relations(*nodes)
        else:
            node = next(i for i in selected if isinstance(i, Node))
            nodes = self.graph.get_selected_nodes([node.name])
            relations = (set(i for i in self.graph.in_relations(nodes[0])) |
                         set(i for i in self.graph.out_relations(nodes[0])))
        self._populate_table(relations)

    def _create_layout(self):
        self.mainArea.layout().addWidget(self.graphview)
        info = gui.widgetBox(self.controlArea, 'Info')
        gui.label(info, self, '%(n_object_types)d object types')
        gui.label(info, self, '%(n_relations)d relations')
        # Table view of relation details
        info = gui.widgetBox(self.controlArea, 'Relations')

        class TableView(gui.TableView):
            def __init__(self, parent=None, **kwargs):
                super().__init__(parent, **kwargs)
                self._parent = parent
                self.bold_font = self.BoldFontDelegate(self)   # member because PyQt sometimes unrefs too early
                self.setItemDelegateForColumn(2, self.bold_font)
                self.setItemDelegateForColumn(4, self.bold_font)
                self.horizontalHeader().setVisible(False)

            def selectionChanged(self, selected, deselected):
                super().selectionChanged(selected, deselected)
                if not selected:
                    assert len(deselected) > 0
                    relation = None
                else:
                    assert len(selected) == 1
                    data = self._parent.tablemodel[selected[0].top()][0]
                    relation = Relation(data)
                self._parent.send(Output.RELATION, relation)

        model = self.tablemodel = PyTableModel(parent=self)
        table = self.table = TableView(self,
                                       selectionMode=TableView.SingleSelection)
        table.setModel(model)
        info.layout().addWidget(self.table)

        gui.lineEdit(self.controlArea,
                     self, 'pref_algo_name', 'Fuser name:',
                     orientation='horizontal',
                     callback=self.checkcommit)
        gui.radioButtons(self.controlArea,
                         self, 'pref_algorithm', [i[0] for i in DECOMPOSITION_ALGO],
                         box='Decomposition algorithm',
                         callback=self.checkcommit)
        gui.radioButtons(self.controlArea,
                         self, 'pref_initialization', INITIALIZATION_ALGO,
                         box='Initialization algorithm',
                         callback=self.checkcommit)
        slider = gui.hSlider(
            self.controlArea, self, 'pref_n_iterations',
            'Maximum number of iterations',
            minValue=10, maxValue=500, createLabel=True,
            callback=self.checkcommit)
        slider.setTracking(False)
        self.slider_rank = gui.hSlider(self.controlArea, self, 'pref_rank',
                                       'Factorization rank',
                                       minValue=1, maxValue=100, createLabel=True,
                                       labelFormat=" %d%%",
                                       callback=self.checkcommit)
        self.slider_rank.setTracking(False)
        gui.auto_commit(self.controlArea, self, "autorun", "Run",
                        checkbox_label="Run after any change  ")

    def checkcommit(self):
        return self.commit()

    def commit(self):
        self.progressbar = gui.ProgressBar(self, self.pref_n_iterations)
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
        try:
            self.fuser = Algo(init_type=init_type,
                              max_iter=self.pref_n_iterations,
                              random_state=0,
                              callback=lambda *args: self.progressbar.advance()).fuse(self.graph)
        finally:
            self.progressbar.finish()
        self.fuser.name = self.pref_algo_name
        self.send(Output.FUSER, FittedFusionGraph(self.fuser))

    def _populate_table(self, relations=None):
        self.tablemodel.wrap([[rel, rel_shape(rel.data)] + rel_cols(rel)
                              for rel in relations or self.graph.relations])
        self.table.hideColumn(0)
        self.table.selectRow(0)

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

        self.graphview.clear()
        for relation in self.graph.relations:
            self.graphview.addRelation(relation)
        self.graphview.hideSquares()

        self._populate_table()
        LIMIT_RANK_THRESHOLD = 1000  # If so many objects or more, limit maximum rank
        self.slider_rank.setMaximum(30
                                    if any(max(rel.data.shape) > LIMIT_RANK_THRESHOLD
                                           for rel in self.graph.relations)
                                    else
                                    100)
        self.send(Output.FUSION_GRAPH, FusionGraph(self.graph))
        # this ensures gui.label-s get updated
        self.n_object_types = self.graph.n_object_types
        self.n_relations = self.graph.n_relations

    # called when all signals are received, so the graph is updated only once
    def handleNewSignals(self):
        self.commit()


def main():
    # example from https://github.com/marinkaz/scikit-fusion
    import numpy as np
    R12 = np.random.rand(50, 100)
    R22 = np.random.rand(100, 100)
    R13 = np.random.rand(50, 40)
    R31 = np.random.rand(40, 50)
    R23 = np.random.rand(100, 40)
    R23 = np.random.rand(100, 40)
    R24 = np.random.rand(100, 40)
    R34 = np.random.rand(40, 40)
    t1 = fusion.ObjectType('Users', 10)
    t2 = fusion.ObjectType('Actors', 20)
    t3 = fusion.ObjectType('Movies', 30)
    t4 = fusion.ObjectType('Genres', 40)
    relations = [fusion.Relation(R12, t1, t2, name='like'),
                 fusion.Relation(R13, t1, t3, name='rated'),
                 fusion.Relation(R13, t1, t3, name='mated'),
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
