
from math import sin, cos, acos, pi as PI
from collections import OrderedDict
from threading import Lock
from itertools import chain
from functools import wraps

import numpy as np

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt4.QtGui import qApp, QBrush, QPen, QPolygonF, QStyle, QColor, QFont

def pp(i):
    return i.pos().x(), i.pos().y()


def shape_line_intersection(shape, shape_pos, line):
    """ Return point of intersection between shape and line that is
        closest to line.p1().
    """
    intersections, point = [], QPointF()
    p1 = shape.pointAtPercent(0) + shape_pos
    r = shape.boundingRect()
    for t in np.linspace(0, 1.01, 50) % 1:
        p2 = shape.pointAtPercent(t) + shape_pos
        if QLineF(p1, p2).intersect(line, point) == QLineF.BoundedIntersection:
            intersections.append(QPointF(point))
        p1 = p2
    return min(intersections,
               key=lambda point: QLineF(line.p1(), point).length())


class TextItem(QtGui.QGraphicsSimpleTextItem):
    def __init__(self, text, parent):
        super().__init__(text)
        self._parent = parent
        self.setZValue(3)
    def parentItem(self):
        return self._parent


class GroupOfSquares(QtGui.QGraphicsItemGroup):
    def __init__(self, parent):
        super().__init__(parent)
        self.setZValue(2)

    def selected(self, value):
        for item in self.childItems():
            item.setBrush(QColor('red' if value else 'pink'))

    def addSquare(self, size):
        size = np.clip(1.3**np.log2(size**.5), 8, 20)
        item = QtGui.QGraphicsRectItem(self)
        offset = len(self.childItems())
        item.setRect(offset*3, offset*2, size, size)
        item.setPen(QColor('maroon'))
        item.setBrush(QColor('pink'))
        self.selected(False)
        self.addToGroup(item)

    def placeBelow(self, item):
        pos = item.pos()
        self.setPos(pos.x(), pos.y() + item.boundingRect().height())


class _SelectableItem:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected = False

    @property
    def selected(self):
        return self._selected


