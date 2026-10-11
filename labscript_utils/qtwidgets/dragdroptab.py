#####################################################################
#                                                                   #
# dragdroptab.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import weakref
from collections import namedtuple, defaultdict

from qtutils.qt import QtCore, QtGui, QtWidgets


Tab = namedtuple('Tab', ['widget', 'text', 'data', 'text_color', 'tooltip',
                         'whats_this', 'button_left', 'button_right', 'icon'])


class _BaseDragDropTabBar(QtWidgets.QTabBar):
    # The QPoint of the mouse relative to the top left corner of the dragged
    # tab when the drag began. Shared by all instances.
    _dragged_tab_grab_point = None

    @property
    def dragged_tab_grab_point(self):
        return self._dragged_tab_grab_point

    @dragged_tab_grab_point.setter
    def dragged_tab_grab_point(self, value):
        # Set on the base class so that all subclasses share one value.
        _BaseDragDropTabBar._dragged_tab_grab_point = value

    def remove_dragged_tab(self, index):
        """Remove the tab at index and return its configuration as a Tab."""
        tab = Tab(widget=self.parent().widget(index),
                  text=self.tabText(index),
                  data=self.tabData(index),
                  text_color=self.tabTextColor(index),
                  tooltip=self.tabToolTip(index),
                  whats_this=self.tabWhatsThis(index),
                  button_left=self.tabButton(index, QtWidgets.QTabBar.ButtonPosition.LeftSide),
                  button_right=self.tabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide),
                  icon=self.tabIcon(index))

        self.parent().removeTab(index)
        if self.prev_active_tab is not None:
            self.setCurrentIndex(self.prev_active_tab)
            self.prev_active_tab = None

        return tab

    def add_dragged_tab(self, index, tab):
        self.prev_active_tab = self.currentIndex()

        self.parent().insertTab(index, tab.widget, tab.text)
        self.setCurrentIndex(index)

        if tab.data:
            self.setTabData(index, tab.data)
        self.setTabTextColor(index, tab.text_color)
        if tab.tooltip:
            self.setTabToolTip(index, tab.tooltip)
        if tab.whats_this:
            self.setTabWhatsThis(index, tab.whats_this)
        if tab.button_left:
            self.setTabButton(index, QtWidgets.QTabBar.ButtonPosition.LeftSide, tab.button_left)
        if tab.button_right:
            self.setTabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide, tab.button_right)
        if tab.icon:
            self.setTabIcon(index, tab.icon)


class _Limbo(_BaseDragDropTabBar):
    """A floating tab bar holding the dragged tab outside every tab bar."""

    def __init__(self):
        self.parent_tabwidget = QtWidgets.QTabWidget()
        super().__init__(self.parent_tabwidget)
        self.parent_tabwidget.setTabBar(self)
        self.previous_parent = None
        self.previous_index = None
        self.prev_active_tab = None
        self.setWindowFlags(QtCore.Qt.WindowType.ToolTip)
        self.setUsesScrollButtons(False)
        # A pixmap to render during animations, when we no longer own the tab.
        self.pixmap = None
        self.animation_in_progress = False

    def remove_dragged_tab(self, index):
        # Grab a pixmap of our contents in case the tab animates back to a tab
        # bar.
        self.pixmap = QtGui.QPixmap(self.size())
        self.render(self.pixmap, QtCore.QPoint(), QtGui.QRegion(self.rect()))
        result = super().remove_dragged_tab(index)
        self.hide()
        return result

    def animation_starting(self):
        self.animation_in_progress = True
        self.show()

    def animation_over(self):
        if self.animation_in_progress:
            self.pixmap = None
            self.animation_in_progress = False
            self.hide()

    def add_dragged_tab(self, index, tab):
        # Cancel any animation in progress.
        self.animation_over()
        result = super().add_dragged_tab(index, tab)
        self.show()
        return result

    def update_tab_index(self, index, pos):
        """Return index unchanged: limbo holds a single tab."""
        return index

    def tabLayoutChange(self):
        if self.count():
            self.resize(self.tabSizeHint(0))
        self.update()

    def insertion_index_at(self, pos):
        return 0

    def update(self):
        """Move the tab under the cursor's current position, then repaint."""
        if self.dragged_tab_grab_point is not None:
            self.move(QtGui.QCursor.pos() - self.dragged_tab_grab_point)
        super().update()

    def paintEvent(self, event):
        if self.animation_in_progress:
            painter = QtGui.QPainter(self)
            painter.drawPixmap(QtCore.QPoint(), self.pixmap)
            painter.end()
        else:
            super().paintEvent(event)


