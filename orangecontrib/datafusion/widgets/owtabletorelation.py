from PyQt4.QtGui import QTableView, QSizePolicy, QHeaderView, QGridLayout, QWidget
from PyQt4.QtCore import Qt, QSize
from Orange.data import Table, Domain
from Orange.widgets.settings import Setting, ContextSetting, PerfectDomainContextHandler
from Orange.widgets.utils.itemmodels import TableModel
from Orange.widgets.widget import OWWidget
from Orange.widgets import gui
from orangecontrib.datafusion.table import Relation
from skfusion import fusion


class Output:
    RELATION = 'Relation'


class OWTableToRelation(OWWidget):
    name = "Table to Relation"

    inputs = [("Data", Table, "set_data")]
    outputs = [(Output.RELATION, Relation)]

    settingsHandler = PerfectDomainContextHandler()

    data = None

    relation_name = ContextSetting("")
    transpose = ContextSetting(False)

    row_type = ContextSetting("")
    row_names_attribute = ContextSetting("")
    row_names = None

    col_type = ContextSetting("")
    col_names = None

    auto_commit = Setting(False)

    def __init__(self):
        super().__init__()

        rel = gui.widgetBox(self.controlArea, "Relation")
        gui.lineEdit(rel, self, "relation_name", "Name", callbackOnType=True, callback=self.commit)
        gui.checkBox(rel, self, "transpose", "Transpose")

        col = gui.widgetBox(self.controlArea, "Column")
        gui.lineEdit(col, self, "col_type", "Object Type", callbackOnType=True, callback=self.commit)

        row = gui.widgetBox(self.controlArea, "Row")
        gui.lineEdit(row, self, "row_type", "Object Type", callbackOnType=True, callback=self.commit)
        self.row_names_combo = gui.comboBox(row, self, "row_names_attribute", label="Object Names",
                                            sendSelectedValue=True, emptyString="(None)",
                                            callback=self.update_row_names)

        gui.rubber(self.controlArea)
        gui.auto_commit(self.controlArea, self, "auto_commit", "Send")
        self.icons = gui.attributeIconDict

        grid = QWidget()
        grid.setLayout(QGridLayout(grid))
        self.mainArea.layout().addWidget(grid)

        col_type = gui.label(None, self, '%(col_type)s')

        grid.layout().addWidget(col_type, 0, 1)
        grid.layout().setAlignment(col_type, Qt.AlignHCenter)

        row_type = gui.label(None, self, '%(row_type)s')
        grid.layout().addWidget(row_type, 1, 0)
        grid.layout().setAlignment(row_type, Qt.AlignVCenter)

        self.view = QTableView()
        self.model = None
        grid.layout().addWidget(self.view, 1, 1)

    def sizeHint(self):
        return QSize(800, 500)

    def set_data(self, data):
        self.closeContext()
        self.data = data
        if data is not None:
            self.init_attr_values(data.domain.metas)
            self.openContext(self.data)
        else:
            self.init_attr_values(())
        self.update_preview()
        self.update_row_names()
        self.unconditional_commit()

    def init_attr_values(self, candidates):
        self.col_type = ""
        self.col_names = None

        if candidates:
            self.row_type = candidates[0].name
            self.row_names_attribute = candidates[0]
        else:
            self.row_type = ""
            self.row_names_attribute = ""
            self.row_names = None

        self.row_names_combo.clear()
        self.row_names_combo.addItem('(None)')
        for var in candidates:
            self.row_names_combo.addItem(self.icons[var], var.name)

    def update_row_names(self):
        if not self.row_names_attribute:
            self.row_names = None
        else:
            self.row_names = list(self.data[:, self.row_names_attribute].metas.flatten())

        if self.model:
            self.model.headerDataChanged.emit(
                Qt.Vertical, 0, self.model.rowCount() - 1)
        self.commit()

    def update_preview(self):
        this = self

        class MyTableModel(TableModel):
            def headerData(self, section, orientation, role):
                if orientation == Qt.Vertical and role == Qt.DisplayRole:
                    if this.row_names:
                        return this.row_names[section]
                else:
                    return super().headerData(section, orientation, role)

        domain = Domain(self.data.domain.attributes)
        preview_data = Table(domain, self.data)
        self.model = MyTableModel(preview_data)
        self.view.setModel(self.model)

    def commit(self):
        if self.data:
            if self.transpose:
                relation = fusion.Relation(
                    self.data.X, name=self.relation_name,
                    row_type=fusion.ObjectType(self.col_type or 'Unknown'), row_names=self.col_names,
                    col_type=fusion.ObjectType(self.row_type or 'Unknown'), col_names=self.row_names)
            else:
                relation = fusion.Relation(
                    self.data.X, name=self.relation_name,
                    row_type=fusion.ObjectType(self.row_type or 'Unknown'), row_names=self.row_names,
                    col_type=fusion.ObjectType(self.col_type or 'Unknown'), col_names=self.col_names)
            self.send(Output.RELATION, Relation(relation))


if __name__ == '__main__':
    from PyQt4.QtGui import QApplication
    import Orange
    app = QApplication([])
    ow = OWTableToRelation()
    ow.set_data(Orange.data.Table('zoo'))
    ow.show()
    app.exec()
    ow.saveSettings()