class Edge(_SelectableItem, QtGui.QGraphicsLineItem):

    ARROW_SIZE = 16

    class Font:
        DEFAULT = QFont('Sans', 12, QFont.Normal)
        SELECTED = QFont('Sans', 12, QFont.DemiBold)

    class Color:
        # = pen color, font brush
        DEFAULT = Qt.gray, QBrush(Qt.black)
        SELECTED = QColor('#dd4455'), QBrush(QColor('#770000'))

    def __init__(self, source, dest):
        super().__init__()
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)  # Without this, burn thy CPU
        self.setZValue(1)
        pen = QPen(Edge.Color.DEFAULT[0], 1)
        pen.setJoinStyle(Qt.MiterJoin)
        self.setPen(pen)
        self.arrowHead = QtGui.QPolygonF()
        self._selected = False
        self._weights = []
        self._labels = []
        self.squares = GroupOfSquares(self)

        self.source = source
        self.dest = dest
        if source is dest:
            source.edges.append(self)
        else:
            source.edges.insert(0, self)
            dest.edges.insert(0, self)

        # Add text labels
        label = self.label = TextItem('', self)
        label.setFont(Edge.Font.DEFAULT)
        label.setZValue(3)
        self.adjust()

    def addRelation(self, name, shape, is_constraint):
        if not is_constraint:
            self.squares.addSquare(np.multiply(*shape))
        self._labels.append((name, shape))

        tooltip = '\n'.join('{} ({}×{})'.format(i[0], *i[1])
                            for i in self._labels)
        self.setToolTip(tooltip)
        self.label.setToolTip(tooltip)
        self.squares.setToolTip(tooltip)

        text = ', '.join(i[0] for i in self._labels)
        text = text[:15] + ('…' if len(text) > 15 else '')
        self.label.setText(text)

    def __contains__(self, node):
        return node == self.source or node == self.dest

    def weight(self): return sum(self._weights)
    def addWeight(self, weight): self._weights.append(weight)

    @_SelectableItem.selected.setter
    def selected(self, value):
        self._selected = value
        pencolor, fontbrush = Edge.Color.SELECTED if value else Edge.Color.DEFAULT
        pen = self.pen()
        pen.setColor(QColor(pencolor))
        self.setPen(pen)
        self.label.setBrush(fontbrush)
        self.label.setFont(Edge.Font.SELECTED if value else Edge.Font.DEFAULT)
        self.squares.selected(value)

    def adjust(self):
        line = QLineF(self.source.pos(), self.dest.pos())
        self.setLine(line)
        self.label.setPos(line.pointAt(.5) - self.label.boundingRect().center())
        self.squares.placeBelow(self.label)

    def boundingRect(self):
        extra = (self.pen().width() + Edge.ARROW_SIZE) / 2
        p1, p2 = self.line().p1(), self.line().p2()
        return QtCore.QRectF(p1, QtCore.QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)
    def shape(self):
        path = super().shape()
        path.addPolygon(self.arrowHead)
        return path

    def _arrowhead_points(self, line):
        ARROW_WIDTH = 2.5
        angle = acos(line.dx() / line.length())
        if line.dy() >= 0: angle = 2*PI - angle
        p1 = line.p2() - QPointF(sin(angle + PI / ARROW_WIDTH) * Edge.ARROW_SIZE,
                                 cos(angle + PI / ARROW_WIDTH) * Edge.ARROW_SIZE)
        p2 = line.p2() - QPointF(sin(angle + PI - PI / ARROW_WIDTH) * Edge.ARROW_SIZE,
                                 cos(angle + PI - PI / ARROW_WIDTH) * Edge.ARROW_SIZE)
        return line.p2(), p1, p2

    def paintArc(self, painter, option, widget):
        assert self.source is self.dest
        node = self.source
        def best_angle():
            """...is the one furthest away from all other angles"""
            angles = [QLineF(node.pos(), other.pos()).angle()
                      for other in chain((edge.source for edge in node.edges
                                          if edge.dest == node and edge.source != node),
                                         (edge.dest for edge in node.edges
                                          if edge.dest != node and edge.source == node))]
            angles.sort()
            if not angles:  # If this self-constraint is the only edge
                return 225
            deltas = np.array(angles[1:] + [360 + angles[0]]) - angles
            return (angles[deltas.argmax()] + deltas.max()/2) % 360

        angle = best_angle()
        inf = QPointF(-1e20, -1e20)  # Doesn't work with real -np.inf!
        line0 = QLineF(node.pos(), inf)
        line1 = QLineF(node.pos(), inf)
        line2 = QLineF(node.pos(), inf)
        line0.setAngle(angle)
        line1.setAngle(angle - 13)
        line2.setAngle(angle + 13)

        p0 = shape_line_intersection(node.shape(), node.pos(), line0)
        p1 = shape_line_intersection(node.shape(), node.pos(), line1)
        p2 = shape_line_intersection(node.shape(), node.pos(), line2)
        path = QtGui.QPainterPath()
        path.moveTo(p1)
        line = QLineF(node.pos(), p0)
        line.setLength(3*line.length())
        pt = line.p2()
        path.quadTo(pt, p2)

        line = QLineF(node.pos(), pt)
        self.setLine(line)  # This invalidates DeviceCoordinateCache
        painter.drawPath(path)

        # Draw arrow head
        line = QLineF(pt, p2)
        self.arrowHead.clear()
        for point in self._arrowhead_points(line):
            self.arrowHead.append(point)
        painter.setBrush(self.pen().color())
        painter.drawPolygon(self.arrowHead)

        # Update label position
        self.label.setPos(path.pointAtPercent(.5))
        if 90 < angle < 270:  # Right-align the label
            pos = self.label.pos()
            x, y = pos.x(), pos.y()
            self.label.setPos(x - self.label.boundingRect().width(), y)
        self.squares.placeBelow(self.label)
    def paint(self, painter, option, widget=None):
        color, _ = Edge.Color.SELECTED if self.selected else Edge.Color.DEFAULT
        pen = self.pen()
        pen.setColor(color)
        pen.setBrush(QBrush(color))
        pen.setWidth(np.clip(2 * self.weight(), .5, 4))
        painter.setPen(pen)
        self.setPen(pen)

        if self.source == self.dest:
            return self.paintArc(painter, option, widget)
        if self.source.collidesWithItem(self.dest):
            return

        have_two_edges = len([edge for edge in self.source.edges
                              if self.source in edge and self.dest in edge and edge is not self])

        source_pos = self.source.pos()
        dest_pos = self.dest.pos()

        color = self.pen().color()
        painter.setBrush(color)

        point = shape_line_intersection(self.dest.shape(), dest_pos,
                                        QLineF(source_pos, dest_pos))
        line = QLineF(source_pos, point)
        if have_two_edges:
            normal = line.normalVector()
            normal.setLength(15)
            line = QLineF(normal.p2(), point)
            self.label.setPos(line.pointAt(.5))
            self.squares.placeBelow(self.label)

        self.setLine(line)
        painter.drawLine(line)

        # Draw arrow head
        self.arrowHead.clear()
        for point in self._arrowhead_points(line):
            self.arrowHead.append(point)
        painter.drawPolygon(self.arrowHead)


