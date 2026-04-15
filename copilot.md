あなたは、PySide6 / Qt のスレッド設計・OpenCV・シリアル通信・プラグインロード構成に強い、上級 Python デスクトップアプリ開発エンジニアです。

これから渡す既存コードベースに対して、全面的なリファクタリングを行ってください。
目的は、単なるバグ修正ではなく、Qt の thread-affinity / worker-object パターンに整合した、安全で保守しやすいアーキテクチャへ移行することです。

# 最重要方針

- 現行機能は極力維持する
- ただし、スレッド境界・責務分離・停止処理・画像取得 API・シリアル出力経路は、互換性より健全性を優先して設計し直してよい
- 「たまたま動く実装」ではなく、「Qt 的に正しい実装」に寄せる
- cross-thread では DirectConnection を原則禁止する
- worker object への通常メソッド直呼びを禁止する
- terminate() を禁止する
- signal を同期関数の戻り値のように使う設計を禁止する

---

# 対象アプリの概要

このアプリは、以下を持つ PySide6 GUI アプリです。

- GUI（MainWindow）
- OpenCV による Web カメラ映像取得
- テンプレートマッチング等の画像認識
- シリアル通信によるマイコン / コントローラ制御
- ゲームパッド入力
- Python Command / MCU Command のロードと実行
- LINE 通知
- スクリーンショット保存
- プラグイン的な command reload

既存コードには以下の問題があります。

- moveToThread() はしているが、別スレッド QObject に通常メソッド直呼びしている
- cross-thread で DirectConnection を多用している
- command が get_image.emit(True) の直後に __src を読む等、signal を同期 API のように扱っている
- serial write 経路が分散していて排他されていない
- terminate() に依存した停止処理がある
- CommandBase に責務が集まりすぎている
- Utility / CommandLoader の import/reload が壊れやすい
- signal の型定義が不自然（np.ndarray / type(Button.A) / type(logging.DEBUG) など）
- capture / sender / command base / loader に未使用 import や型注釈の不整合がある

---

# 最終的に目指すアーキテクチャ

## スレッド構成

- MainWindow / UI: main thread
- CaptureWorker: capture thread
- SerialWorker: serial thread
- GamepadWorker: gamepad thread
- LineNotifyWorker: line thread
- CommandRuntime / CommandWorker: command thread

## 基本ルール

- QObject worker は moveToThread() して使用する
- cross-thread 通信は queued signal/slot を使う
- 他スレッド所属 QObject の内部状態に直接アクセスしない
- worker に対する操作は slot 経由で行う
- CommandBase は MainWindow を知らない
- CommandBase は Sender / KeyPress / ser を知らない
- Serial / camera / line notify はそれぞれ専用 worker に所有させる

---

# 実装対象ファイル

最低限、以下のファイル群を改修対象にしてください。

- MainWindow を含むメイン GUI ファイル
- libs/capture.py
- libs/sender.py
- libs/CommandBase.py
- libs/CommandLoader.py
- libs/Utility.py
- 必要であれば新規ファイル:
  - libs/serial_worker.py
  - libs/line_notify_worker.py
  - libs/command_runtime.py
  - libs/keyboard_helper.py
  - その他適切な分離先

既存ファイルを無理に温存する必要はありません。
最適な状態になるように構造変更して構いません。

---

# 具体的な改修要件

## 1. DirectConnection の全面見直し

以下のような cross-thread DirectConnection は禁止し、queued connection へ変更するか、中継用 worker / signal を挟んで責務分離してください。

危険な代表例:

- Gamepad axis -> MainWindow.stick_control (Direct)
- command worker -> MainWindow.callback_keypress (Direct)
- command worker -> MainWindow.callback_run_macro (Direct)
- command worker -> MainWindow.callback_line_txt / callback_line_img (Direct)
- command worker -> MainWindow.callback_show_recognize_rect (Direct)
- capture worker -> command worker callback_receive_img (Direct)
- command worker -> MainWindow.callback_return_img (Direct)

