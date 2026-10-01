---
created: "2026-09-28T18:20:01+09:00"
lastmod: "2026-10-01T00:26:28+09:00"
---

# 通信規格

metis における通信の単位をメッセージとよび、メッセージはヘッダーとペイロードに分かれる。
もともとのペイロードは送信元から配送先まで一貫して変化のないものであるが、ヘッダーは配送中に変化しうるものである。

##　警報についての考え方

[[alarm-delivery]]

# 調べたこと

## redis stream

redis pub/sub websocket どっち、という検索ワードで引っかかってきたサイトに、redis pub/sub は負荷が増えることが予想され、
redis stream を使うことにしたという記事があったので、メモ。

https://zenn.dev/happy_elements/articles/hekk_ac_20201224