class Node(_SelectableItem, QtGui.QGraphicsEllipseItem):
    """
    This class provides an interface for all the bells & whistles of the
    Network Explorer.
    """
    class Style:
        DEFAULT = QPen(Qt.black, 2), QBrush(Qt.white)
        SELECTED = QPen(QColor('#880000'), 2), QBrush(QColor('#ffcc33'))

    class Font:
        TITLE = QFont('Sans', 14, QFont.Bold)
        SUBTITLE = QFont('Sans', 10, QFont.Normal)

    @_SelectableItem.selected.setter
    def selected(self, value):
        self._selected = value
        pen, brush = Node.Style.SELECTED if value else Node.Style.DEFAULT
        self.setPen(pen)
        self.setBrush(brush)
        self.title.setBrush(pen.brush())
        self.squares.selected(value)

    def __init__(self, title, rank):
        super().__init__()
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCacheMode(self.DeviceCoordinateCache)
        self.setZValue(10)
        self.edges = []
        self.name = title
        self.squares = GroupOfSquares(self)
        # Add text labels
        if len(title) > 20: title = title[:20] + '…'
        title = self.title = QtGui.QGraphicsSimpleTextItem(title, self)
        subtitle = self.subtitle = QtGui.QGraphicsSimpleTextItem('', self)
        self.rank = rank
        title.setFont(Node.Font.TITLE)
        subtitle.setFont(Node.Font.SUBTITLE)
        title.setZValue(12)
        subtitle.setZValue(11)
        # Set node's rect accoring to title size
        title = self.title.boundingRect()
        NODE_WIDTH, NODE_HEIGHT = 1.4, 3
        self.setRect(-NODE_WIDTH/2*title.width(), -NODE_HEIGHT/2*title.height(),
                     NODE_WIDTH*title.width(), NODE_HEIGHT*title.height())
        self.selected = False

    @property
    def rank(self): return self._rank
    @rank.setter
    def rank(self, value):
        self._rank = value
        self.subtitle.setText(str(value))
        if self.squares.childItems():
            last = self.squares.childItems()[0]
            self.squares.removeFromGroup(last)
            last.scene().removeItem(last)
        self.squares.addSquare(value**2)

    def setPos(self, x, y):
        super().setPos(x, y)
        self.adjust()
    def adjust(self):
        # Adjust edges
        for edge in self.edges:
            edge.adjust()
        # Adjust title position
        center = self.boundingRect().center()
        cx, cy = center.x(), center.y()
        rect = self.title.boundingRect()
        w, h = rect.width(), rect.height()
        self.title.setPos(cx - w/2, cy - h/2 + 2)
        # Adjust squares
        self.squares.setPos(cx, cx + h/2)
        # Adjust subtitle
        rect = self.subtitle.boundingRect()
        w2, h2 = rect.width(), rect.height()
        self.subtitle.setPos(cx - w2/2, cy - h2/2 - h/2 - 2)