### 修正方針
- ゲームパッド入力の UI 表示は MainWindow に返してよいが、実入力処理は SerialWorker に queued で渡す
- serial_input / send_serial は SerialWorker に queued で集約する
- recognize_rect は CaptureWorker.add_rect に queued で渡す
- line_txt / line_img は LineNotifyWorker に queued で渡す
- カメラ画像は CaptureWorker から frame_ready で定期配信し、command 側が latest frame をキャッシュする
- get_image.emit(True) のような request/response は廃止する

---

## 2. SerialWorker の導入と serial 経路の一元化

Sender / KeyPress / serial write は SerialWorker に閉じ込めてください。

### 必須条件
- Sender を MainWindow が直接保持しない
- KeyPress を MainWindow が直接保持しない
- ser.writeRow() を MainWindow / CommandBase / Gamepad から直接呼ばない
- GUI、Gamepad、Command、MCU command のすべての serial 要求は SerialWorker に signal で渡す
- serial write は 1 スレッドで直列処理する

### SerialWorker に持たせるべき責務
- open_port
- close_port
- write_row
- on_keypress(buttons, duration, wait, input_type)
- on_axis_moved(...)
- on_gui_stick_input(...)
- log / serial_state_changed / serial_error signal

### sender.py 改修要件
- Signal(str, int) に型修正
- logging handler を弱くする（ライブラリ側で StreamHandler を勝手に足さない）
- openSerial() のログファイル open 順序を見直す
- closeSerial() で None 安全にする
- SerialException を握り潰さず上位へ通知する
- isOpen() を現行 pyserial API に寄せる
- show_input() は必要なら helper 分離してよい

---

## 3. CaptureWorker の再設計

CaptureWorker は camera owner として整理してください。

### 必須 signal
- image_ready(QImage)
- frame_ready(object)
- log(str, int)

### 必須 slot
- start_capture()
- stop_capture()
- reopen_camera(int)
- set_fps(int)
- save_capture(...)
- add_rect(tuple, tuple, object, int)

### 必須修正
- worker 外から capture_worker.open_camera() / set_fps() / saveCapture() / callback_return_img() を直接呼ばない
- QPainter をインスタンス属性にせず、ローカル生成にする
- rect_list を走査しながら remove しない
- latest_frame の所有権を明確化する
- send_img/request_image 方式はやめ、frame_ready の定期配信 + latest frame キャッシュ方式にする
- Signal(QImage, np.ndarray) のような型定義は object に寄せる
- 未使用 import（multiprocessing, shared_memory, Process など）は削除する
- numpy は np に統一する
- camera 型注釈が cv2.VideoWriter になっているなら修正する
- playing がクラス変数になっているならインスタンス変数へ移す

---

## 4. CommandBase の再設計

CommandBase は「コマンドの手順定義」に寄せてください。
現在の責務過多を是正してください。

### CommandBase に残してよい責務
- do() / press() / hold() / release_all() / write_serial()
- latest frame の読み出し
- テンプレートマッチング等の高レベル認識 API
- line notify の高レベル API
- screenshot の高レベル API
- stop flag を見た cooperative stop

### CommandBase から排除 / 縮退すべきもの
- get_image.emit(True) 前提の同期風 API
- MainWindow 依存
- Sender / KeyPress / ser への直接依存
- signal を同期関数の戻り値のように使う設計
- 可能であれば keyboard helper / pykakasi 依存の直持ち

### 必須修正
- get_image signal に依存する readFrame() を廃止または再設計し、latest_frame キャッシュを返すだけにする
- callback_receive_img は @Slot(object) にする
- line_notify() で get_image.emit(True) の直後に __src を使う構造をやめる
- Signal(type(Button.A), ...) のような型を object に置き換える
- Signal(np.ndarray) も object に置き換える
- print_strings は Signal(str, int) にする
- wait() の busy wait を廃止する
- cooperative wait（小刻み sleep + stop flag check）か、理想的には状態機械 + QTimer に寄せる
- cv2.imread(self.TEMPLATE_PATH) + template_path のバグを修正する
- ThreadPoolExecutor の使用は停止制御と整合しないなら見直す
- random, QPainter, QTimer など未使用 import を整理する
- numpy / np の混在を解消する