class TabAnimation(QtCore.QAbstractAnimation):
    """Animate a DragDropTabBar's tabs and the limbo tab returning to it."""

    # Time constant in milliseconds: an object moves at its distance from its
    # target divided by tau, in pixels per millisecond.
    tau = float(60)

    def __init__(self, parent):
        super().__init__(parent)
        # The left edges of where the tabs will be drawn. These approach the
        # left edges returned by parent.tabRect() over time.
        self.positions = []
        # The position of the floating limbo tab while it returns to the tab
        # bar that owns this animation.
        self.limbo_position = None
        self.limbo_target_tab = None
        self.limbo = None
        self.previous_time = 0

        # Set while asking widgets to update, to avoid recursion.
        self.callback_in_progress = False

    def duration(self):
        return -1

    def ensure_running(self):
        if self.callback_in_progress:
            return
        if self.state() == QtCore.QAbstractAnimation.State.Stopped:
            self.start()

    def target(self, i):
        """Return the left edge toward which tab i animates."""
        return self.parent().tabRect(i).left()

    def tabInserted(self, index):
        self.positions.insert(index, self.parent().tabRect(index).left())
        self.ensure_running()

    def tabRemoved(self, index):
        del self.positions[index]
        self.ensure_running()

    def on_tab_moved(self, source_index, dest_index):
        self.positions.insert(dest_index, self.positions.pop(source_index))
        self.ensure_running()

    def animate_limbo(self, limbo, index):
        """Fly the limbo tab into the tab at index, hidden until it arrives."""
        # The tab is already back in this bar; limbo only draws its pixmap.
        self.limbo = limbo
        self.limbo.animation_starting()
        self.limbo_position = self.parent().mapFromGlobal(limbo.pos())
        self.limbo_target_tab = index
        self.ensure_running()

    def updateCurrentTime(self, current_time):
        dt = current_time - self.previous_time
        self.previous_time = current_time

        finished = True

        # Move tabs toward their target:
        for i, pos in enumerate(self.positions):
            target_pos = self.target(i)
            dx = target_pos - pos
            # Animate while the tab is more than a pixel away from its target:
            if abs(dx) > 1:
                finished = False
                new_pos = pos + dx * dt / self.tau
                # Check for overshoot:
                if dx * (target_pos - new_pos) < 0:
                    new_pos = target_pos
                self.positions[i] = new_pos
            else:
                # Once it's close enough, snap it to the final value
                self.positions[i] = target_pos

        # Move the floating tab toward its target, if there is one.
        if self.limbo is not None:
            pos_x = self.limbo_position.x()
            pos_y = self.limbo_position.y()
            target_pos = self.parent().tabRect(self.limbo_target_tab).topLeft()
            target_pos_x = target_pos.x()
            target_pos_y = target_pos.y()
            dx = target_pos_x - pos_x
            dy = target_pos_y - pos_y

            # Animate while the floating tab is more than 15 pixels from its
            # target, by taxicab distance.
            if abs(dx) + abs(dy) > 15:
                finished = False

                new_pos_x = pos_x + dx * dt / self.tau
                new_pos_y = pos_y + dy * dt / self.tau

                # Check for overshoot:
                if dx * (target_pos_x - new_pos_x) < 0:
                    new_pos_x = target_pos_x
                if dy * (target_pos_y - new_pos_y) < 0:
                    new_pos_y = target_pos_y

                self.limbo_position = QtCore.QPoint(
                    int(round(new_pos_x)), int(round(new_pos_y))
                )
            else:
                self.limbo.animation_over()
                self.limbo = None
                self.limbo_position = None
                self.limbo_target_tab = None
        if finished:
            self.previous_time = 0
            self.stop()
        # With callback_in_progress set, updating the parent cannot recurse
        # through ensure_running.
        self.callback_in_progress = True
        if self.limbo is not None:
            self.limbo.move(self.parent().mapToGlobal(self.limbo_position))
            self.limbo.update()
        self.parent().update()
        self.callback_in_progress = False


