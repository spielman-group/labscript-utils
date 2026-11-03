#####################################################################
#                                                                   #
# /tests/conftest.py                                                #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
"""Keep test windows and exception dialogs off the user's screen.

These defaults must precede test-module imports: qtutils imports Qt, and excepthook
reads its environment flag once. Offscreen rendering still lets geometry tests show
their widgets. Explicit environment settings override these defaults.
"""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK', '1')
