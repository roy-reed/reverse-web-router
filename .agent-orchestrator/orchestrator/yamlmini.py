"""Minimal YAML subset parser/serializer (standard library only).

Supports the subset of YAML used by this repository:

- nested mappings via indentation;
- sequences of scalars and sequences of mappings (``- key: value``);
- inline flow sequences ``[a, b, c]``;
- block literal scalars (``key: |`` / ``key: |-``);
- quoted and plain scalars;
- ``#`` comments on their own lines or after a space.

It is intentionally NOT a full YAML implementation. Unknown constructs raise
``YamlParseError`` (fail closed).
"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple


class YamlParseError(ValueError):
    pass


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1] in " \t":
                return line[:i]
    return line


def _next_nonblank(lines: List[str], idx: int) -> Optional[int]:
    while idx < len(lines):
        if lines[idx].strip():
            return idx
        idx += 1
    return None


def _unescape_double(s: str) -> str:
    out = []
    i = 0
    mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            out.append(mapping.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _scalar(text: str) -> Any:
    text = text.strip()
    if text == "" or text.lower() in ("null", "~"):
        return None
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return _unescape_double(text[1:-1])
    if len(text) >= 2 and text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _parse_flow_seq(text: str) -> List[Any]:
    inner = text.strip()
    if not (inner.startswith("[") and inner.endswith("]")):
        raise YamlParseError("invalid flow sequence: %r" % (text,))
    inner = inner[1:-1]
    if not inner.strip():
        return []
    parts = []
    buf = []
    in_single = False
    in_double = False
    for ch in inner:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "," and not in_single and not in_double:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [_scalar(p) for p in parts]


def _parse_block_scalar(lines: List[str], idx: int, indent: int, header: str) -> Tuple[str, int]:
    parts = []
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            parts.append("")
            idx += 1
            continue
        if _indent(line) <= indent:
            break
        parts.append(line[_indent(line):])
        idx += 1
    while parts and parts[-1] == "":
        parts.pop()
    text = "\n".join(parts)
    if header.endswith("|+") and parts:
        text = text + "\n"
    return text, idx


def _parse_map(lines: List[str], idx: int, min_indent: int) -> Tuple[dict, int]:
    result = {}
    while True:
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines):
            break
        line = lines[idx]
        indent = _indent(line)
        if indent < min_indent:
            break
        content = _strip_comment(line[indent:]).strip()
        if not content:
            idx += 1
            continue
        if content.startswith("-"):
            break
        if ":" not in content:
            raise YamlParseError("line %d: expected 'key: value', got %r" % (idx + 1, content))
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        idx += 1
        if rest == "":
            nidx = _next_nonblank(lines, idx)
            if nidx is None:
                value = None
            else:
                nindent = _indent(lines[nidx])
                if nindent > indent:
                    value, idx = _parse_node(lines, idx, nindent)
                else:
                    value = None
        elif rest.startswith("|"):
            value, idx = _parse_block_scalar(lines, idx, indent, rest)
        elif rest.startswith("["):
            value = _parse_flow_seq(rest)
        else:
            value = _scalar(rest)
        result[key] = value
    return result, idx


def _parse_inline_map(lines: List[str], idx: int, seq_indent: int, key: str, vrest: str) -> Tuple[dict, int]:
    m = {}
    if vrest == "":
        nidx = _next_nonblank(lines, idx)
        if nidx is not None and _indent(lines[nidx]) > seq_indent:
            m[key], idx = _parse_node(lines, idx, _indent(lines[nidx]))
        else:
            m[key] = None
    elif vrest.startswith("|"):
        m[key], idx = _parse_block_scalar(lines, idx, seq_indent, vrest)
    elif vrest.startswith("["):
        m[key] = _parse_flow_seq(vrest)
    else:
        m[key] = _scalar(vrest)
    while True:
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines):
            break
        line = lines[idx]
        ind = _indent(line)
        if ind <= seq_indent:
            break
        content = _strip_comment(line[ind:]).strip()
        if not content or content.startswith("-"):
            break
        if ":" not in content:
            raise YamlParseError("line %d: expected 'key: value'" % (idx + 1,))
        k2, _, r2 = content.partition(":")
        k2 = k2.strip()
        r2 = r2.strip()
        idx += 1
        if r2 == "":
            nidx = _next_nonblank(lines, idx)
            if nidx is not None and _indent(lines[nidx]) > ind:
                m[k2], idx = _parse_node(lines, idx, _indent(lines[nidx]))
            else:
                m[k2] = None
        elif r2.startswith("|"):
            m[k2], idx = _parse_block_scalar(lines, idx, ind, r2)
        elif r2.startswith("["):
            m[k2] = _parse_flow_seq(r2)
        else:
            m[k2] = _scalar(r2)
    return m, idx


def _parse_seq(lines: List[str], idx: int, min_indent: int) -> Tuple[list, int]:
    items = []
    seq_indent = None
    while True:
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines):
            break
        line = lines[idx]
        indent = _indent(line)
        if indent < min_indent:
            break
        content = _strip_comment(line[indent:]).strip()
        if not content.startswith("-"):
            break
        if seq_indent is None:
            seq_indent = indent
        elif indent != seq_indent:
            break
        rest = content[1:].strip()
        idx += 1
        if rest == "":
            nidx = _next_nonblank(lines, idx)
            if nidx is None:
                items.append(None)
            else:
                nindent = _indent(lines[nidx])
                if nindent > indent:
                    value, idx = _parse_node(lines, idx, nindent)
                    items.append(value)
                else:
                    items.append(None)
        elif rest.startswith("["):
            items.append(_parse_flow_seq(rest))
        elif ":" in rest and not rest.startswith("["):
            key, _, vrest = rest.partition(":")
            m, idx = _parse_inline_map(lines, idx, indent, key.strip(), vrest.strip())
            items.append(m)
        else:
            items.append(_scalar(rest))
    return items, idx


def _parse_node(lines: List[str], idx: int, min_indent: int) -> Tuple[Any, int]:
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines):
        return None, idx
    line = lines[idx]
    indent = _indent(line)
    if indent < min_indent:
        return None, idx
    content = _strip_comment(line[indent:]).strip()
    if content == "-" or content.startswith("- "):
        return _parse_seq(lines, idx, min_indent)
    return _parse_map(lines, idx, min_indent)


def parse(text: str) -> Any:
    """Parse a YAML subset document into plain Python objects."""
    text = text.lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    value, idx = _parse_node(lines, 0, 0)
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines):
        raise YamlParseError("unexpected trailing content at line %d: %r" % (idx + 1, lines[idx]))
    return value


def _needs_quote(s: str) -> bool:
    if s == "":
        return True
    if s.lower() in ("true", "false", "null", "~"):
        return True
    try:
        int(s)
        return True
    except ValueError:
        pass
    try:
        float(s)
        return True
    except ValueError:
        pass
    if re.search(r"[:#\[\]{}\n\"',]|^\s|\s$|^- ", s):
        return True
    return False


def _quote(s: str) -> str:
    if not _needs_quote(s):
        return s
    esc = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"%s"' % esc


def _is_plain_scalar(x: Any) -> bool:
    return x is None or isinstance(x, (str, int, float, bool))


def _scalar_repr(x: Any) -> str:
    if x is None:
        return "null"
    if x is True:
        return "true"
    if x is False:
        return "false"
    if isinstance(x, (int, float)):
        return str(x)
    return _quote(str(x))


def _dump_list(items: list, indent: int) -> str:
    pad = "  " * indent
    out = []
    for item in items:
        if isinstance(item, dict):
            if not item:
                out.append("%s- {}" % pad)
                continue
            first = True
            for k, v in item.items():
                ks = _quote(k)
                prefix = ("%s- %s" if first else "%s  %s") % (pad, ks)
                first = False
                if isinstance(v, dict):
                    out.append("%s:" % prefix)
                    out.append(_dump_dict(v, indent + 2))
                elif isinstance(v, list):
                    if v and all(_is_plain_scalar(x) for x in v):
                        out.append("%s: [%s]" % (prefix, ", ".join(_scalar_repr(x) for x in v)))
                    else:
                        out.append("%s:" % prefix)
                        out.append(_dump_list(v, indent + 2))
                else:
                    out.append("%s: %s" % (prefix, _scalar_repr(v)))
        else:
            out.append("%s- %s" % (pad, _scalar_repr(item)))
    return "\n".join(out)


def _dump_dict(obj: dict, indent: int) -> str:
    pad = "  " * indent
    out = []
    for k, v in obj.items():
        ks = _quote(k)
        if isinstance(v, dict):
            out.append("%s%s:" % (pad, ks))
            out.append(_dump_dict(v, indent + 1))
        elif isinstance(v, list):
            if v and all(_is_plain_scalar(x) for x in v):
                out.append("%s%s: [%s]" % (pad, ks, ", ".join(_scalar_repr(x) for x in v)))
            else:
                out.append("%s%s:" % (pad, ks))
                out.append(_dump_list(v, indent + 1))
        elif isinstance(v, str) and "\n" in v:
            out.append("%s%s: |-" % (pad, ks))
            for ln in v.split("\n"):
                out.append("%s  %s" % (pad, ln))
        else:
            out.append("%s%s: %s" % (pad, ks, _scalar_repr(v)))
    return "\n".join(out)


def dumps(obj: Any, indent: int = 0) -> str:
    """Serialize plain Python objects to the YAML subset this parser reads."""
    if isinstance(obj, dict):
        return _dump_dict(obj, indent)
    if isinstance(obj, list):
        return _dump_list(obj, indent)
    return _scalar_repr(obj)
