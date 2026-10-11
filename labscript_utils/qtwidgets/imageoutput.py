#####################################################################
#                                                                   #
# imageoutput.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import base64
import os

from qtutils.qt import QtCore, QtGui, QtWidgets
from qtutils.qt.QtCore import pyqtSignal as Signal

from labscript_utils import ensure_str

from . import file_dialogs
from .lockable import LockableOutput


class BrowseButton(QtWidgets.QPushButton):
    """A button that asks for an image file and sets it as ``image_output``'s value."""

    def __init__(self, image_output, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_output = image_output
        self.installEventFilter(self)
        self.clicked.connect(self.browse)
        self.last_opened_folder = ""

    def browse(self):
        supported_images = "Image files ("

        for image_format in QtGui.QImageReader.supportedImageFormats():
            supported_images += f"*.{image_format.data().decode()} "

        supported_images = supported_images[:-1]
        supported_images += ")"

        image_file = file_dialogs.open_file(
            self, 'Select image file to load', self.last_opened_folder, supported_images
        )
        if image_file is None:
            return
        if not os.path.exists(image_file):
            return

        self.last_opened_folder = os.path.dirname(image_file)

        raw_data = ''
        with open(image_file, 'rb') as f:
            raw_data = f.read()

        data = base64.b64encode(raw_data)

        self.image_output.value = data

    def eventFilter(self, obj, event):
        if (event.type() == QtCore.QEvent.Type.MouseButtonRelease
                and event.button() == QtCore.Qt.MouseButton.RightButton):
            self.image_output.popup_lock_menu(self, event.pos())
            return True

        return super().eventFilter(obj, event)


class ImageView(QtWidgets.QGraphicsView):
    def contextMenuEvent(self, event):
        self.parent().popup_lock_menu(self, event.pos())


class ImageOutput(LockableOutput, QtWidgets.QWidget):
    """A labelled button and a view that show and set a BLACS image output.

    The button loads an image from a file. Right-clicking the button or the view
    offers to lock the widget.

    Parameters
    ----------
    name : str
        The label text.
    width, height : int
        The size in pixels of the image, and of the view. Only an image of exactly
        this size can be shown.
    *args, **kwargs
        Passed to ``QWidget``.

    Attributes
    ----------
    imageUpdated : Signal(str)
        Emitted with the new ``value`` when an image has been set.
    """

    imageUpdated = Signal(str)

    def __init__(self, name, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum
        )

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)

        header_widget = QtWidgets.QWidget(self)
        header_layout = QtWidgets.QHBoxLayout(header_widget)

        self._label = QtWidgets.QLabel(name)
        header_layout.addWidget(self._label)

        self._browse_button = BrowseButton(self, 'Select Image')
        self._browse_button.setIcon(QtGui.QIcon(':/qtutils/fugue/image-import'))
        self._lock_target = self._browse_button
        header_layout.addWidget(self._browse_button)

        # The spacer keeps the label and button at the left.
        header_layout.addItem(
            QtWidgets.QSpacerItem(
                0, 0,
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )
        )

        self._layout.addWidget(header_widget)

        self.image_size = QtCore.QSize(width, height)

        self._scene = QtWidgets.QGraphicsScene(0, 0, width, height)
        self._scene.setBackgroundBrush(QtCore.Qt.GlobalColor.black)
        self._view = ImageView(self._scene)
        self._view.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
        )
        self._view.setStyleSheet("border: 0px")
        self._view.setMinimumSize(self.image_size)
        self._view.setMaximumSize(self.image_size)
        self._layout.addWidget(self._view)

        # The widget filters its own events, so that a right-click menu opens
        # even while it is disabled.
        self.installEventFilter(self)

        self._output = None

        # The image as base64 text.
        self._value = ""

        # The image item in the scene.
        self._pixmap_item = None

    def set_Image(self, Image, notify_old_Image=True, notify_new_Image=True):
        """Put a BLACS image output in charge of this widget.

        Nothing is notified when ``Image`` is the output already in charge.

        Parameters
        ----------
        Image : ImageOut or None
            The output to put in charge, or None for none.
        notify_old_Image : bool, optional
            Whether to remove this widget from the output that was in charge.
        notify_new_Image : bool, optional
            Whether to add this widget to ``Image``.
        """
        if Image != self._output:
            if self._output is not None and notify_old_Image:
                self._output.remove_widget(self)
            if Image is not None and notify_new_Image:
                Image.add_widget(self)
        self._output = Image

    def get_Image(self):
        """Return the BLACS image output in charge of this widget, or None."""
        return self._output

    @property
    def value(self):
        """str: the image shown, as base64 text.

        Setting it, from text or bytes, shows the image and emits ``imageUpdated``.
        An image that is not ``width`` by ``height`` pixels is refused with a
        warning dialog.
        """
        return self._value

    @value.setter
    def value(self, value):
        value = ensure_str(value)
        decoded_image = base64.b64decode(value)
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(
            decoded_image,
            flags=QtCore.Qt.ImageConversionFlag.AvoidDither
            | QtCore.Qt.ImageConversionFlag.ThresholdAlphaDither
            | QtCore.Qt.ImageConversionFlag.ThresholdDither,
        )
        if pixmap.size() != self.image_size:
            QtWidgets.QMessageBox.warning(
                self,
                "Failed to load image",
                f'The image size was incorrect. It must be {self.image_size.width()}'
                f'x{self.image_size.height()} pixels.',
                QtWidgets.QMessageBox.StandardButton.Ok,
                QtWidgets.QMessageBox.StandardButton.Ok,
            )
            return

        self._value = value
        pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)

        if self._pixmap_item is not None:
            self._scene.removeItem(self._pixmap_item)
        self._scene.addItem(pixmap_item)
        self._pixmap_item = pixmap_item

        self.imageUpdated.emit(self._value)
