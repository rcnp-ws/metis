"""Device 定義の読み込み・検証・系列展開。DB には依存しない。

JSON Schema は contracts/schemes の既存ファイルを使用する。
quantity/role の DB 登録確認は呼び出し側が行う。
"""

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from itertools import product
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class DeviceDefinitionError(ValueError):
    """JSON の形式または定義の整合性が不正。"""


@dataclass(frozen=True)
class ExpandedField:
    field_path: str
    quantity: str
    role: str
    unit: str | None = None
    description: str | None = None


IDENTIFIER = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", re.ASCII)
PATH = re.compile(r"/(?:[a-z][a-z0-9]*(?:_[a-z0-9]+)*|[0-9]+)(?:/(?:[a-z][a-z0-9]*(?:_[a-z0-9]+)*|[0-9]+))*", re.ASCII)
VARIABLE = re.compile(r"\{([a-z][a-z0-9]*(?:_[a-z0-9]+)*)\}", re.ASCII)


def load_json(path: str | Path) -> dict[str, Any]:
    """JSON オブジェクトを読み込む。同名キーの重複も拒否する。"""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DeviceDefinitionError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise DeviceDefinitionError(f"Invalid JSON constant: {value}")

    try:
        with Path(path).open(encoding="utf-8") as stream:
            result = json.load(
                stream, object_pairs_hook=unique_object,
                parse_constant=invalid_constant,
            )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise DeviceDefinitionError(f"{path}: {exc}") from exc
    if not isinstance(result, dict):
        raise DeviceDefinitionError(f"{path}: expected a JSON object")
    return result


