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


## License
---
![License logo](https://www.gnu.org/graphics/lgplv3-147x51.png)

This repository is mainly licensed under the [GNU LGPL v3](http://github.com/IQAndreas/markdown-licenses/blob/master/gnu-lgpl-v3.0.md#gnu-lesser-general-public-license).

### 免責事項
このプログラム、および同梱のファイルの使用、または使用不具合等により生じたいかなる損害に関しまして、作者は一切責任を負いません。

#### お布施
https://ofuse.me/moi0326
