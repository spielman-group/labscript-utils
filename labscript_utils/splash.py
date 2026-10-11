#####################################################################
#                                                                   #
# /splash.py                                                        #
#                                                                   #
# Copyright 2018, Christopher Billington                            #
#                                                                   #
# This file is part of labscript_utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import sys
from labscript_utils import dedent

try:
    from qtutils.qt import QtWidgets, QtCore, QtGui
except ImportError as e:
    if 'DLL load failed' in str(e):
        msg = """Failed to load Qt DLL. This can be caused by application shortcuts
            not being configured to activate conda environments. Try running the
            following from within the activated conda environment to fix the shortcuts:

                desktop-app install blacs lyse runmanager runviewer"""
        raise ImportError(dedent(msg))
    raise

Qt = QtCore.Qt

# Importing this module creates no QApplication; only constructing Splash, or
# calling get_qapplication(), does. That is what lets sibling repositories'
# tests stub this module without putting a banner on screen.


def configure_qapplication(qapplication):
    """Apply labscript-wide QApplication configuration.

    On macOS this also sets the window icon from the application's
    ``_labscript_icon_path`` property, and, once per application, the Fusion style
    with the application's own palette.

    Returns
    -------
    QApplication
        ``qapplication``.
    """
    qapplication.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    if sys.platform == 'darwin':
        icon_path = qapplication.property('_labscript_icon_path')
        if icon_path:
            qapplication.setWindowIcon(QtGui.QIcon(icon_path))
        if not qapplication.property('_labscript_qapplication_configured'):
            # Native macOS styling looks inconsistent with the rest of the
            # suite. Use Qt's own style, keeping the palette so dark or light
            # appearance still follows the theme.
            palette = QtGui.QPalette(qapplication.palette())
            qapplication.setStyle('Fusion')
            qapplication.setPalette(palette)
            qapplication.setProperty('_labscript_qapplication_configured', True)
    return qapplication


def get_qapplication(application_name=None, icon_path=None):
    """Return the QApplication, creating it if there is none, and configure it.

    Parameters
    ----------
    application_name : str, optional
        Name to give a QApplication created here, as its first argument. Ignored
        if a QApplication already exists.
    icon_path : str, optional
        Path of the image to use as the application's window icon on macOS.
    """
    qapplication = QtWidgets.QApplication.instance()

    if qapplication is None:
        argv = sys.argv
        if application_name is not None:
            # Create a new argv so QApplication can alter it without mutating sys.argv.
            argv = [application_name] + argv[1:]

        qapplication = QtWidgets.QApplication(argv)

    if icon_path is not None:
        qapplication.setProperty('_labscript_icon_path', icon_path)
    return configure_qapplication(qapplication)


class Splash(QtWidgets.QFrame):
    """A splash screen showing an icon over a line of text.

    Constructing it creates and configures the QApplication if there is none.

    Parameters
    ----------
    application_name : str, optional
        Passed to :func:`get_qapplication`.

    Raises
    ------
    ValueError
        If the image at ``icon_path`` cannot be loaded.
    """

    w = 250
    h = 230
    imwidth = 150
    imheight = 150
    alpha = 0.875
    BG = '#ffffff'
    FG = '#000000'

    def __init__(self, icon_path, application_name=None):
        self.qapplication = get_qapplication(
            application_name=application_name, icon_path=icon_path
        )
        super().__init__()
        self.icon = QtGui.QPixmap()
        self.icon.load(icon_path)
        if self.icon.isNull():
            raise ValueError(f"Invalid image file: {icon_path}.\n")
        self.icon = self.icon.scaled(
            self.imwidth,
            self.imheight,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.text = 'Loading'
        self.setWindowFlags(Qt.WindowType.SplashScreen)
        self.setWindowOpacity(self.alpha)
        self.label = QtWidgets.QLabel(self.text)
        self.setStyleSheet(
            f"color: {self.FG}; background-color: {self.BG}; font-size: 10pt"
        )
        # Frame not necessary on macos, and looks ugly.
        if sys.platform != 'darwin':
            self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize(self.w, self.h)

        image_label = QtWidgets.QLabel()
        image_label.setPixmap(self.icon)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(image_label)
        layout.addWidget(self.label)

        self._paint_pending = False

    def paintEvent(self, event):
        self._paint_pending = False
        return super().paintEvent(event)

    def update_text(self, text):
        """Show ``text`` under the icon.

        Returns once the text has been painted, unless the window is not exposed.
        """
        self.text = text
        self.label.setText(text)
        self._paint_pending = True
        # Wait for the new text to be painted before the caller blocks, but only
        # while the window can be: macOS paints no window covered by others, so the
        # wait would last until the application was brought to the front.
        window = self.windowHandle()
        while self._paint_pending and window is not None and window.isExposed():
            QtCore.QCoreApplication.processEvents(
                QtCore.QEventLoop.ProcessEventsFlag.AllEvents
            )
            QtCore.QCoreApplication.sendPostedEvents()
