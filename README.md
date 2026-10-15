# Rings Watch Face

Wear OS 用のウォッチフェイスです。外側から「秒・分・時・曜日・週の予定」の5本の同心円リングで時間を表示します。

Watch Face Format (WFF) で作り、Google Play で公開する予定です。

## 構成

- `app/src/main/res/raw/watchface.xml` … ウォッチフェイス本体(WFF v2、Wear OS 5 以降)
- `tools/generate_watchface.py` … 上の XML と画像を生成するスクリプト。リングの寸法・色・祝日はここで変更します
- 祝日は 2026〜2030 年の日本の祝日を書き込んでいます。`HOLIDAY_YEARS` を延ばして再生成してください

```sh
pip install pillow
python3 tools/generate_watchface.py
./gradlew assembleDebug
```

## いまの版でできること

- 秒・分・時・曜日の4本のリングを白い三角で指す(時は12時間で1周)
- 曜日リングの日曜・祝日をピンク、土曜を青で表示。祝日は7日前から色が付きます
- 中央に日付、天気(気温と天気名)、次の予定(カレンダーのコンプリケーション)
- 常時表示では秒の三角を消し、リングを暗くします

予定の時間帯・タイマー・週の予定リングの色分けは、連携アプリを作る次の段階で追加します。
