from __future__ import annotations

import unittest

import _bootstrap  # noqa: F401

from orchestrator.yamlmini import YamlParseError, dumps, parse


class YamlMiniTests(unittest.TestCase):
    def test_nested_mapping_and_scalars(self) -> None:
        doc = parse(
            "a:\n"
            "  b: 1\n"
            "  c: true\n"
            "  d: null\n"
            "  e: 1.5\n"
            "  f: \"x\\ty\"\n"
            "  g: 'it''s'\n"
        )
        self.assertEqual(doc, {"a": {"b": 1, "c": True, "d": None, "e": 1.5, "f": "x\ty", "g": "it's"}})

    def test_comments_respect_quotes(self) -> None:
        doc = parse("k: \"a # not comment\" # real comment\nv: x#y\n# whole line\n")
        self.assertEqual(doc, {"k": "a # not comment", "v": "x#y"})

    def test_flow_sequence_with_quoted_comma(self) -> None:
        self.assertEqual(parse("xs: [1, 'a,b', \"c\"]\n"), {"xs": [1, "a,b", "c"]})
        self.assertEqual(parse("xs: []\n"), {"xs": []})

    def test_block_sequences(self) -> None:
        doc = parse("xs:\n  - one\n  - two\nms:\n  - name: a\n    n: 1\n  - name: b\n    n: 2\n")
        self.assertEqual(doc, {"xs": ["one", "two"], "ms": [{"name": "a", "n": 1}, {"name": "b", "n": 2}]})

    def test_block_literal_scalar(self) -> None:
        doc = parse("run: |\n  line1\n  line2\nnext: 1\n")
        self.assertEqual(doc["run"].rstrip("\n"), "line1\nline2")
        self.assertEqual(doc["next"], 1)

    def test_round_trip(self) -> None:
        obj = {"name": "w", "flags": [True, False], "items": [{"k": "v: colon"}], "n": 3}
        self.assertEqual(parse(dumps(obj)), obj)

    def test_invalid_flow_sequence_fails_closed(self) -> None:
        with self.assertRaises(YamlParseError):
            parse("xs: [1, 2\n")


if __name__ == "__main__":
    unittest.main()
