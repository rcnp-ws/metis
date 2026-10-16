# Device 定義の検証・展開

`backend` で依存パッケージを導入する。

```bash
python -m pip install jsonschema
```

利用例:

```python
from metis.contracts.device_definition import load_fields

fields = load_fields("device_definition.json", "device_instance.json")
for field in fields:
    print(field.field_path, field.quantity, field.role, field.unit)
```

既存の `contracts/schemes/device_type_difinition.schema.json` と
`device_instance_definition.schema.json` を利用する。スキーマの名前・内容は変更しない。
インストール可能なパッケージにする場合、これらの JSON も package data に含める。

`validate_definitions(definition, instance)` は検証のみ、
`expand_fields(definition, instance)` は検証と展開を行う。
整数範囲は first/last の両端を含み、同じ指定内は直積で展開する。
項目が使用する変数だけを展開し、同じ項目内の重複はまとめる。
異なる項目からのパス衝突は拒否する。
省略されたオプションには型式定義の default を使用する。
未指定単位は None として返す。

DB 内の語彙・個体・Agent の照合、登録、通信値の抽出は行わない。
返される description は表示用の情報であり、現在の monitor_series には保存列がない。
展開上限の既定値は100,000系列で、max_fields 引数で変更できる。

テスト:

```bash
python -m pip install pytest
python -m pytest ../backend/tests/test_device_definition.py
```
