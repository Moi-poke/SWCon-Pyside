# Todo

## メインウィンドウ
---

ベースとなる部分で、GUIのボタンなどから関数の起動(シグナルの発火)やスレッドの呼び出しを行う。

### キャプチャ画像表示は以下のような構造

- メインウィンドウでthreadをたてる。各workerを各thread上にmoveしてマルチスレッドとする
  - capture用
  - スクリプト実行用
  - コントローラー接続用
    - スティックの状態のみマルチプロセスでworkerが受け取る
  - (キーボード操作用？)
- ゲームパッドのキー割当はlibsにあるgame_pad_connect.pyを実行しておこなう
- 


## License
---
![License logo](https://www.gnu.org/graphics/lgplv3-147x51.png)

This repository is mainly licensed under the [GNU LGPL v3](http://github.com/IQAndreas/markdown-licenses/blob/master/gnu-lgpl-v3.0.md#gnu-lesser-general-public-license).