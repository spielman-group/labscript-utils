#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/row_order.py                           #
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
"""The order of a list's rows after the selected ones are moved."""

DIRECTIONS = ('up', 'down', 'top', 'bottom')


def moved_row_order(n_rows, selected_rows, direction):
    """Return where each row goes when the selected rows are moved.

    Selected rows keep their order among themselves. Moving up or down shifts each
    selected row by one past an unselected neighbour; one blocked by the end of the
    list, or by a selected row that cannot move, stays where it is.

    Parameters
    ----------
    n_rows : int
        The number of rows.
    selected_rows : iterable of int
        The selected rows.
    direction : str
        One of ``'up'``, ``'down'``, ``'top'`` or ``'bottom'``.

    Returns
    -------
    list of int
        The new position of each row, indexed by its old one.

    Raises
    ------
    ValueError
        If ``direction`` is not one of the four.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f'direction must be one of {DIRECTIONS}, not {direction!r}')
    selected = set(selected_rows)
    # The old row at each new position:
    rows = list(range(n_rows))
    if direction in ('top', 'bottom'):
        moved = [row for row in rows if row in selected]
        kept = [row for row in rows if row not in selected]
        rows = moved + kept if direction == 'top' else kept + moved
    else:
        step = -1 if direction == 'up' else 1
        # The row nearest the end it moves towards goes first, so that a block of
        # selected rows moves together:
        positions = range(n_rows) if direction == 'up' else reversed(range(n_rows))
        for position in positions:
            target = position + step
            if rows[position] in selected and 0 <= target < n_rows:
                if rows[target] not in selected:
                    rows[position], rows[target] = rows[target], rows[position]
    order = [0] * n_rows
    for new_position, row in enumerate(rows):
        order[row] = new_position
    return order