class GraphView(QtGui.QGraphicsView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = OrderedDict()
        self.edges = []

        self.setScene(QtGui.QGraphicsScene(self))
        self.setCacheMode(self.CacheBackground)
        self.setViewportUpdateMode(self.FullViewportUpdate)

        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setResizeAnchor(self.AnchorViewCenter)

        self.setRenderHints(QtGui.QPainter.Antialiasing |
                            QtGui.QPainter.TextAntialiasing)

    def hideSquares(self):
        for i in chain(self.nodes.values(), self.edges):
            i.squares.setVisible(False)

    def clear(self):
        self.scene().clear()
        self.scene().setSceneRect(QRectF())
        self.nodes.clear()
        self.edges.clear()

    def fromFusionFit(self, fuser):
        self.clear()
        if not fuser: return
        for relation in fuser.relations:
            edge = self.addRelation(relation)
            if edge.source is edge.dest:
                edge.squares.setVisible(False)
                continue
            last_rect = edge.squares.childItems()[-1]
            edge.squares.removeFromGroup(last_rect)
            last_rect.scene().removeItem(last_rect)
            size = fuser.backbone(relation).shape[0]
            edge.squares.addSquare(size)

    def addRelation(self, relation):
        ot1, ot2 = relation.row_type.name, relation.col_type.name
        rank1, rank2 = relation.data.shape
        rel_name = relation.name or ('Θ' if ot1 == ot2 else 'R')

        node1 = self.nodes.get(ot1)
        if not node1:
            node1 = self.nodes[ot1] = Node(ot1, rank1)
            self.scene().addItem(node1)
        elif node1.rank < rank1:
            node1.rank = rank1

        node2 = self.nodes.get(ot2)
        if not node2:
            node2 = self.nodes[ot2] = Node(ot2, rank2)
            self.scene().addItem(node2)
        elif node2.rank < rank2:
            node2.rank = rank2

        try:
            edge = next(edge for edge in node1.edges
                        if edge.source is node1 and edge.dest is node2)
        except StopIteration:
            edge = Edge(node1, node2)
            self.scene().addItem(edge)
            self.scene().addItem(edge.label)
            pos = int(node1 is node2) * (len(self.edges) + 1)
            self.edges.insert(pos, edge)

        edge.addRelation(rel_name, relation.data.shape, node1 is node2)
        edge.addWeight(np.ma.count(relation.data)/np.multiply(*relation.data.shape))
        self.relayout()
        return edge

    def wheelEvent(self, event):
        if event.orientation() != Qt.Vertical: return
        self.scaleView(2**(event.delta() / 240))
    def scaleView(self, factor):
        magnitude = self.transform().scale(factor, factor).mapRect(QRectF(0, 0, 1, 1)).width()
        if 0.4 < magnitude < 6:
            self.scale(factor, factor)

    def sizeHint(self):
        return QtCore.QSize(600, 500)

    def relayout(self):
        """Approximate Fruchterman-Reingold spring layout"""
        nodes = list(self.nodes.values())
        pos = np.array([(np.cos(i/len(nodes)*2*np.pi + np.pi/4),
                         np.sin(i/len(nodes)*2*np.pi + np.pi/4))
                        for i in range(1, 1 + len(nodes))])
        K = 1 / np.sqrt(pos.shape[0])
        GRAVITY, ITERATIONS = 10, 20
        TEMPERATURES = np.linspace(.3, .01, ITERATIONS)
        for temp in chain([.8, .5], TEMPERATURES):
            # Repulsive forces
            delta = pos[:, np.newaxis, :] - pos
            delta /= np.abs(delta).sum(2)[:, :, np.newaxis]**2  # NOTE: This warning was expected
            delta = np.nan_to_num(delta)  # Reverse the effect of zero-division
            disp = -delta.sum(0)*K*K
            # Attractive forces
            for edge in self.edges:
                n1, n2 = nodes.index(edge.source), nodes.index(edge.dest)
                delta = pos[n1] - pos[n2]
                magnitude = np.abs(delta).sum()
                disp[n1] -= delta*magnitude/K
                disp[n2] += delta*magnitude/K
            # Gravity; tend toward center
            magnitude = np.sqrt(np.sum(np.abs(pos)**2, 1))
            disp -= (pos.T*K*GRAVITY*magnitude).T
            # Limit max displacement and reposition
            magnitude = np.sqrt(np.sum(np.abs(disp)**2, 1))
            pos += (disp.T / magnitude).T * np.clip(np.abs(disp), 0, temp)

        for node, position in zip(nodes, 500*pos):
            node.setPos(*position)
        for edge in self.edges:
            edge.adjust()

        MARGIN, rect = 10, self.scene().itemsBoundingRect()
        rect = QRectF(rect.x() - MARGIN, rect.y() - MARGIN,
                      rect.width() + 2*MARGIN, rect.height() + 2*MARGIN)
        self.scene().setSceneRect(rect)
        self.scene().invalidate()

    selectionChanged = QtCore.pyqtSignal(list)

    def edgeClicked(self, edge): edge.selected = True
    def nodeClicked(self, node): node.selected = True
    def itemClicked(self, item):
        if   isinstance(item, Edge): self.edgeClicked(item)
        elif isinstance(item, Node): self.nodeClicked(item)
        selection = {i for i in chain(self.edges, self.nodes.values())
                     if i.selected} - {item}
        selection = [item] + list(selection)  # Put clicked item first
        self.selectionChanged.emit(selection)
    def clearSelection(self):
        were_selected = any(i for i in chain(self.edges, self.nodes.values())
                            if i.selected)
        for node in self.nodes.values():
            node.selected = False
        for edge in self.edges:
            edge.selected = False
        if were_selected:
            self.selectionChanged.emit([])
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        while item is not None:
            if isinstance(item, (Node, Edge)): break
            item = item.parentItem()
        assert item is None or isinstance(item, (Node, Edge))
        if item: self.itemClicked(item)
        else: self.clearSelection()


if __name__ == '__main__':

    import sys
    app = QtGui.QApplication(sys.argv)

    widget = GraphView()
    widget.show()

    import numpy as np
    from skfusion import fusion
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
    relations = [
        fusion.Relation(R12, t1, t2, name='like'),
        fusion.Relation(R13, t1, t3, name='rated'),
        fusion.Relation(R13, t1, t3, name='mated'),
        fusion.Relation(R23, t2, t3, name='play in'),
        fusion.Relation(R31, t3, t1),
        fusion.Relation(R24, t2, t4, name='prefer'),
        fusion.Relation(R34, t3, t4, name='belong to'),
        fusion.Relation(R22, t2, t2, name='married to')
    ]

    for rel in relations:
        widget.addRelation(rel)

    sys.exit(app.exec_())
