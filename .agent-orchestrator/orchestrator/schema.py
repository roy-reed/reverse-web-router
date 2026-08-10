"""Minimal JSON Schema (draft-07 subset) validation — standard library only.

Fail-closed by design: unknown enum values, missing required properties,
unexpected additional properties, and type mismatches are all reported as
validation errors.

Supported keywords: ``type``, ``enum``, ``const``, ``properties``,
``required``, ``additionalProperties``, ``items``, ``minItems``, ``maxItems``,
``uniqueItems``, ``minLength``, ``maxLength``, ``pattern``, ``minimum``,
``maximum``, ``anyOf``, ``allOf``, ``oneOf``, ``not``, and local ``$ref``
(``#/$defs/...`` / ``#/definitions/...``).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .errors import SchemaValidationError

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def _is_hashable(value: Any) -> bool:
    try:
        hash(value)
        return True
    except TypeError:
        return False


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


class SchemaValidator:
    """Validate one instance against one schema object."""

    def __init__(self, schema: Dict[str, Any]):
        self.root = schema

    def validate(self, instance: Any) -> List[str]:
        errors: List[str] = []
        self._check(instance, self.root, "$", errors)
        return errors

    def _resolve(self, ref: str) -> Dict[str, Any]:
        if not ref.startswith("#/"):
            raise SchemaValidationError(["unsupported $ref %r (only local refs are supported)" % (ref,)])
        parts = ref[2:].split("/")
        node: Any = self.root
        for part in parts:
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                raise SchemaValidationError(["cannot resolve $ref %r" % (ref,)])
            node = node[part]
        if not isinstance(node, dict):
            raise SchemaValidationError(["$ref %r does not point to a schema object" % (ref,)])
        return node

    def _check(self, instance: Any, schema: Dict[str, Any], path: str, errors: List[str]) -> None:
        if not isinstance(schema, dict):
            raise SchemaValidationError(["schema at %s must be an object" % (path,)])
        if "$ref" in schema:
            self._check(instance, self._resolve(schema["$ref"]), path, errors)
            return

        schema_type = schema.get("type")
        if schema_type is not None:
            types = schema_type if isinstance(schema_type, list) else [schema_type]
            if not any(_TYPE_CHECKS.get(t, lambda v: False)(instance) for t in types):
                errors.append("%s: expected type %s, got %s" % (path, "/".join(types), _type_name(instance)))
                return  # stop: further keyword checks assume the type

        if "const" in schema and instance != schema["const"]:
            errors.append("%s: expected constant %r, got %r" % (path, schema["const"], instance))
        if "enum" in schema and not any(instance == e for e in schema["enum"]):
            errors.append("%s: value %r not in enum %r" % (path, instance, schema["enum"]))

        if isinstance(instance, dict):
            self._check_object(instance, schema, path, errors)
        elif isinstance(instance, list):
            self._check_array(instance, schema, path, errors)
        elif isinstance(instance, str):
            self._check_string(instance, schema, path, errors)
        elif isinstance(instance, (int, float)) and not isinstance(instance, bool):
            self._check_number(instance, schema, path, errors)

        combinators = []
        if "anyOf" in schema:
            combinators.append(("anyOf", schema["anyOf"], lambda n: n >= 1))
        if "allOf" in schema:
            combinators.append(("allOf", schema["allOf"], lambda n: n == len(schema["allOf"])))
        if "oneOf" in schema:
            combinators.append(("oneOf", schema["oneOf"], lambda n: n == 1))
        for name, subs, ok in combinators:
            matches = 0
            for sub in subs:
                sub_errors: List[str] = []
                self._check(instance, sub, path, sub_errors)
                if not sub_errors:
                    matches += 1
            if not ok(matches):
                errors.append("%s: failed %s (matched %d of %d)" % (path, name, matches, len(subs)))
        if "not" in schema:
            sub_errors = []
            self._check(instance, schema["not"], path, sub_errors)
            if not sub_errors:
                errors.append("%s: must not match schema" % (path,))

    def _check_object(self, instance: Dict[str, Any], schema: Dict[str, Any], path: str, errors: List[str]) -> None:
        properties = schema.get("properties") or {}
        for key, value in instance.items():
            if key in properties:
                self._check(value, properties[key], "%s.%s" % (path, key), errors)
            elif "additionalProperties" in schema:
                additional = schema["additionalProperties"]
                if additional is False:
                    errors.append("%s: unexpected property %r" % (path, key))
                elif isinstance(additional, dict):
                    self._check(value, additional, "%s.%s" % (path, key), errors)
        for key in schema.get("required") or []:
            if key not in instance:
                errors.append("%s: missing required property %r" % (path, key))
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append("%s: too few properties" % (path,))
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            errors.append("%s: too many properties" % (path,))

    def _check_array(self, instance: List[Any], schema: Dict[str, Any], path: str, errors: List[str]) -> None:
        items = schema.get("items")
        if isinstance(items, dict):
            for i, value in enumerate(instance):
                self._check(value, items, "%s[%d]" % (path, i), errors)
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("%s: expected at least %d items, got %d" % (path, schema["minItems"], len(instance)))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append("%s: expected at most %d items, got %d" % (path, schema["maxItems"], len(instance)))
        if schema.get("uniqueItems"):
            seen = [_freeze(v) for v in instance]
            if len(set(seen)) != len(seen):
                errors.append("%s: items must be unique" % (path,))

    def _check_string(self, instance: str, schema: Dict[str, Any], path: str, errors: List[str]) -> None:
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: shorter than minLength %d" % (path, schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: longer than maxLength %d" % (path, schema["maxLength"]))
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append("%s: %r does not match pattern %r" % (path, instance, schema["pattern"]))

    def _check_number(self, instance: float, schema: Dict[str, Any], path: str, errors: List[str]) -> None:
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: %s is below minimum %s" % (path, instance, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("%s: %s is above maximum %s" % (path, instance, schema["maximum"]))


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


@lru_cache(maxsize=None)
def load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / name
    if not path.exists():
        raise SchemaValidationError(["schema file %s not found" % (name,)])
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate(instance: Any, schema_name: str) -> List[str]:
    return SchemaValidator(load_schema(schema_name)).validate(instance)


def validate_or_raise(instance: Any, schema_name: str) -> None:
    errors = validate(instance, schema_name)
    if errors:
        raise SchemaValidationError(errors)


# ---- typed entry points used by scripts, workflows and tests -----------------

def validate_run(record: Dict[str, Any]) -> List[str]:
    errors = validate(record, "run.schema.json")
    if isinstance(record, dict) and isinstance(record.get("budget"), dict):
        errors.extend("$.budget" + item[1:] for item in validate_budget(record["budget"]))
    return errors


def validate_work_unit(contract: Dict[str, Any]) -> List[str]:
    errors = validate(contract, "work-unit.schema.json")
    if isinstance(contract, dict):
        if isinstance(contract.get("worker"), dict):
            errors.extend("$.worker" + item[1:] for item in validate_worker_selection(contract["worker"]))
        if isinstance(contract.get("budget"), dict):
            errors.extend("$.budget" + item[1:] for item in validate_budget(contract["budget"]))
    return errors


def validate_envelope(envelope: Dict[str, Any]) -> List[str]:
    return validate(envelope, "rwrouter2.schema.json")


def validate_worker_selection(selection: Dict[str, Any]) -> List[str]:
    return validate(selection, "worker-selection.schema.json")


def validate_dependency_state(record: Dict[str, Any]) -> List[str]:
    return validate(record, "dependency-state.schema.json")


def validate_budget(budget: Dict[str, Any]) -> List[str]:
    return validate(budget, "budget.schema.json")