### 理想
- CommandBase と別に CommandRuntime / CommandContext を導入し、
  - latest frame 管理
  - worker 接続管理
  - stop/start 管理
  - CommandBase への文脈注入
  を分離する

---

## 5. Gamepad 入力処理の見直し

### 必須条件
- ゲームパッド監視は専用 worker thread に置く
- ボタン押下/解放・axis は signal 化する
- UI 用更新と serial 入力用処理を分ける
- MainWindow.stick_control のような cross-thread 直接呼び出しをやめる

### 具体方針
- axis_moved -> MainWindow.stickMoveEvent（UI 表示用）
- axis_moved -> SerialWorker.on_axis_moved（実入力用）
- button_pressed/released -> MainWindow.update_button_ui（必要なら）
- button_pressed/released -> SerialWorker.on_keypress

---

## 6. LineNotifyWorker の導入

LINE 通知は MainWindow 経由で直接呼ばず、LineNotifyWorker を別スレッドに置いてください。

### 必須 slot
- send_text(text, token_key)
- send_image(text, token_key, img)

### 必須条件
- command worker から MainWindow.callback_line_txt / callback_line_img に DirectConnection しない
- img は Signal(str, str, object) で受ける

---

## 7. MainWindow の責務縮退

MainWindow は UI controller として再設計してください。

### MainWindow が持つべき責務
- UI の状態管理
- Worker の生成・接続・終了
- command class 選択
- 設定保存/復元
- ログ表示
- UI から worker への signal 発行

### MainWindow がやってはいけないこと
- capture_worker の内部状態を直接触る
- serial / keyPress / sender を直接触る
- command worker を直接 stop()/run() する
- rect_list に直接 append する
- worker の内部リストやフレームに直接触る

### start_command() 改修要件
- MainWindow が command と他 worker の細かい wiring を全部持たない
- 必要なら CommandRuntime を導入する
- stop は stop_request signal 経由に統一する
- worker.run を started に接続する場合でも、その worker が queued slot を処理できる設計にすること
- 長時間ブロックして event loop を塞ぐ run() は避ける

### stop_command() / closeEvent() 改修要件
- worker.stop() の直呼びをやめる
- terminate() を全廃する
- stop_request -> worker stop flag -> quit() -> wait() の順で止める
- shutdown 順序は以下を守ること
  1. UI から新規操作を止める
  2. command stop
  3. gamepad stop
  4. capture stop
  5. line worker stop
  6. serial close
  7. thread quit/wait
  8. 設定保存

---

## 8. Utility.py / CommandLoader.py の安定化

### Utility.py 改修要件
- ospath() は os.path.normpath() 相当にする
- browseFileNames() は sorted() する
- getModuleNames() は __init__.py を除外する
- 絶対パス前提で壊れない module 名生成にする
- getClassesInModule() は cls.__module__ == module.__name__ のものだけ返す
- import_all_modules() で mod_names が str の場合は list 化する
- error 情報は traceback object ではなく文字列化して保持する
- 型注釈を実態に合わせる

### CommandLoader.py 改修要件
- load()/reload() の戻り値型注釈を修正する
- error_ls / error_dict を統一する
- error_while_process のような未使用変数は削除する
- stderr print は logger に置き換える
- set() ベースの差分比較結果は sorted() で安定化する
- get_command_classes() は base_type 自身を除外する
- 必要なら抽象 class も除外する
- reload 後は stale class / stale instance を使い続けない方針を明確にする

---

## 9. logging / 例外処理ルール

