from qtutils.qt import QtCore, QtWidgets


ELLIPSIS = u'\u2026'


class ElideScrollArea(QtWidgets.QScrollArea):
    """A scroll area with no scroll bars, so text beyond its width is scrolled out of sight."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color:transparent;")
        self.setElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.setWidgetResizable(True)

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().event(event)

    def setElideMode(self, elideMode):
        if not isinstance(elideMode, QtCore.Qt.TextElideMode):
            raise TypeError("Argument must be of type Qt.TextElideMode")
        if elideMode == QtCore.Qt.TextElideMode.ElideMiddle:
            raise NotImplementedError("The hack being used to elidetext does not work for ElideMiddle")

        self._elide_mode = elideMode

    def minimumSizeHint(self):
        if self._elide_mode == QtCore.Qt.TextElideMode.ElideNone:
            return super().minimumSizeHint()
        else:
            actual_minimum_sizehint = self.widget().minimumSizeHint()
            return QtCore.QSize(0, actual_minimum_sizehint.height())

    def sizeHint(self):
        if self._elide_mode == QtCore.Qt.TextElideMode.ElideNone:
            return super().sizeHint()
        else:
            actual_sizehint = self.widget().sizeHint()
            return QtCore.QSize(0, actual_sizehint.height())

    def setWidget(self, widget):
        super().setWidget(widget)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            self.sizePolicy().horizontalPolicy(), widget.sizePolicy().verticalPolicy()))


class ElidedLabelContainer(QtWidgets.QWidget):
    """A widget that elides the text of a QLabel.

    Use this for a label created in code, before adding it to any layout or
    container widget; elide_label wraps one that is already in a layout. The
    label must be a single line of text, which may be rich text; ValueError is
    raised if it has word wrap enabled.
    """

    def __init__(self, label):
        super().__init__()
        if label.wordWrap():
            raise ValueError("Cannot elide label with word wrapping enabled")
        self.label = label
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0,0,0,0)
        self.ellipsis_label = QtWidgets.QLabel(ELLIPSIS)
        self.scroll_area = ElideScrollArea()
        self.scroll_area.setWidget(self.label)
        self.setElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.setSizePolicy(label.sizePolicy())
        self.scroll_area.horizontalScrollBar().rangeChanged.connect(self.update_elide_widget)
        self.update_elide_widget()

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.ToolTip:
            self.setToolTip(self.label.text())
        return super().event(event)

    def elideMode(self):
        """Return the Qt.TextElideMode in use."""
        return self._elide_mode

    def setElideMode(self, elideMode):
        """Set the side on which the text is elided: ElideLeft, ElideRight or ElideNone."""
        self.scroll_area.setElideMode(elideMode)
        self._elide_mode = elideMode

        if self.layout.count():
            self.layout.removeWidget(self.ellipsis_label)
            self.layout.removeWidget(self.scroll_area)
        if self._elide_mode == QtCore.Qt.TextElideMode.ElideLeft:
            self.layout.addWidget(self.ellipsis_label)
            self.layout.addWidget(self.scroll_area)
        elif self._elide_mode == QtCore.Qt.TextElideMode.ElideRight:
            self.layout.addWidget(self.scroll_area)
            self.layout.addWidget(self.ellipsis_label)

    def update_elide_widget(self):
        label_width = self.label.minimumSizeHint().width()

        width = self.width()
        if label_width > width:
            self.ellipsis_label.setText(ELLIPSIS)
        else:
            self.ellipsis_label.setText('')

        if self._elide_mode == QtCore.Qt.TextElideMode.ElideNone:
            return
        elif self._elide_mode == QtCore.Qt.TextElideMode.ElideLeft:
            self.scroll_area.ensureVisible(label_width, 0, 0, 0)
        elif self._elide_mode == QtCore.Qt.TextElideMode.ElideRight:
            self.scroll_area.ensureVisible(0, 0, 0, 0)

    def minimumSizeHint(self):
        return self.scroll_area.minimumSizeHint()

    def sizeHint(self):
        return self.scroll_area.minimumSizeHint()


def elide_label(label, layout, elide_mode):
    """Elide the text of a QLabel that is already in a QBoxLayout or QSplitter.

    The label is wrapped in an ElidedLabelContainer, which takes its place in
    the layout. Raises NotImplementedError for any other layout or for
    ElideMiddle, and ValueError if label is not in layout or has word wrap
    enabled.
    """
    if not (isinstance(layout, QtWidgets.QBoxLayout) or isinstance(layout, QtWidgets.QSplitter)):
        raise NotImplementedError("Only labels that are in QBoxLayouts or QSplitters supported")
    index = layout.indexOf(label)
    if index == -1:
        raise ValueError("Label not found in given layout")
    container = ElidedLabelContainer(label)
    label.setParent(container.scroll_area)
    label.setVisible(False)
    label.setVisible(True)
    layout.insertWidget(index, container)
    container.setElideMode(elide_mode)
