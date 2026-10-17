# 汎用の監視系列登録

`backend` から実行します。

```bash
python -m pip install sqlalchemy jsonschema 'psycopg[binary]'
python -m metis.central.seed \
  --type-definition path/to/device_definition.json \
  --instance path/to/device_instance.json \
  --agent-id 1 \
  --dry-run
```

`DATABASE_URL` にマイグレーション済みの PostgreSQL 接続 URL を設定してください。
`--dry-run` を外すと登録します。JSON の形式は既存スキーマに従います。
型式定義・個体設定を JSON オブジェクトとして渡す Python API も利用できます。

```python
from metis.central.seed import seed
result = seed(definition, instance, db_url, agent_id=1)
```

- Agent・Device・quantity・role は事前登録が必要です。自動作成しません。
- Device の device_type が入力と一致することを確認します。
- 一個体分を一つのトランザクションで保存します。
- 同一キー・同一属性は再利用し、物理量・役割・単位の相違はエラーにします。
- 入力から消えた既存系列は削除しません。
- 実験上の対象・期間付き対応・監視履歴は登録しません。
- description と definition_version は現在の系列テーブルに保存しません。
- dry-run の結果は確認時点の予定であり、その後の登録を予約しません。
- 既存スキーマのディレクトリ名 schemes、ファイル名 difinition は維持しています。

テストは `PYTHONPATH=backend python -m pytest -q backend/tests`（リポジトリ直下）。
系列登録・再実行・ロールバックのテストには SQLite を使用し、PostgreSQL の
ON CONFLICT 文は PostgreSQL dialect でコンパイルして確認します。
実 PostgreSQL / TimescaleDB に対する結合テストは別途必要です。