### 必須ルール
- except: pass を禁止
- 少なくとも logger または signal で可視化する
- ライブラリ側で StreamHandler を勝手に足さない
- NullHandler を基本にし、handler 設定はアプリ側に寄せる
- logging.DEBUG を型として使わず int を使う
- traceback object をそのまま保持しない
- print() は原則 logger へ置換する（デバッグ一時用途を除く）

---

## 10. 型 / import / 可読性整理

全体に対して以下を行ってください。

- 未使用 import 削除
- numpy / np の混在解消
- 明らかに誤った型注釈修正
- Signal / Slot の型を実態に合わせる
- 明らかなバグ修正
  - comboBox_MCU の findText 対象ミス
  - assign_window_size_to_setting の内容ミス
  - is not [] / is {} 判定
  - staticmethod + self の矛盾
  - cv2.imread(self.TEMPLATE_PATH) + template_path のバグ
  - 等価判定に is を使っている箇所
- 反復コピペ実装（press_/release_ 群など）は、可能な範囲で整理してよい

---

# 受け入れ条件（必須）

実装後、以下を満たしてください。

## スレッド健全性
- cross-thread DirectConnection が実質ゼロ（同一スレッド UI ローカルイベントを除く）
- 他スレッド QObject への通常メソッド直呼びがゼロ
- terminate() がゼロ

## 画像取得
- command 実行中に latest frame を安定して読める
- screenshot / rect 描画 / UI 表示が同時でも壊れない

## シリアル
- GUI / Gamepad / Command / MCU command が同時に入力しても COM write が壊れない
- open / close / reconnect が安全

## reload
- reload 後に stale class / stale instance を使い続けない
- 削除 command は一覧から消える
- reload 中に実行中 command がある場合、安全に止めてから再ロードする

## shutdown
- カメラ / シリアル / 各 thread が clean に終了する
- 設定が保存される

---

# 出力形式（厳守）

以下の順番で出力してください。

## 1. 変更方針の要約
- 何をどう直すかを短く整理

## 2. ファイル別修正方針
- MainWindow
- capture.py
- sender.py
- CommandBase.py
- Utility.py
- CommandLoader.py
- 新規追加ファイル（ある場合）

## 3. 修正後コード
- 変更したファイルごとに、完全なコードを出す
- 省略記号（...）は使わない
- 実際に保存できる形で出す
- 新規ファイルも全文出す

## 4. 変更点一覧
- Before / After を箇条書きで整理

## 5. 懸念点
- もし未確認の外部依存（GamepadController, KeyPress, LineNotify, CaptureWorker 以外の libs 等）があれば、その影響範囲を最後に書く

---

# 重要な制約

- 既存の機能名や public API は、必要以上に壊さない
- ただし危険な設計は互換性より修正を優先してよい
- 動く最小差分ではなく、長期保守に耐える構造を優先する
- 実装は Python / PySide6 として一貫し、Qt の設計に整合すること
- 実装コードは省略せず、すべて具体的に書くこと
- 疑わしい箇所は TODO コメントを明示的に残すこと
- 外部クラスの中身が不明でも、仮定を明記して最善の構造を提示すること

---

# 補足指示

- `QMetaObject.invokeMethod(..., Qt.QueuedConnection)` は、signal を新設するより適切な場合にのみ使用してよい
- ただし常用せず、基本は Signal/Slot で整理すること
- `CommandBase.wait()` は最初は cooperative sleep 実装でもよいが、将来的な QTimer 化がしやすいように構造を整えること
- `Sender` を pure Python class にして SerialWorker でラップする構成も許可する
- `CommandRuntime` / `CommandContext` の新設を推奨する
- `Keyboard helper` は CommandBase から分離してよい

---

# 期待する最終状態の一言要約

「UI / camera / serial / gamepad / line / command がそれぞれ owner thread を持ち、cross-thread は queued signal/slot のみでつながる、安全な PySide6 アーキテクチャ」

この要件に従って、最適な実装を提示してください。