class DragDropTabBar(_BaseDragDropTabBar):
    """The tab bar of a DragDropTabWidget.

    Tabs can be dragged between tab bars with the same group_id.
    """

    # The tab widgets in each group, which share a group_id.
    tab_widgets = defaultdict(weakref.WeakSet)

    # Whether a drag is in progress. Cleared before the variables below, so
    # that re-entrant event processing sees the drag is over.
    _drag_in_progress = False

    # The index and tab bar of the dragged tab, or None if no drag is in
    # progress. Shared by all instances.
    _dragged_tab_index = None
    _dragged_tab_parent = None

    # The _Limbo that holds the tab being dragged. Shared by all instances and
    # created with the first, since there may be no QApplication at import.
    limbo = None

    SCROLL_BUTTON_WIDTH = 15
    FLUSH_GAP = 5
    SCROLL_BUTTON_GAP = 2

    def __init__(self, parent, group_id):
        super().__init__(parent)

        self.group_id = group_id
        self.tab_widgets[group_id].add(self.parent())

        self.prev_active_tab = None
        if self.limbo is None:
            self.__class__.limbo = _Limbo()

        self.animation = TabAnimation(self)
        self.tabMoved.connect(self.animation.on_tab_moved)
        self.scroll_offset = 0
        self.left_scrollbutton = QtWidgets.QToolButton(self)
        self.right_scrollbutton = QtWidgets.QToolButton(self)
        self.left_scrollbutton.setArrowType(QtCore.Qt.ArrowType.LeftArrow)
        self.right_scrollbutton.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self.left_scrollbutton.setAutoRepeat(True)
        self.right_scrollbutton.setAutoRepeat(True)
        self.left_scrollbutton.clicked.connect(
            lambda: self.on_scroll_button_clicked(self.left_scrollbutton))
        self.right_scrollbutton.clicked.connect(
            lambda: self.on_scroll_button_clicked(self.right_scrollbutton))
        self.currentChanged.connect(self.ensure_visible)
        self.left_scrollbutton.hide()
        self.right_scrollbutton.hide()
        super().setUsesScrollButtons(False)
        self.setElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.uses_scrollbuttons = False

    def setUsesScrollButtons(self, uses_scrollbuttons):
        self.uses_scrollbuttons = uses_scrollbuttons
        if uses_scrollbuttons:
            # Scrolling replaces elision.
            self.setElideMode(QtCore.Qt.TextElideMode.ElideNone)
        else:
            self.setElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.update_scroll_button_state()
        self.update()

    def _leftflush(self):
        return self.FLUSH_GAP

    def _rightflush(self):
        return (self.width() - 2 * self.SCROLL_BUTTON_WIDTH -
                self.FLUSH_GAP - self.SCROLL_BUTTON_GAP)

    def ensure_visible(self, index, prefer_left=True):
        """Scroll tab index into view. Does nothing without scroll buttons.

        If the tab is too wide to fit, prefer_left chooses which edge to align.
        """
        if index == -1 or not self.uses_scrollbuttons:
            return
        left_protruding_width = -self.tabRect(index).left() + self._leftflush()
        right_protruding_width = self.tabRect(index).right() - self._rightflush()
        if left_protruding_width > 0 and not right_protruding_width > 0:
            self.scroll_offset -= left_protruding_width
        elif right_protruding_width > 0 and not left_protruding_width > 0:
            self.scroll_offset += right_protruding_width
        elif left_protruding_width > 0 and right_protruding_width > 0:
            if prefer_left:
                self.scroll_offset -= left_protruding_width
            else:
                self.scroll_offset += right_protruding_width

        self.update_scroll_button_state()
        self.update()

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(self.parent().width())
        return hint

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        if self.uses_scrollbuttons:
            hint.setWidth(0)
        return hint

    def update(self):
        super().update()
        self.animation.ensure_running()

    # The setters assign on the class so that all instances share the value.
    @property
    def drag_in_progress(self):
        return self._drag_in_progress

    @drag_in_progress.setter
    def drag_in_progress(self, value):
        self.__class__._drag_in_progress = value

    @property
    def dragged_tab_index(self):
        return self._dragged_tab_index

    @dragged_tab_index.setter
    def dragged_tab_index(self, value):
        self.__class__._dragged_tab_index = value

    @property
    def dragged_tab_parent(self):
        return self._dragged_tab_parent

    @dragged_tab_parent.setter
    def dragged_tab_parent(self, value):
        self.__class__._dragged_tab_parent = value

    def set_tab_parent(self, dest, index=None, pos=None):
        """Move the dragged tab to the tab bar dest, if it is not already there.

        If index is None, the insertion index is found from the mouse position
        pos.
        """
        if index is None:
            assert pos is not None
            index = dest.insertion_index_at(self.mapToGlobal(pos -
                                                             self.dragged_tab_grab_point))
        if self.dragged_tab_parent != dest:
            tab = self.dragged_tab_parent.remove_dragged_tab(self.dragged_tab_index)
            dest.add_dragged_tab(index, tab)
            if dest is self.limbo:
                self.limbo.previous_parent = self.dragged_tab_parent
                self.limbo.previous_index = self.dragged_tab_index
            self.dragged_tab_parent = dest
            self.dragged_tab_index = index
            dest.update()

    def insertion_index_at(self, pos):
        """Return the insertion index for a tab with its corner at global pos."""
        left = self.mapFromGlobal(pos).x()
        for other in range(self.count()):
            other_midpoint = self.tabRect(other).center().x()
            if other_midpoint > left:
                return other
        return self.count()

    def update_dragged_tab_animation_pos(self, pos):
        # Keep the dragged tab's animation position current, so that it
        # animates correctly once released.
        assert self.dragged_tab_parent is self
        pinned_rect = self.tabRect(self.dragged_tab_index)
        pinned_rect.translate(pos - self.dragged_tab_grab_point - pinned_rect.topLeft())
        left = pinned_rect.left()
        self.animation.positions[self.dragged_tab_index] = left

    def update_tab_index(self, index, pos):
        """Move the dragged tab at index past tabs it crosses; return its new index."""
        # Where the tab rect would be if pinned to the mouse at the point where
        # it was grabbed.
        pinned_rect = self.tabRect(index)
        pinned_rect.translate(pos-self.dragged_tab_grab_point - pinned_rect.topLeft())
        left = pinned_rect.left()
        self.animation.positions[index] = left
        right = pinned_rect.right()

        move_target = None

        for other in range(self.count()):
            other_midpoint = self.tabRect(other).center().x()
            if other < index and left < other_midpoint:
                move_target = other
                # Take the leftmost such tab, to move as far left as warranted.
                break
            elif other > index and right > other_midpoint:
                move_target = other
                # No break: the tab may move further right.
        if move_target is not None:
            self.moveTab(index, move_target)

            # The tab widget may not update its stacked widget on tabMoved
            # during a mouseMove event.
            if self.currentIndex() == move_target:
                stack = self.parent().findChild(QtWidgets.QStackedWidget, 'qt_tabwidget_stackedwidget')
                stack.setCurrentWidget(self.parent().widget(move_target))

            return move_target
        return index

    def widgetAt(self, pos):
        """Return the tab bar under pos, or the limbo if there is none.

        Only tab widgets in this bar's group are considered.
        """
        for tab_widget in self.tab_widgets[self.group_id]:
            count = tab_widget.tabBar().count()

            if tab_widget.accept_drops_bar_only:
                if count == 0:
                    widget = tab_widget
                    rect = widget.rect()
                    # The region at the top of the TabWidget equal to the height
                    # of a tab:
                    height = self.dragged_tab_parent.tabRect(self.dragged_tab_index).height()
                    rect.setHeight(height)
                else:
                    widget = tab_widget.tabBar()
                    rect = widget.rect()
                    # Include the whole horizontal part of the tabBar:
                    rect.setLeft(widget.parent().rect().left())
                    rect.setRight(widget.parent().rect().right())
                    # While leaving, add a buffer so the tab stays until the mouse
                    # is some distance away.
                    if self.drag_in_progress and self.dragged_tab_parent is widget:
                        rect.setLeft(rect.left() - 10)
                        rect.setRight(rect.right() + 10)
                    # Vertically the buffer is always there, which makes the tab
                    # bars a slightly bigger target for coming and going.
                    rect.setTop(rect.top() - 10)
                    rect.setBottom(rect.bottom() + 10)

            else:
                widget = tab_widget
                rect = widget.rect()
                # While leaving, add a buffer so the tab stays until the mouse
                # is some distance away.
                if self.drag_in_progress and self.dragged_tab_parent is tab_widget.tabBar():
                    rect.setLeft(rect.left() - 10)
                    rect.setRight(rect.right() + 10)
                    rect.setTop(rect.top() - 10)
                    rect.setBottom(rect.bottom() + 10)

            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(pos))
            if rect.contains(other_local_pos):
                return tab_widget.tabBar()
        return self.limbo

    def tabRect(self, index):
        rect = super().tabRect(index)
        rect.translate(-self.scroll_offset, 0)
        return rect

    def tabAt(self, pos):
        for i in range(self.count()):
            if self.tabRect(i).contains(pos):
                return i
        return -1

    def mousePressEvent(self, event):
        """Start dragging the tab under the mouse."""
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        event.accept()
        index = self.tabAt(event.pos())
        if index == -1:
            return
        self.setCurrentIndex(index)
        self.ensure_visible(index)
        self.drag_in_progress = True
        # Receive all mouse events until the mouse is released.
        self.grabMouse()
        self.dragged_tab_index = index
        self.dragged_tab_parent = self
        self.dragged_tab_grab_point = (event.pos()
                                       - self.tabRect(self.dragged_tab_index).topLeft())

    def mouseMoveEvent(self, event):
        """Move the dragged tab to the tab bar under the mouse, or to limbo."""
        super().mouseMoveEvent(event)
        if not self.drag_in_progress:
            self.update()
            return
        event.accept()
        if self.group_id is not None:
            widget = self.widgetAt(event.pos())
            self.set_tab_parent(widget, pos=event.pos())
            other_local_pos = widget.mapFromGlobal(self.mapToGlobal(event.pos()))
            self.dragged_tab_index = widget.update_tab_index(self.dragged_tab_index,
                                                             other_local_pos)
            if self.dragged_tab_parent is not self.limbo:
                self.dragged_tab_parent.update_dragged_tab_animation_pos(other_local_pos)
            widget.update()

    def mouseReleaseEvent(self, event):
        """Drop the dragged tab in the tab bar under the mouse.

        If the tab is in limbo and the mouse is over no tab bar, the tab
        returns to the tab bar it last left.
        """
        super().mouseReleaseEvent(event)
        if not self.drag_in_progress or event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        event.accept()
        self.drag_in_progress = False
        widget = self.widgetAt(event.pos())
        self.releaseMouse()
        # If the tab and the mouse are both in limbo, put the tab back at its
        # last known place.
        if widget is self.limbo and self.dragged_tab_parent is self.limbo:
            index = self.limbo.previous_index
            self.set_tab_parent(self.limbo.previous_parent, index)
            self.limbo.previous_parent.animation.animate_limbo(self.limbo, index)
        # If the mouse is over a tab bar that the tab is not in, put it there.
        # Otherwise leave it where it is, rather than moving it into limbo.
        elif widget is not self.limbo and widget is not self.dragged_tab_parent:
            self.set_tab_parent(widget, pos=event.pos())
        else:
            # The tab is already in this widget; store its position to animate.
            other_local_pos = self.dragged_tab_parent.mapFromGlobal(
                                  self.mapToGlobal(event.pos()))
            self.dragged_tab_parent.update_dragged_tab_animation_pos(other_local_pos)

        self.dragged_tab_parent.update()

        self.dragged_tab_index = None
        self.dragged_tab_parent = None
        self.dragged_tab_grab_point = None

    def is_dragged_tab(self, index):
        """Return whether the tab at index is being dragged."""
        return (self.drag_in_progress
                and self.dragged_tab_parent is self
                and self.dragged_tab_index == index)

    def tabInserted(self, index):
        super().tabInserted(index)
        self.animation.tabInserted(index)

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self.animation.tabRemoved(index)

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self.animation.ensure_running()
        self.update_scroll_button_state()
        self.ensure_visible(self.currentIndex())

    def update_scroll_button_state(self):
        if not self.uses_scrollbuttons:
            self.left_scrollbutton.hide()
            self.right_scrollbutton.hide()
            return
        all_tabs_right_edge = self.tabRect(self.count() - 1).right()
        all_tabs_left_edge = self.tabRect(0).left()
        total_width_of_all_tabs = all_tabs_right_edge - all_tabs_left_edge
        min_scroll_offset = 0
        max_scroll_offset = max(0, total_width_of_all_tabs -
                                   self.parent().width() +
                                   2 * self.SCROLL_BUTTON_WIDTH +
                                   2 * self.SCROLL_BUTTON_GAP)
        if self.scroll_offset <= min_scroll_offset:
            self.scroll_offset = min_scroll_offset
            self.left_scrollbutton.setEnabled(False)
        else:
            self.left_scrollbutton.setEnabled(True)
        if self.scroll_offset >= max_scroll_offset:
            self.scroll_offset = max_scroll_offset
            self.right_scrollbutton.setEnabled(False)
        else:
            self.right_scrollbutton.setEnabled(True)
        self.left_scrollbutton.resize(self.SCROLL_BUTTON_WIDTH,
                                      self.height() - 6)
        self.right_scrollbutton.resize(self.SCROLL_BUTTON_WIDTH,
                                       self.height() - 6)
        self.left_scrollbutton.move(self.parent().width() -
                                    2*self.SCROLL_BUTTON_WIDTH, 3)
        self.right_scrollbutton.move(self.parent().width() -
                                     self.SCROLL_BUTTON_WIDTH, 3)

        if self.left_scrollbutton.isEnabled() or self.right_scrollbutton.isEnabled():
            self.left_scrollbutton.show()
            self.right_scrollbutton.show()
        else:
            self.left_scrollbutton.hide()
            self.right_scrollbutton.hide()

    def on_scroll_button_clicked(self, button):
        if button is self.left_scrollbutton:
            for i in range(self.count() - 1, -1, -1):
                if self.tabRect(i).left() < self._leftflush():
                    self.ensure_visible(i, prefer_left=True)
                    break
        elif button is self.right_scrollbutton:
            for i in range(self.count()):
                if self.tabRect(i).right() > self._rightflush():
                    self.ensure_visible(i, prefer_left=False)
                    break
        self.update_scroll_button_state()
        self.update()

    def paint_tab(self, index, painter, option):
        # The floating tab's target is not drawn while the tab flies in.
        if index == self.animation.limbo_target_tab:
            return
        painter.save()
        if self.is_dragged_tab(index):
            # The dragged tab follows the mouse.
            xpos = self.mapFromGlobal(QtGui.QCursor.pos()).x() - self.dragged_tab_grab_point.x()
        else:
            # Other tabs are at their animated position.
            xpos = self.animation.positions[index]
        tabrect = self.tabRect(index)
        painter.translate(xpos - tabrect.left() - self.scroll_offset, 0)
        self.initStyleOption(option, index)
        painter.drawControl(QtWidgets.QStyle.ControlElement.CE_TabBarTab, option)
        painter.restore()

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        option = QtWidgets.QStyleOptionTab()
        # Draw in reverse order so that tabs to the left overlap those to the
        # right.
        for index in range(self.count() - 1, -1, -1):
            if self.currentIndex() == index:
                # The current tab is drawn last, so it is on top.
                continue
            self.paint_tab(index, painter, option)
        if self.currentIndex() != -1:
            self.paint_tab(self.currentIndex(), painter, option)
        # Erase the region where the scroll buttons go.
        if self.left_scrollbutton.isEnabled() or self.right_scrollbutton.isEnabled():
            rect = self.rect()
            rect.moveLeft(self.width() - 2 * self.SCROLL_BUTTON_WIDTH -
                          self.SCROLL_BUTTON_GAP)
            rect.moveBottom(rect.bottom() - 2)
            painter.eraseRect(rect)
        painter.end()


class DragDropTabWidget(QtWidgets.QTabWidget):
    """A tab widget whose tabs can be dragged and reordered with animation.

    Parameters
    ----------
    group_id : hashable, optional
        Tabs move between widgets sharing a group_id. None disables dragging.
    accept_drops_bar_only : bool, optional
        If True, tabs drop only on the tab bar, not anywhere over the widget.
    """

    def __init__(self, group_id=None, accept_drops_bar_only=False):
        super().__init__()
        self.setTabBar(DragDropTabBar(self, group_id))
        self.tabBar().setExpanding(False)
        # Alias of tabBar(), for callers that use tab_bar.
        self.tab_bar = self.tabBar()
        self.accept_drops_bar_only = accept_drops_bar_only
        self.setUsesScrollButtons(True)

    def setUsesScrollButtons(self, uses_scrollbuttons):
        self.tabBar().setUsesScrollButtons(uses_scrollbuttons)

    def setElideMode(self, mode):
        """Ignored: elision follows setUsesScrollButtons (right if off, none if on)."""
