# Description
[Poke-Controller](https://github.com/KawaSwitch/Poke-Controller)をベースにPySide6で主要機能を再構築しています


![image](https://user-images.githubusercontent.com/59233665/204475385-c8cacfe3-5b35-49ed-b77b-cde447c9be91.png)


# Requirements

- python 3.10

# Usage
- pip install requirements.txt
- mainwindow.pyを起動


# Feature

Poke-Controllerからの変更点は下記
- GUI Controller を据え置き型で設置(消すことも再表示することも可能)
- PCに繋いだコントローラーでSwitchを操作できるように
  - キー割当は一度`mainwindow.py`を実行後に`game_pad_connect.py`を実行して行う。
- `Ctrl + マウス左Click`でクリック箇所の座標と色情報表示
- キーボード操作は不可能
- 一部基本関数を変更
  - そもそも実装できていない関数が多いです。

    以下は実装済み(一部関数名に変更あり)
    - `press`　ボタンなど押下
    - `wait`　一定時間待機
    - `is_contain_template`　画像認識

  - `print`はLogに出ません。代わりに`debug`などを使用してください。
  - 画像認識周りの処理の実装が適当なので、正しく動かない可能性があります。

## 構造
---

ベースとなる部分で、GUIのボタンなどから関数の起動(シグナルの発火)やスレッドの呼び出しを行う。

### キャプチャ画像表示

- メインウィンドウでthreadをたてる。各workerを各thread上にmoveしてマルチスレッドとする
  - capture用
  - スクリプト実行用
  - コントローラー接続用
    - スティックの状態のみマルチプロセスでworkerが受け取る
- ゲームパッドのキー割当はlibsにあるgame_pad_connect.pyを実行しておこなう
- キーボード操作はそのうち実装したい


## 🧩 Visual Macro Editor（ビジュアルマクロエディタ）

GUI上でブロックを組み合わせてマクロを作成できるビジュアルプログラミング機能です。Pythonコードを一切書かずに、ゲームコントローラー操作の自動化マクロを構築・実行できます。

### 主な特徴

- **Blockly ベースのビジュアルエディタ** — ブラウザ技術（QWebEngineView）を活用したドラッグ＆ドロップ式エディタ
- **51種類のブロック** — ボタン操作・スティック制御・条件分岐・ループ・変数・関数・リスト・画像認識など
- **テンプレートマッチ対応** — キャプチャ画像からの画像認識によるif分岐・待機・ループ制御
- **ROI（領域指定）選択** — テンプレートマッチの対象範囲をマウス操作で直感的に設定
- **リアルタイムプレビュー** — 画像ブロック選択時にテンプレート画像がサイドパネルに表示
- **保存 / 読み込み** — JSON形式でマクロの保存・復元。コンボボックスからの直接実行にも対応
- **実行中ハイライト** — 実行中のブロックがリアルタイムでハイライト表示

### ROI 選択機能

画像認識ブロックの検索対象範囲（Region of Interest）を直感的に指定できます。

| 機能 | 説明 |
|------|------|
| 📷 キャプチャ取得 | 現在のゲーム画面をROI選択の背景として取得（常時取得可能） |
| 📁 画像ファイル読み込み | ローカル画像ファイルをROI背景として使用 |
| 🖱️ マウスドラッグ選択 | ドラッグで矩形範囲を新規作成, 位置移動 |
| リサイズ | 四隅・四辺の8つのハンドルで選択範囲をリサイズ |
| ⌨️ 座標手動入力 | X1/Y1/X2/Y2 を数値で直接指定 |

### ブロック一覧

<details>
<summary>全51ブロック（クリックで展開）</summary>

#### 📂 操作（13ブロック）
`ボタン押し` `同時押し` `連打` `長押し開始` `長押し解除` `スティック入力` `スティック保持` `スティック解除` `待機` `ログ出力` `値付きログ` `コメント` `マクロ終了`

#### 📂 制御（10ブロック）
`if/else分岐` `N回繰り返し` `無限ループ` `条件ループ` `for range` `リスト反復` `break` `continue` `画像あり間ループ` `画像なし間ループ`

#### 📂 条件・画像（3ブロック）
`画像判定` `画像出現待ち` `画像消滅待ち`

#### 📂 変数（3ブロック）
`変数セット` `変数取得` `変数加算`

#### 📂 論理（5ブロック）
`比較(=,≠,<,>,≤,≥)` `AND/OR` `NOT` `真偽リテラル` `三項演算子`

#### 📂 数値（7ブロック）
`数値リテラル` `四則演算+剰余` `整数乱数` `小数乱数` `abs/round/floor/ceil` `min/max` `数値変換`

#### 📂 テキスト（6ブロック）
`文字列リテラル` `結合` `文字列変換` `文字数` `含む判定` `切り出し`

#### 📂 リスト（6ブロック）
`空リスト` `初期値リスト` `要素数` `取得` `代入` `追加`

#### 📂 関数（5ブロック）
`関数定義` `関数呼び出し(文)` `関数呼び出し(値)` `return` `引数参照`

</details>

### ファイル構成

```
ui/visual_macro/              # フロントエンド
├── index.html                # エディタ HTML
├── app.js                    # UI制御ロジック
├── blocks.js                 # Blockly ブロック定義 + シリアライズ
├── styles.css                # スタイル
└── toolbox.json              # ツールボックス定義

libs/visual_macro/            # バックエンド
├── models.py                 # データモデル（dataclass群）
├── schema.py                 # JSON パース＆バリデーション
├── runtime.py                # 実行エンジン（CommandBase継承）
├── bridge.py                 # Qt ↔ Web ブリッジ
├── editor_widget.py          # QWebEngineView ホスト
├── template_service.py       # テンプレート画像管理
├── repository.py             # ドキュメント保存/読込
├── factory.py                # コマンドクラス動的生成
├── frame_store.py            # フレーム共有ストア
└── errors.py                 # 例外クラス
```



## License

This repository's source code is licensed under the **MIT License** unless
otherwise explicitly stated. See [LICENSE.md](./LICENSE.md) for details.

### Third-party dependencies

This project uses **PySide6 / Qt for Python** and other third-party components.
Those dependencies are provided under their own licenses and are **not**
relicensed by this repository.

In particular, PySide6 / Qt for Python is available under open source
licenses (including LGPLv3 / GPLv2 / GPLv3) or under a commercial license.
If you redistribute binaries, bundled applications, or installers that include
PySide6 / Qt, you are responsible for complying with the applicable Qt / PySide6
license terms.

For more information, see:
- [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)
- [COPYING.LESSER.md](./COPYING.LESSER.md)

### Notes

- The code written specifically for this project is intended to remain under MIT.
- Third-party libraries keep their original licenses.
- If you modify or redistribute Qt / PySide6 related components, additional
  obligations may apply depending on the license mode you use.

### 免責事項
このプログラム、および同梱のファイルの使用、または使用不具合等により生じたいかなる損害に関しまして、作者は一切責任を負いません。

