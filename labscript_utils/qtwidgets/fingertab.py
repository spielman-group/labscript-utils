#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/fingertab.py                            #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
"""Left-side tabs with horizontal labels and optional tab buttons."""

from qtutils.qt import QtCore, QtGui, QtWidgets
from qtutils.qt.QtCore import Qt
from qtutils.icons import Icon


_RIGHT_SIDE = QtWidgets.QTabBar.ButtonPosition.RightSide


class FingerTabBarWidget(QtWidgets.QTabBar):

    """A TabBar with the tabs on the left and the text horizontal. Credit to
    @LegoStormtroopr, https://gist.github.com/LegoStormtroopr/5075267.
    FingerTabWidget installs one as its tab bar."""

    def __init__(self, parent=None, minwidth=180, minheight=30, **kwargs):
        QtWidgets.QTabBar.__init__(self, parent, **kwargs)
        self.minwidth = minwidth
        self.minheight = minheight
        self._movable = None
        self.tab_movable = {}
        self.paint_clip = None

    def setMovable(self, movable, index=None):
        """Set tabs movable on an individual basis, or set for all tabs if no
        index specified"""
        if index is None:
            self._movable = movable
            self.tab_movable = {}
            QtWidgets.QTabBar.setMovable(self, movable)
        else:
            self.tab_movable[int(index)] = bool(movable)

    def isMovable(self, index=None):
        if index is None:
            if self._movable is None:
                self._movable = QtWidgets.QTabBar.isMovable(self)
            return self._movable
        return self.tab_movable.get(index, self._movable)

    def setTabStatusIcon(self, index, icon):
        """Set an icon to draw at the right of the tab, to the left of its button"""
        self.setTabData(index, icon)
        # Lay out the tabs again for the new tab size hint:
        self.setIconSize(self.iconSize())

    def tabStatusIcon(self, index):
        icon = self.tabData(index)
        if icon is None:
            return QtGui.QIcon()
        return icon

    def indexAtPos(self, point):
        for index in range(self.count()):
            if self.tabRect(index).contains(point):
                return index

    def mousePressEvent(self, event):
        index = self.indexAtPos(event.position().toPoint())
        if not self.tab_movable.get(index, self.isMovable()):
            # Disable dragging until they release the mouse:
            QtWidgets.QTabBar.setMovable(self, False)
        return QtWidgets.QTabBar.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.isMovable():
            # Restore this in case it was temporarily disabled by mousePressEvent
            QtWidgets.QTabBar.setMovable(self, True)
        return QtWidgets.QTabBar.mouseReleaseEvent(self, event)

    def tabLayoutChange(self):
        total_height = 0
        for index in range(self.count()):
            tabRect = self.tabRect(index)
            total_height += tabRect.height()
        if total_height > self.parent().height():
            # Don't paint over the top of the scroll buttons:
            scroll_buttons_area_height = 2*self.style().pixelMetric(
                QtWidgets.QStyle.PixelMetric.PM_TabBarScrollButtonWidth)
            self.paint_clip = (
                self.width(), self.parent().height() - scroll_buttons_area_height
            )
        else:
            self.paint_clip = None

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        if self.paint_clip is not None:
            painter.setClipRect(0, 0, *self.paint_clip)

        option = QtWidgets.QStyleOptionTab()
        for index in range(self.count()):
            tabRect = self.tabRect(index)
            self.initStyleOption(option, index)
            painter.drawControl(
                QtWidgets.QStyle.ControlElement.CE_TabBarTabShape, option
            )
            text_left = tabRect.left() + 10
            text_right = tabRect.right() - 10
            button = self.tabButton(index, _RIGHT_SIDE)
            if button is not None:
                text_right = button.x() - 5
            if not self.tabIcon(index).isNull():
                icon_rect = QtCore.QRect(QtCore.QPoint(0, 0), self.iconSize())
                icon_rect.moveCenter(tabRect.center())
                icon_rect.moveLeft(text_left)
                text_left = icon_rect.right() + 6
                self.tabIcon(index).paint(painter, icon_rect)
            if not self.tabStatusIcon(index).isNull():
                icon_rect = QtCore.QRect(QtCore.QPoint(0, 0), self.iconSize())
                icon_rect.moveCenter(tabRect.center())
                icon_rect.moveRight(text_right)
                text_right = icon_rect.left() - 5
                self.tabStatusIcon(index).paint(painter, icon_rect)
            textRect = QtCore.QRect(tabRect)
            textRect.setLeft(text_left)
            textRect.setRight(text_right)
            text = painter.fontMetrics().elidedText(
                self.tabText(index), Qt.TextElideMode.ElideRight, textRect.width()
            )
            painter.drawText(textRect, Qt.AlignmentFlag.AlignVCenter, text)
        if self.paint_clip is not None:
            x_clip, y_clip = self.paint_clip
            painter.setClipping(False)
            palette = self.palette()
            mid_color = palette.color(QtGui.QPalette.ColorRole.Mid)
            painter.setPen(mid_color)
            painter.drawLine(0, y_clip, x_clip, y_clip)
        painter.end()

    def tabSizeHint(self, index):
        fontmetrics = QtGui.QFontMetrics(self.font())
        text_width = fontmetrics.horizontalAdvance(self.tabText(index))
        text_height = fontmetrics.height()
        height = text_height + 15
        height = max(self.minheight, height)
        width = text_width + 15
        if not self.tabIcon(index).isNull():
            width += self.iconSize().width() + 5
        if not self.tabStatusIcon(index).isNull():
            width += self.iconSize().width() + 5

        button = self.tabButton(index, _RIGHT_SIDE)
        if button is not None:
            height = max(height, button.height() + 7)
            # Same amount of space around the button horizontally as it has vertically:
            width += button.width() + height - button.height()
        width = max(self.minwidth, width)
        return QtCore.QSize(width, height)

    def setTabButton(self, index, geometry, button):
        if button is not None and not isinstance(button, TabToolButton):
            raise TypeError(
                "Not a TabToolButton, won't paint correctly. Use a TabToolButton"
            )
        result = QtWidgets.QTabBar.setTabButton(self, index, geometry, button)
        if button is not None:
            button.move(*button.get_correct_position())
        return result


class TabToolButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        QtWidgets.QToolButton.__init__(self, *args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoRaise(True)

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        paint_clip = self.parent().paint_clip
        if paint_clip is not None:
            point = QtCore.QPoint(*paint_clip)
            global_point = self.parent().mapToGlobal(point)
            local_point = self.mapFromGlobal(global_point)
            painter.setClipRect(0, 0, local_point.x(), local_point.y())
        option = QtWidgets.QStyleOptionToolButton()
        self.initStyleOption(option)
        painter.drawComplexControl(
            QtWidgets.QStyle.ComplexControl.CC_ToolButton, option
        )

    def get_correct_position(self):
        parent = self.parent()
        for index in range(parent.count()):
            if parent.tabButton(index, _RIGHT_SIDE) is self:
                break
        else:
            raise LookupError('Tab not found')
        tabRect = parent.tabRect(index)
        tab_x, tab_y = tabRect.x(), tabRect.y()
        tab_width, tab_height = tabRect.width(), tabRect.height()
        size = self.sizeHint()
        width = size.width()
        height = size.height()
        padding = int((tab_height - height) / 2)
        correct_x = tab_x + tab_width - width - padding
        correct_y = tab_y + padding
        return correct_x, correct_y

    def moveEvent(self, event):
        try:
            correct_x, correct_y = self.get_correct_position()
        except LookupError:
            return # Things aren't initialised yet
        if self.x() != correct_x or self.y() != correct_y:
            # Keep the button where the tab bar puts it:
            self.move(correct_x, correct_y)
        return QtWidgets.QToolButton.moveEvent(self, event)


# Shamelessly stolen from this thread:
#   http://www.riverbankcomputing.com/pipermail/pyqt/2005-December/011724.html
class FingerTabWidget(QtWidgets.QTabWidget):
    """A QTabWidget equivalent which uses our FingerTabBarWidget.

    `addTab` takes `closable=True` for a close button on the tab, which emits
    `tabCloseRequested`.
    """

    def __init__(self, parent, *args):
        QtWidgets.QTabWidget.__init__(self, parent, *args)
        self.setTabBar(FingerTabBarWidget(self))

    def addTab(self, *args, **kwargs):
        closeable = kwargs.pop('closable', False)
        index = QtWidgets.QTabWidget.addTab(self, *args, **kwargs)
        self.setTabClosable(index, closeable)
        return index

    def setTabClosable(self, index, closable):
        right_button = self.tabBar().tabButton(index, _RIGHT_SIDE)
        if closable:
            if not right_button:
                close_button = TabToolButton(self.parent())
                close_button.setIcon(Icon(':/qtutils/fugue/cross'))
                self.tabBar().setTabButton(
                    index, _RIGHT_SIDE, close_button
                )
                close_button.clicked.connect(
                    lambda: self._on_close_button_clicked(close_button)
                )
        else:
            if right_button:
                self.tabBar().setTabButton(index, _RIGHT_SIDE, None)

    def _on_close_button_clicked(self, button):
        for index in range(self.tabBar().count()):
            if self.tabBar().tabButton(index, _RIGHT_SIDE) is button:
                self.tabCloseRequested.emit(index)
                break
