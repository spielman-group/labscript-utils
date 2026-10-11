#####################################################################
#                                                                   #
# filewatcher.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from inspect import Parameter, signature
from queue import Queue, Empty
import threading
import os
import hashlib


class FileWatcher:
    """Detect modification, deletion, creation, or restoration of specific files
    (and all files in specific folders).

    Files are polled in a background thread until `stop` is called.

    Parameters
    ----------
    callback : callable
        Called whenever a file event is detected. It is called with
        ``(name, info, event)`` if `inspect.getfullargspec` lists more than
        two arguments for it (counting ``self`` of a bound method), otherwise
        with ``(name, info)``. `event` is one of ``'modified'``, ``'deleted'``,
        ``'created'``, ``'restored'`` or ``'original'``. The 'original' event,
        with `name` ``'all'``, reports a state change that results in the
        original file info at instantiation.
    files : iterable of str, optional
        Specific files to watch.
    folders : iterable of str, optional
        Specific folders to watch. If a file is created or deleted in any
        watched folder, it is added to or removed from the `files` attribute.
    clean_modified_info : dict, optional
        File info to detect modification and restoration with respect to. If
        None, or for files not present in it, the initial modified info is
        based on the first polling of files.
    hashable_types : iterable of str, optional
        File extensions, with the leading dot, for which the MD5 checksum is used to detect
        modification and restoration. Files of any other type are watched
        using their modified time, and restoration cannot be detected for
        them.
    interval : float, optional
        Polling interval in seconds. Default 1.
    **kwargs
        `modified_times` is accepted as a synonym for `clean_modified_info`,
        which takes precedence.
    """

    def __init__(self, callback, files=None, folders=None, clean_modified_info=None,
                 hashable_types=None, interval=1, **kwargs):
        positional = [
            p for p in signature(callback).parameters.values()
            if p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(positional) > 2:
            # For backwards compatability, allow callback to have only two args
            self.callback = callback
        else:
            self.callback = lambda name, info, event: callback(name, info)
        self.lock = threading.Lock()

        self.hashable_types = (
            [] if hashable_types is None else [x.lower() for x in hashable_types]
        )
        self.files = set()
        self.folders = set()

        # Backwards compat for BLACS before hashing was introduced:
        if 'modified_times' in kwargs and clean_modified_info is None:
            clean_modified_info = kwargs['modified_times']

        if clean_modified_info is None:
            clean_modified_info = {}
        self.clean_modified_info = clean_modified_info.copy()

        if files:
            self.add_files(files)
        if folders:
            self.add_folders(folders)
        self.update_files(trigger_callback=False)

        # Remove keys from clean_modified_info that are not in the files watchlist:
        for name in self.clean_modified_info.copy():
            if name not in self.files:
                del self.clean_modified_info[name]

        self.modified_info = self.clean_modified_info.copy()

        self.main = threading.Thread(target=self.mainloop, daemon=True)
        self.running = True
        self.interval = interval
        self._stopping = Queue()
        self.main.start()

    def mainloop(self):
        stopping = False
        while not stopping:
            try:
                self._stopping.get(timeout=self.interval)
            except Empty:
                stopping = False
            else:
                stopping = True
            # We run one final time if stopping so that after we have stopped,
            # get_modified_info() is guaranteed to reflect any events prior to stop()
            # being called
            with self.lock:
                self.update_files(trigger_callback=not stopping)
                self.check(trigger_callback=not stopping)

    def update_files(self, folders=None, trigger_callback=True, recursive=True):
        """Add the files in folders to the watchlist, `files`.

        Parameters
        ----------
        folders : iterable of str, optional
            Folders to scan. Default is the `folders` attribute.
        trigger_callback : bool, optional
            Whether to call the callback with a 'created' event for each file
            added. Default True.
        recursive : bool, optional
            Whether to scan subfolders too. Default True.
        """
        if folders is None:
            folders = self.folders
        for folder in folders:
            try:
                for name in os.listdir(folder):
                    path = os.path.join(folder, name)
                    # Recurse into subdirectories
                    if recursive and os.path.isdir(path):
                        self.update_files([path], trigger_callback)
                    else:
                        if not path in self.files:
                            self.files.add(path)
                            if trigger_callback:
                                self.callback(
                                    path, os.path.getmtime(path), 'created')
            except OSError:
                # Folder has been deleted. File deletion will still be
                # detected, so we can ignore this.
                continue

    def _modified_info_of_file(self, name):
        try:
            # If extension is a hashable type, use hash for modified_info
            if os.path.splitext(name)[-1].lower() in self.hashable_types:
                with open(name, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
            elif os.path.isdir(name):
                # Modified info of a directory is a hash of its entries:
                entries = os.listdir(os.fsencode(name))
                return hashlib.md5(b'\0'.join(entries)).hexdigest()
            else:
                return os.path.getmtime(name)
        except (OSError, IOError):
            # If it doesn't exist or is inaccessible, modified info is None
            return None

    def check(self, trigger_callback=True):
        """Poll the watched files once, calling the callback for each event."""
        check_all = False
        deleted_files = set()
        for name in self.files:
            modified_info = self._modified_info_of_file(name)
            previous_modified_info = self.modified_info.setdefault(name, modified_info)
            self.modified_info[name] = modified_info
            if modified_info != previous_modified_info:
                if modified_info is None:
                    if trigger_callback:
                        self.callback(name, modified_info, 'deleted')
                    deleted_files.add(name)
                    check_all = True
                elif modified_info == self.clean_modified_info.get(name, None):
                    if trigger_callback:
                        self.callback(name, modified_info, 'restored')
                    check_all = True
                elif name in self.modified_info:
                    if trigger_callback:
                        self.callback(name, modified_info, 'modified')
        for name in deleted_files:
            # Keep monitoring deleted files if they were explicitly added, since we want
            # to be able to detect them being restored:
            if name not in self.clean_modified_info:
                self.files.remove(name)
                del self.modified_info[name]
        if (
            check_all
            and self.modified_info == self.clean_modified_info
            and self.files == self.clean_modified_info.keys()
            and trigger_callback
        ):
            self.callback('all', '', 'original')

    def stop(self):
        """Stop polling.

        A final poll without callbacks is made, so that `get_modified_info`
        reflects the files as of this call.

        Raises
        ------
        RuntimeError
            If the watcher has already been stopped.
        """
        with self.lock:
            if not self.running:
                raise RuntimeError("Not running")
            self._stopping.put(None)
            self.running = False
        self.main.join()
        self.main = None

    def add_file(self, path):
        """Add a single file to the watchlist. See `add_files`."""
        self.add_files((path,))

    def get_clean_modified_info(self):
        """Return a copy of the modified info that files are compared against.

        Returns
        -------
        dict
            File name to its modified time or checksum, as of instantiation or
            when the file was added.
        """
        with self.lock:
            return self.clean_modified_info.copy()

    def get_modified_info(self):
        """Return a copy of the modified info as of the latest poll.

        Returns
        -------
        dict
            File name to its modified time or checksum.
        """
        with self.lock:
            return self.modified_info.copy()

    def get_modified_times(self):
        """Synonym for `get_modified_info`."""
        return self.get_modified_info()

    def _set_clean_modified_info(self, new_files, clean_modified_info):
        # Remove keys from the clean_modified_info that are not in the files
        # watchlist:
        for name in self.clean_modified_info.copy():
            if name not in self.files:
                del self.clean_modified_info[name]
        # For all files added to the watchlist that we were not given a
        # clean_modified_info for, set it based on their info now:
        for name in new_files:
            if name in clean_modified_info:
                self.clean_modified_info[name] = clean_modified_info[name]
            elif name not in self.clean_modified_info:
                self.clean_modified_info[name] = self._modified_info_of_file(name)

    def add_files(self, files, clean_modified_info=None):
        """Add files to the watchlist.

        Parameters
        ----------
        files : iterable of str
            Files to watch.
        clean_modified_info : dict, optional
            Modified info to detect modification and restoration of these
            files with respect to. Files not in it are compared against their
            info when added.
        """
        if clean_modified_info is None:
            clean_modified_info = {}
        with self.lock:
            self.files = self.files.union(set(files))
            self._set_clean_modified_info(files, clean_modified_info)

    def add_folders(self, folders, clean_modified_info=None):
        """Add folders to the watchlist, along with the files they contain.

        Parameters
        ----------
        folders : iterable of str
            Folders to watch.
        clean_modified_info : dict, optional
            As for `add_files`, for the files found in the folders.
        """
        if clean_modified_info is None:
            clean_modified_info = {}
        with self.lock:
            self.folders = self.folders.union(set(folders))
            initial_files = self.files.copy()
            self.update_files(trigger_callback=False)
            new_files = self.files - initial_files
            self._set_clean_modified_info(new_files, clean_modified_info)
