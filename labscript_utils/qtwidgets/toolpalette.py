#####################################################################
#                                                                   #
# toolpalette.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from qtutils.qt import QtCore, QtGui, QtWidgets


EXPAND_ICON = ':/qtutils/fugue/toggle-small-expand'
CONTRACT_ICON = ':/qtutils/fugue/toggle-small'

_ENABLE_LAYOUT_EVENT_TYPE = QtCore.QEvent.Type.User


class ToolPaletteGroup(QtWidgets.QVBoxLayout):
    """A vertical layout of named ToolPalettes, each under a header button that hides or shows it."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widget_groups = {}

    def append_new_palette(self, name, *args, **kwargs):
        """Create a ToolPalette called name, add it to the group and return it.

        Other arguments go to ToolPalette. Raises RuntimeError if the group
        already has a palette called name.
        """
        if name in self._widget_groups:
            raise RuntimeError(f'The tool palette group already has a palette named {name}')

        tool_palette = ToolPalette(self, name, *args, **kwargs)
        push_button = QtWidgets.QPushButton(name)
        push_button.setIcon(QtGui.QIcon(CONTRACT_ICON))
        push_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        push_button.setToolTip('Click to hide')

        frame = QtWidgets.QFrame()
        frame.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel)
        frame_layout = QtWidgets.QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(push_button)
        header_layout.addStretch(1)
        header_widget.setLayout(header_layout)
        header_layout.setContentsMargins(3, 3, 3, 3)

        def create_callback(name):
            return lambda: self._on_button_clicked(name)

        push_button.clicked.connect(create_callback(name))
        self._widget_groups[name] = (tool_palette, push_button)

        frame_layout.addWidget(header_widget)
        frame_layout.addWidget(tool_palette)

        self.addWidget(frame)
        return tool_palette

    def _on_button_clicked(self, name):
        if self._widget_groups[name][0].isHidden():
            self.show_palette(name)
        else:
            self.hide_palette(name)

    def show_palette(self, name):
        """Show the palette called name; raises RuntimeError if there is none."""
        if name not in self._widget_groups:
            raise RuntimeError(f'The tool palette does not have a palette named {name}')
        palette, push_button = self._widget_groups[name]
        palette.show()
        push_button.setIcon(QtGui.QIcon(CONTRACT_ICON))
        push_button.setToolTip('Click to hide')

    def hide_palette(self, name):
        """Hide the palette called name; raises RuntimeError if there is none."""
        if name not in self._widget_groups:
            raise RuntimeError(f'The tool palette does not have a palette named {name}')

        palette, push_button = self._widget_groups[name]
        palette.hide()
        push_button.setIcon(QtGui.QIcon(EXPAND_ICON))
        push_button.setToolTip('Click to show')

    def has_palette(self, name):
        """Return whether the group has a palette called name."""
        if name in self._widget_groups:
            return True
        return False

    def get_palette(self, name):
        """Return the palette called name; raises RuntimeError if there is none."""
        if name not in self._widget_groups:
            raise RuntimeError(f'The tool palette group does not contain a palette named {name}')

        return self._widget_groups[name][0]


class ToolPalette(QtWidgets.QScrollArea):
    """A scroll area that lays its widgets out in a grid with as many columns as fit its width.

    Made by ToolPaletteGroup.append_new_palette; parent and name are not used.
    """

    def __init__(self, parent, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(3, 0, 3, 3)
        self._layout.setHorizontalSpacing(3)
        self._layout.setVerticalSpacing(3)
        self._widget_list = []

        # The layout's columnCount() and rowCount() give the allocated rather
        # than the visible number, so keep our own.
        self._column_count = 0
        self._row_count = 0

        # Whether resizeEvent() calls self._layout_widgets().
        self._layout_widgets_during_resizeEvent = True

    def addWidget(self, widget, force_relayout=True):
        """Append widget to the end of the palette.

        If force_relayout is False, the grid is rebuilt only if the number of
        columns changes.
        """
        self._widget_list.append(widget)
        self._layout_widgets(force_relayout)

    def insertWidget(self, index, widget, force_relayout=True):
        """Insert widget at position index; arguments as for addWidget."""
        self._widget_list.insert(index, widget)
        self._layout_widgets(force_relayout)

    def _find_max_item_width(self):
        # The widest of the widgets' minimum widths.
        w_size_hints = [w.minimumSizeHint().width() for w in self._widget_list]
        if len(w_size_hints) < 1:
            return 0
        max_width = max(w_size_hints)
        return max_width

    def _layout_widgets(self, force_relayout=False):
        h_size_hints = [w.sizeHint().height() for w in self._widget_list]
        max_width = self._find_max_item_width()

        layout_width = self.size().width()
        layout_spacing = self._layout.horizontalSpacing()

        # TODO: Why layout_spacing*3? The width is that of the scroll area, so it
        # presumably allows for borders around the grid layout, whose size is unknown.
        num_widgets_per_row = (layout_width - layout_spacing*3)//(max_width + layout_spacing)

        if num_widgets_per_row < 1:
            num_widgets_per_row = 1
        elif num_widgets_per_row > len(self._widget_list):
            num_widgets_per_row = len(self._widget_list)

        if num_widgets_per_row != self._column_count or force_relayout:
            for widget in self._widget_list:
                self._layout.removeWidget(widget)

            row = 0
            column = 0
            for widget in self._widget_list:
                self._layout.addWidget(widget, row, column)
                column += 1
                if column >= num_widgets_per_row:
                    column = 0
                    row += 1

            # A partly filled last row still counts.
            if column != 0:
                row += 1
            self._column_count = num_widgets_per_row
            self._row_count = row

            total_height = max(h_size_hints) * self._row_count
            total_height += self._layout.verticalSpacing() * (self._row_count - 1)
            total_height += self._layout.contentsMargins().top()
            total_height += self._layout.contentsMargins().bottom()
            self.setMinimumSize(QtCore.QSize(self.minimumSize().width(), total_height))
            for i in range(self._layout.rowCount()):
                if i < self._row_count:
                    self._layout.setRowMinimumHeight(i, max(h_size_hints))
                else:
                    self._layout.setRowMinimumHeight(i, 0)

    def minimumSize(self):
        widget_size = QtWidgets.QWidget.minimumSize(self)

        # The width must fit the widest child's minimum width.
        widths = [w.minimumSizeHint().width() for w in self._widget_list]
        if len(widths) > 0:
            max_width = max(widths)
            if max_width > widget_size.width():
                widget_size = QtCore.QSize(max_width, widget_size.height())

        return widget_size

    def sizeHint(self):
        width = super().sizeHint().width()
        height = self.minimumSize().height()
        return QtCore.QSize(width, height)

    def minimumSizeHint(self):
        width = super().minimumSizeHint().width()
        height = self.minimumSize().height()
        return QtCore.QSize(width, height)

    def event(self, event):
        # The custom event re-enables self._layout_widgets() in resizeEvent().
        if (event.type() == _ENABLE_LAYOUT_EVENT_TYPE):
            self._layout_widgets_during_resizeEvent = True
            # Return True so that this event isn't sent along to other event
            # handlers as well.
            return True

        return super().event(event)

    def resizeEvent(self, event):
        # _layout_widgets() can change the column count, which adds or removes a
        # scrollbar and triggers another resizeEvent, endlessly (issue 27). Skip it
        # until an event posted at the queue's end re-enables it.
        try:
            # QWidget's handler is called directly, skipping QScrollArea's.
            QtWidgets.QWidget.resizeEvent(self, event)
            size = event.size()
            if size.width() == self.size().width() and size.height() == self.size().height():
                if self._layout_widgets_during_resizeEvent:
                    self._layout_widgets_during_resizeEvent = False
                    self._layout_widgets()
        finally:
            # Posted last, so it is handled after the resize events that
            # _layout_widgets() generates.
            QtCore.QCoreApplication.instance().postEvent(self, QtCore.QEvent(_ENABLE_LAYOUT_EVENT_TYPE))
