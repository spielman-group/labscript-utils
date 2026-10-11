#####################################################################
#                                                                   #
# /labscript_utils/lookup_format.py                                 #
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

import ast
import string


class InvalidLookupFormatField(ValueError):
    """Raised when a lookup-format field is not valid lookup-only syntax."""


class UnresolvedLookupField(LookupError):
    """Raised when a lookup could not be resolved from the provided context."""

    def __init__(self, root_name):
        super().__init__(root_name)
        self.root_name = root_name


def _escape_braces(text):
    return text.replace('{', '{{').replace('}', '}}')


def unescape_braces(text):
    """Undo the brace escaping applied when producing a template, to display it.

    Do not unescape a value that goes on to the per-shot pass, which needs the
    escaping.
    """
    return text.replace('{{', '{').replace('}}', '}')


def format_lookup_string(
    template,
    context,
    dt=None,
    preserve_unresolved_roots=(),
):
    """Format a template using optional ``strftime`` plus lookup-only fields.

    Parameters
    ----------
    template : str
        Format template. A field is a root name followed by any number of
        ``[key]`` lookups.
    preserve_unresolved_roots : iterable of str, optional
        Root names that may be preserved when a lookup below them is unresolved.

    Raises
    ------
    ValueError
        If the template's braces are unbalanced.
    InvalidLookupFormatField
        If a field is not valid lookup-only syntax.
    UnresolvedLookupField
        If a lookup cannot be resolved and its root is not preserved.

    Notes
    -----
    Preserving unresolved lookups makes the result a template for a further pass,
    so literal text and resolved values are brace-escaped to survive it. Without
    preservation the result is final text and is emitted verbatim.
    """
    if dt is not None:
        template = dt.strftime(template)
    formatter = _LookupFormatter(
        context,
        preserve_unresolved_roots=preserve_unresolved_roots,
    )
    return formatter.format(template)


class _LookupFormatter:
    def __init__(
        self,
        context,
        preserve_unresolved_roots=(),
    ):
        self.context = context
        self.preserve_unresolved_roots = set(preserve_unresolved_roots)
        # Preserved placeholders only mean anything to a later pass, so when any
        # preservation is enabled this pass is producing a template rather than
        # final text.
        self.produces_template = bool(self.preserve_unresolved_roots)
        self.formatter = string.Formatter()

    def format(self, template, produces_template=None):
        if produces_template is None:
            produces_template = self.produces_template
        parts = []
        for literal_text, field_name, format_spec, conversion in self.formatter.parse(template):
            parts.append(_escape_braces(literal_text) if produces_template else literal_text)
            if field_name is None:
                continue
            placeholder = self._reconstruct_placeholder(
                field_name, conversion, format_spec
            )
            try:
                value = self._resolve_field(field_name)
                if conversion:
                    value = self.formatter.convert_field(value, conversion)
                if format_spec:
                    # A format spec is consumed by this pass, never re-parsed.
                    format_spec = self.format(format_spec, produces_template=False)
                formatted = self.formatter.format_field(value, format_spec)
                # A resolved value containing a brace would otherwise be read as
                # a field by the next pass.
                parts.append(_escape_braces(formatted) if produces_template else formatted)
            except UnresolvedLookupField as exc:
                if exc.root_name in self.preserve_unresolved_roots:
                    # The placeholder must stay parseable for the next pass.
                    parts.append(placeholder)
                else:
                    raise
        return ''.join(parts)

    def _resolve_field(self, field_name):
        root_name, lookups = _parse_lookup_field(field_name)
        try:
            value = self.context[root_name]
            for lookup in lookups:
                value = value[lookup]
        except KeyError:
            raise UnresolvedLookupField(root_name)
        return value

    @staticmethod
    def _reconstruct_placeholder(field_name, conversion, format_spec):
        placeholder = '{' + field_name
        if conversion:
            placeholder += '!' + conversion
        if format_spec:
            placeholder += ':' + format_spec
        placeholder += '}'
        return placeholder


def _parse_lookup_field(field_name):
    field_name = str(field_name)
    length = len(field_name)
    index = 0

    root_name, index = _parse_identifier(field_name, index)
    lookups = []

    while index < length:
        if field_name[index] != '[':
            msg = f"Invalid lookup-format field {field_name!r}"
            raise InvalidLookupFormatField(msg)
        closing_index = field_name.find(']', index + 1)
        if closing_index == -1:
            msg = f"Invalid lookup-format field {field_name!r}"
            raise InvalidLookupFormatField(msg)
        lookup_text = field_name[index + 1 : closing_index].strip()
        if not lookup_text:
            msg = f"Invalid lookup-format field {field_name!r}"
            raise InvalidLookupFormatField(msg)
        lookups.append(_parse_lookup_key(lookup_text))
        index = closing_index + 1

    return root_name, lookups


def _parse_identifier(field_name, index):
    if index >= len(field_name):
        msg = f"Invalid lookup-format field {field_name!r}"
        raise InvalidLookupFormatField(msg)

    start = index
    first = field_name[index]
    if not (first.isalpha() or first == '_'):
        msg = f"Invalid lookup-format field {field_name!r}"
        raise InvalidLookupFormatField(msg)
    index += 1

    while index < len(field_name):
        char = field_name[index]
        if char.isalnum() or char == '_':
            index += 1
            continue
        break

    return field_name[start:index], index


def _parse_lookup_key(lookup_text):
    if lookup_text[0] in ('"', "'"):
        try:
            return ast.literal_eval(lookup_text)
        except (SyntaxError, ValueError) as exc:
            msg = f"Invalid lookup-format key {lookup_text!r}"
            raise InvalidLookupFormatField(msg) from exc
    try:
        return int(lookup_text)
    except ValueError:
        return lookup_text