def _validate_schema(document: dict[str, Any], filename: str, label: str) -> None:
    resource = files("metis.contracts").joinpath("schemes", filename)
    schema = json.loads(resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    error = next(Draft202012Validator(schema).iter_errors(document), None)
    if error is not None:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        raise DeviceDefinitionError(f"{label}/{location}: {error.message}")


def _values(value: Any, spec: dict[str, Any], name: str):
    """一覧・範囲を検証し、直積用の iterable を返す。"""
    if isinstance(value, dict):
        first, last = value["first"], value["last"]
        if last < first:
            raise DeviceDefinitionError(f"{name}: first must be <= last")
        candidates = range(first, last + 1)
        endpoints = (first, last)
    else:
        candidates = value if isinstance(value, list) else [value]
        endpoints = candidates

    for item in endpoints:
        if spec["type"] == "integer":
            if type(item) is not int:
                raise DeviceDefinitionError(f"{name}: expected integer")
            if item < spec.get("minimum", 0) or item > spec.get("maximum", item):
                raise DeviceDefinitionError(f"{name}: outside declared bounds")
        elif not isinstance(item, str) or IDENTIFIER.fullmatch(item) is None:
            raise DeviceDefinitionError(f"{name}: expected snake_case identifier")
    return candidates


def validate_definitions(
    definition: dict[str, Any], instance: dict[str, Any],
) -> None:
    """形式・版・変数・オプションの整合性を確認する。"""
    _validate_schema(definition, "device_type_difinition.schema.json", "definition")
    _validate_schema(instance, "device_instance_definition.schema.json", "instance")
    if IDENTIFIER.fullmatch(definition["device_type"]) is None:
        raise DeviceDefinitionError("Invalid device_type")
    for name in ("device_type", "definition_version"):
        if definition[name] != instance[name]:
            raise DeviceDefinitionError(f"{name}: definition and instance differ")

    variables = definition["variables"]
    options = definition.get("options", {})
    for name, spec in variables.items():
        if IDENTIFIER.fullmatch(name) is None:
            raise DeviceDefinitionError(f"Invalid variable name: {name!r}")
        if spec["type"] == "integer" and spec.get("minimum", 0) > spec.get("maximum", float("inf")):
            raise DeviceDefinitionError(f"{name}: minimum exceeds maximum")
    for name in options:
        if IDENTIFIER.fullmatch(name) is None:
            raise DeviceDefinitionError(f"Invalid option name: {name!r}")
    unknown = instance.get("options", {}).keys() - options.keys()
    if unknown:
        raise DeviceDefinitionError(f"Unknown options: {sorted(unknown)}")

    for field in definition["fields"]:
        # fullmatch also rejects a trailing newline (JSON Schema's $ can allow it).
        template = field["field_template"]
        concrete = VARIABLE.sub("placeholder", template)
        if PATH.fullmatch(concrete) is None:
            raise DeviceDefinitionError(f"Invalid template: {template!r}")
        for attr in ("quantity", "role"):
            if IDENTIFIER.fullmatch(field[attr]) is None:
                raise DeviceDefinitionError(f"Invalid {attr}: {field[attr]!r}")
        unknown = set(VARIABLE.findall(template)) - variables.keys()
        if unknown:
            raise DeviceDefinitionError(f"{template}: unknown variables {sorted(unknown)}")
        if "enabled_if" in field and field["enabled_if"] not in options:
            raise DeviceDefinitionError(f"{template}: unknown enabled_if")

    enabled = {name: spec["default"] for name, spec in options.items()}
    enabled.update(instance.get("options", {}))
    for binding in instance["field_template_bindings"]:
        unknown = binding.keys() - variables.keys()
        if unknown:
            raise DeviceDefinitionError(f"Unknown variables: {sorted(unknown)}")
        for name, value in binding.items():
            _values(value, variables[name], name)
        for field in definition["fields"]:
            if "enabled_if" in field and not enabled[field["enabled_if"]]:
                continue
            missing = set(VARIABLE.findall(field["field_template"])) - binding.keys()
            if missing:
                raise DeviceDefinitionError(f"{field['field_template']}: missing variables {sorted(missing)}")


def expand_fields(
    definition: dict[str, Any], instance: dict[str, Any],
    *, max_fields: int = 100_000,
) -> list[ExpandedField]:
    """検証後、各項目が使う変数だけを直積展開する。

同じ項目内の重複は統合し、異なる項目間のパス衝突は拒否する。
max_fields は展開結果の上限。DB 登録は行わない。
"""
    if max_fields <= 0:
        raise ValueError("max_fields must be positive")
    validate_definitions(definition, instance)
    options = {key: value["default"] for key, value in definition.get("options", {}).items()}
    options.update(instance.get("options", {}))
    result: dict[str, ExpandedField] = {}
    for field in definition["fields"]:
        if "enabled_if" in field and not options[field["enabled_if"]]:
            continue
        names = sorted(set(VARIABLE.findall(field["field_template"])))
        local: dict[str, ExpandedField] = {}
        for binding in instance["field_template_bindings"]:
            candidates = [
                _values(binding[name], definition["variables"][name], name)
                for name in names
            ]
            # Bound before itertools.product materializes its input pools.
            size = 1
            for values in candidates:
                length = values.stop - values.start if isinstance(values, range) else len(values)
                if length > max_fields // size:
                    raise DeviceDefinitionError("Expansion exceeds max_fields")
                size *= length
            for combination in product(*candidates):
                path = field["field_template"].format(**dict(zip(names, combination)))
                if PATH.fullmatch(path) is None:
                    raise DeviceDefinitionError(f"Invalid expanded path: {path!r}")
                if path in result:
                    raise DeviceDefinitionError(f"Conflicting field definitions: {path}")
                local[path] = ExpandedField(
                    field_path=path, quantity=field["quantity"], role=field["role"],
                    unit=field.get("unit"), description=field.get("description"),
                )
                if len(result) + len(local) > max_fields:
                    raise DeviceDefinitionError("Expansion exceeds max_fields")
        result.update(local)
    return list(result.values())


def load_fields(
    definition_path: str | Path, instance_path: str | Path,
    *, max_fields: int = 100_000,
) -> list[ExpandedField]:
    """二つの JSON ファイルを読み込み、検証済みの系列一覧を返す。"""
    return expand_fields(
        load_json(definition_path), load_json(instance_path), max_fields=max_fields,
    )
