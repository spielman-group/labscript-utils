from qtutils.qt import QtCore, QtGui, QtWidgets


class HorizontalHeaderViewWithWidgets(QtWidgets.QHeaderView):
    """A QHeaderView that can hold a widget in any of its sections.

    Put a widget in a section with ``setWidget(logical_index, widget)`` and
    remove it with ``setWidget(logical_index, None)``. The section's text is
    indented to make room for the widget. Decorations, checkboxes and anything
    other than text in a section that holds a widget are unsupported, and may
    draw garbled.

    Parameters
    ----------
    model : QStandardItemModel
        The model whose horizontal header this is. It is also kept as
        ``self.model``.
    parent : QWidget, optional
    """

    # Indents the text of sections that hold widgets.
    thinspace = u'\u2009'

    stylesheet = """
                 QHeaderView::section {
                 /* Will be set dynamically: */
                 padding-top: %dpx;
                 padding-bottom: %dpx;
                 /* Required, otherwise set to zero upon setting any stylesheet at all: */
                 padding-left: 4px;
                 /* Required for some reason, otherwise other settings ignored: */
                 color: palette(text);
                 }

                 /* Any other style goes here: */
                 %s
                 """

    def __init__(self, model, parent=None):
        self.widgets = {}
        self.indents = {}
        self.model = model
        super().__init__(QtCore.Qt.Orientation.Horizontal, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.sectionMoved.connect(self.update_widget_positions)
        self.sectionResized.connect(self.update_widget_positions)
        self.geometriesChanged.connect(self.update_widget_positions)
        self.sectionCountChanged.connect(self.update_widget_positions)
        self.model.columnsInserted.connect(self.on_columns_inserted)
        self.model.columnsRemoved.connect(self.on_columns_removed)
        self.setSectionsMovable(True)
        self.vertical_padding = 0
        self.position_update_required = False
        self.custom_style = ''
        self.update_indents()

    def setStyleSheet(self, custom_style):
        """Set style rules to append to the stylesheet this class generates for
        the sections."""
        self.custom_style = custom_style
        self.update_indents()

    def showSection(self, *args, **kwargs):
        result = super().showSection(*args, **kwargs)
        self.update_indents()
        self.update_widget_positions()
        return result

    def hideSection(self, *args, **kwargs):
        result = super().hideSection(*args, **kwargs)
        self.update_indents()
        self.update_widget_positions()
        return result

    def setSectionHidden(self, *args, **kwargs):
        result = super().setSectionHidden(*args, **kwargs)
        self.update_indents()
        self.update_widget_positions()
        return result

    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.Type.Paint:
            self.update_widget_positions()
        return super().viewportEvent(event)

    def setWidget(self, logical_index, widget=None):
        """Put a widget in a section, or with widget=None remove its widget.

        Parameters
        ----------
        logical_index : int
        widget : QWidget, optional
            The widget to show in the section; the header becomes its parent.
            None removes the section's current widget.
        """
        header_item = self.model.horizontalHeaderItem(logical_index)
        if header_item is None:
            self.model.setHorizontalHeaderItem(logical_index, QtGui.QStandardItem())
        if widget is None:
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                widget.setParent(None)
                del self.widgets[logical_index]
                widget.removeEventFilter(self)
                del self.indents[widget]
                label_text = self.model.headerData(
                    logical_index, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole)
                if label_text is None:
                    return
                else:
                    raw_label_text = label_text.replace(self.thinspace, '')
                    self.model.setHeaderData(
                        logical_index, QtCore.Qt.Orientation.Horizontal, raw_label_text,
                        QtCore.Qt.ItemDataRole.DisplayRole)
        else:
            self.widgets[logical_index] = widget
            widget.setParent(self)
            widget.installEventFilter(self)
            if not self.isSectionHidden(logical_index) and not widget.isVisible():
                widget.show()
        self.update_indents()
        self.update_widget_positions()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_indents()
        self.update_widget_positions()

    def update_indents(self):
        max_widget_height = 0
        for visual_index in range(self.count()):
            logical_index = self.logicalIndex(visual_index)
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                if not self.isSectionHidden(logical_index):
                    max_widget_height = max(max_widget_height, widget.size().height())
                desired_indent = widget.size().width()
                item = self.model.horizontalHeaderItem(logical_index)
                font = item.font()
                fontmetrics = QtGui.QFontMetrics(font, self)
                indent = ''
                while fontmetrics.horizontalAdvance(indent) < desired_indent:
                    indent += self.thinspace
                self.indents[widget] = indent
        font = self.font()
        fontmetrics = QtGui.QFontMetrics(font, self)
        height = fontmetrics.height()
        required_padding = (max_widget_height + 2 - height) // 2
        required_padding = max(required_padding, 3)
        super().setStyleSheet(self.stylesheet % (required_padding, required_padding, self.custom_style))

    def sectionSizeFromContents(self, logical_index):
        base_size = super().sectionSizeFromContents(logical_index)
        width, height = base_size.width(), base_size.height()
        if logical_index in self.widgets:
            widget_size = self.widgets[logical_index].size()
            widget_width, widget_height = widget_size.width(), widget_size.height()
            height = max(height, widget_height + 2)
            width = max(width, widget_width + 7)
        return QtCore.QSize(width, height)

    def update_widget_positions(self):
        # Do later and compress events, so that do_update_widget_positions is not
        # called several times over.
        if not self.position_update_required:
            timer = QtCore.QTimer.singleShot(0, self.do_update_widget_positions)
            self.position_update_required = True

    def do_update_widget_positions(self):
        self.position_update_required = False
        if not self.count():
            return
        max_height = max(self.sectionSizeFromContents(i).height()
                         for i in range(self.count())
                         if not self.isSectionHidden(i))
        for visual_index in range(self.count()):
            logical_index = self.logicalIndex(visual_index)
            if logical_index in self.widgets:
                widget = self.widgets[logical_index]
                if not self.isSectionHidden(logical_index) and not widget.isVisible():
                    widget.show()
                elif self.isSectionHidden(logical_index) and widget.isVisible():
                    widget.hide()
                section_position = self.sectionViewportPosition(logical_index)
                widget_size = widget.size()
                widget_width, widget_height = widget_size.width(), widget_size.height()
                widget_target_x = section_position + 3
                widget_target_y = (max_height - widget_height) // 2 - 1
                widget_current_pos = widget.pos()
                widget_current_x, widget_current_y = widget_current_pos.x(), widget_current_pos.y()
                if (widget_target_x, widget_target_y) != (widget_current_x, widget_current_y):
                    widget.move(widget_target_x, widget_target_y)
                try:
                    indent = self.indents[widget]
                except KeyError:
                    # A section that did not exist when update_indents last ran
                    # has no indent yet.
                    return
                label_text = self.model.headerData(
                    logical_index, QtCore.Qt.Orientation.Horizontal, QtCore.Qt.ItemDataRole.DisplayRole)
                if label_text is None:
                    label_text = ''
                raw_label_text = label_text.replace(self.thinspace, '')
                if label_text != indent + raw_label_text:
                    self.model.setHeaderData(
                        logical_index, QtCore.Qt.Orientation.Horizontal, indent + raw_label_text,
                        QtCore.Qt.ItemDataRole.DisplayRole)

    def eventFilter(self, target, event):
        """Unset the resize cursor when the mouse enters a child widget."""
        if event.type() == QtCore.QEvent.Type.Enter:
            self.unsetCursor()
        return False

    def on_columns_inserted(self, parent, logical_first, logical_last):
        n_inserted = logical_last - logical_first + 1
        widgets_with_offset = {}
        for logical_index, widget in self.widgets.items():
            if logical_index < logical_first:
                widgets_with_offset[logical_index] = widget
            else:
                widgets_with_offset[logical_index + n_inserted] = widget
        self.widgets = widgets_with_offset
        self.update_widget_positions()

    def on_columns_removed(self, parent, logical_first, logical_last):
        n_removed = logical_last - logical_first + 1
        widgets_with_offset = {}
        for logical_index, widget in self.widgets.items():
            if logical_index < logical_first:
                widgets_with_offset[logical_index] = widget
            elif logical_index <= logical_last:
                # Not setWidget(logical_index, None): the column is already gone,
                # so that index now names another column, or none.
                widget.setParent(None)
                widget.removeEventFilter(self)
                del self.indents[widget]
            else:
                widgets_with_offset[logical_index - n_removed] = widget
        self.widgets = widgets_with_offset
        self.update_indents()
        self.update_widget_positions()
