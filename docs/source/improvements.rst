Possible improvements
=====================

* Runviewer's channel list, lyse's routine lists and runmanager's axes are reordered with up, down, top and bottom buttons, which modern interfaces have replaced with drag and drop; all three call :meth:`labscript_utils.qtwidgets.leftclick.MovableRowsMixin.move_selected_rows`, so the change can be made in one place.
