import logging
import math
import os
import queue
import sys
import time
from logging import getLogger
from typing import Optional

import cv2
import PySide6
import shiboken6
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QSize, Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow

from libs import sender
from libs.capture import CaptureWorker
from libs.CommandBase import CommandBase
from libs.CommandLoader import CommandLoader
from libs.game_pad_connect import GamepadController
from libs.keys import Button, Direction, Hat, KeyPress, Stick
from libs.mcu_command_base import McuCommand
from libs.settings import Setting
from libs.Utility import ospath
from ui.main_ui import Ui_MainWindow
from ui.QtextLogger import QPlainTextEditLogger

VERSION = "0.2.0 (beta)"
Author = "Moi"

# Todo
# GUIの起動
class MainWindow(QMainWindow, Ui_MainWindow):
    stop_request = Signal(bool)

    def __init__(
        self,
        parent: Optional[PySide6.QtWidgets.QWidget] = None,
        flags: PySide6.QtCore.Qt.WindowFlags = QtCore.Qt.Window,
    ) -> None:
        """_summary_

        Args:
            parent (Optional[PySide6.QtWidgets.QWidget], optional): _description_. Defaults to None.
            flags (PySide6.QtCore.Qt.WindowFlags, optional): _description_. Defaults to QtCore.Qt.Window.
        """
        super().__init__(parent, flags)
        self.logger = getLogger(__name__)
        self.thread_1 = None
        self.capture_worker = None
        self.thread_2 = None
        self.worker = None
        self.GamepadController_worker = None
        self.GamepadController_thread = QThread()
        self.thread_do = None
        self.img = None
        self.command_mode = None
        self.is_show_serial = False
        self.keyPress = None
        self.keymap = None
        self.setting = Setting()

        self.setupUi(self)
        self.setWindowTitle(f"SWController {VERSION}")

        self.pushButtonReloadCamera.pressed.connect(lambda: self.reconnect_camera(self.lineEditCameraID.text()))
        self.pushButtonReloadCamera.pressed.connect(self.reload_camera)

        self.plainTextEdit = QPlainTextEditLogger(self.dockWidgetContents)
        self.plainTextEdit.widget.setObjectName("plainTextEdit")
        self.plainTextEdit.widget.setEnabled(True)
        self.plainTextEdit.widget.setMinimumSize(QSize(500, 195))
        self.plainTextEdit.widget.setUndoRedoEnabled(True)
        self.plainTextEdit.widget.setCursorWidth(-2)
        self.plainTextEdit.widget.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.gridLayout.addWidget(self.plainTextEdit.widget, 0, 0, 1, 1)
        self.setFocus()

        self.set_settings()
        py_cmd = self.setting.setting["command"]["py_command"]
        mcu_cmd = self.setting.setting["command"]["mcu_command"]

        # self.gamepad_setting = SettingWindow(parent=self, _setting=self.setting)
        # self.gamepad_setting.show()

        self.q: queue.Queue = queue.Queue()
        self.setup_functions_connect()
        self.connect_capture()

        # You can format what is printed to text box
        self.plainTextEdit.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        # You can control the logging level
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.plainTextEdit)

        self.pushButtonClearLog.pressed.connect(self.plainTextEdit.widget.clear)

        self.ser = sender.Sender(self.is_show_serial)
        self.activate_serial()
        self.activate_keyboard()
        self.connect_gamepad()
        self.load_commands()

        try:
            self.comboBox_MCU.setCurrentIndex(self.comboBoxPython.findText(mcu_cmd))
            self.comboBoxPython.setCurrentIndex(self.comboBoxPython.findText(py_cmd))
        except Exception as e:
            self.logger.debug("No Script?")

        # スレッドの開始
        self.thread_1.start()
        self.GamepadController_thread.start()

        if self.setting is not None:
            self.resize(
                self.setting.setting["main_window"]["option"]["window_size_width"],
                self.setting.setting["main_window"]["option"]["window_size_height"],
            )
        self.pushButton_debug.pressed.connect(self.test)

    def test(self):
        self.reconnect_gamepad()

    # <editor-fold desc="ゲームパッド関連">
    def connect_gamepad(self):
        # Controllerスレッドの作成
        try:
            self.GamepadController_worker = GamepadController()
            self.GamepadController_thread = QThread()
            self.GamepadController_worker.moveToThread(self.GamepadController_thread)
            self.GamepadController_thread.started.connect(self.GamepadController_worker.run)

            self.GamepadController_worker.set_keymap(self.keymap)

            self.GamepadController_worker.ZL_PRESSED.connect(self.press_zl)
            self.GamepadController_worker.L_PRESSED.connect(self.press_l)
            self.GamepadController_worker.LCLICK_PRESSED.connect(self.press_lclick)
            self.GamepadController_worker.MINUS_PRESSED.connect(self.press_minus)
            self.GamepadController_worker.TOP_PRESSED.connect(self.press_top)
            self.GamepadController_worker.BTM_PRESSED.connect(self.press_btm)
            self.GamepadController_worker.LEFT_PRESSED.connect(self.press_left)
            self.GamepadController_worker.RIGHT_PRESSED.connect(self.press_right)
            self.GamepadController_worker.CAPTURE_PRESSED.connect(self.press_capture)
            self.GamepadController_worker.ZR_PRESSED.connect(self.press_zr)
            self.GamepadController_worker.R_PRESSED.connect(self.press_r)
            self.GamepadController_worker.RCLICK_PRESSED.connect(self.press_rclick)
            self.GamepadController_worker.PLUS_PRESSED.connect(self.press_plus)
            self.GamepadController_worker.A_PRESSED.connect(self.press_a)
            self.GamepadController_worker.B_PRESSED.connect(self.press_b)
            self.GamepadController_worker.X_PRESSED.connect(self.press_x)
            self.GamepadController_worker.Y_PRESSED.connect(self.press_y)
            self.GamepadController_worker.HOME_PRESSED.connect(self.press_home)

            self.GamepadController_worker.ZL_RELEASED.connect(self.release_zl)
            self.GamepadController_worker.L_RELEASED.connect(self.release_l)
            self.GamepadController_worker.LCLICK_RELEASED.connect(self.release_lclick)
            self.GamepadController_worker.MINUS_RELEASED.connect(self.release_minus)
            self.GamepadController_worker.TOP_RELEASED.connect(self.release_top)
            self.GamepadController_worker.BTM_RELEASED.connect(self.release_btm)
            self.GamepadController_worker.LEFT_RELEASED.connect(self.release_left)
            self.GamepadController_worker.RIGHT_RELEASED.connect(self.release_right)
            self.GamepadController_worker.CAPTURE_RELEASED.connect(self.release_capture)
            self.GamepadController_worker.ZR_RELEASED.connect(self.release_zr)
            self.GamepadController_worker.R_RELEASED.connect(self.release_r)
            self.GamepadController_worker.RCLICK_RELEASED.connect(self.release_rclick)
            self.GamepadController_worker.PLUS_RELEASED.connect(self.release_plus)
            self.GamepadController_worker.A_RELEASED.connect(self.release_a)
            self.GamepadController_worker.B_RELEASED.connect(self.release_b)
            self.GamepadController_worker.X_RELEASED.connect(self.release_x)
            self.GamepadController_worker.Y_RELEASED.connect(self.release_y)
            self.GamepadController_worker.HOME_RELEASED.connect(self.release_home)

            self.GamepadController_worker.AXIS_MOVED.connect(self.stick_control, type=Qt.DirectConnection)

            self.gamepad_l_stick()
            self.gamepad_r_stick()

            self.GamepadController_thread.finished.connect(self.GamepadController_worker.deleteLater)
            self.GamepadController_thread.finished.connect(self.GamepadController_worker.stop)

            if self.GamepadController_worker.no_joystick:
                self.logger.debug("コントローラー接続なし")
        except Exception as e:
            self.logger.error(e)

    def reconnect_gamepad(self):
        self.GamepadController_worker.connect_joystick()
        pass

    def press_zl(self):
        self.keyPress.input(Button.ZL)

    def press_l(self):
        self.keyPress.input(Button.L)

    def press_lclick(self):
        self.keyPress.input(Button.LCLICK)

    def press_minus(self):
        self.keyPress.input(Button.MINUS)

    def press_top(self):
        self.keyPress.input(Hat.TOP)

    def press_btm(self):
        self.keyPress.input(Hat.BTM)

    def press_left(self):
        self.keyPress.input(Hat.LEFT)

    def press_right(self):
        self.keyPress.input(Hat.RIGHT)

    def press_capture(self):
        self.keyPress.input(Button.CAPTURE)

    def press_zr(self):
        self.keyPress.input(Button.ZR)

    def press_r(self):
        self.keyPress.input(Button.R)

    def press_rclick(self):
        self.keyPress.input(Button.RCLICK)

    def press_plus(self):
        self.keyPress.input(Button.PLUS)

    def press_a(self):
        self.keyPress.input(Button.A)

    def press_b(self):
        self.keyPress.input(Button.B)

    def press_x(self):
        self.keyPress.input(Button.X)

    def press_y(self):
        self.keyPress.input(Button.Y)

    def press_home(self):
        self.keyPress.input(Button.HOME)

    def release_zl(self):
        self.keyPress.inputEnd(Button.ZL)

    def release_l(self):
        self.keyPress.inputEnd(Button.L)

    def release_lclick(self):
        self.keyPress.inputEnd(Button.LCLICK)

    def release_minus(self):
        self.keyPress.inputEnd(Button.MINUS)

    def release_top(self):
        self.keyPress.inputEnd(Hat.TOP)

    def release_btm(self):
        self.keyPress.inputEnd(Hat.BTM)

    def release_left(self):
        self.keyPress.inputEnd(Hat.LEFT)

    def release_right(self):
        self.keyPress.inputEnd(Hat.RIGHT)

    def release_capture(self):
        self.keyPress.inputEnd(Button.CAPTURE)

    def release_zr(self):
        self.keyPress.inputEnd(Button.ZR)

    def release_r(self):
        self.keyPress.inputEnd(Button.R)

    def release_rclick(self):
        self.keyPress.inputEnd(Button.RCLICK)

    def release_plus(self):
        self.keyPress.inputEnd(Button.PLUS)

    def release_a(self):
        self.keyPress.inputEnd(Button.A)

    def release_b(self):
        self.keyPress.inputEnd(Button.B)

    def release_x(self):
        self.keyPress.inputEnd(Button.X)

    def release_y(self):
        self.keyPress.inputEnd(Button.Y)

    def release_home(self):
        self.keyPress.inputEnd(Button.HOME)

    def stick_control(self, left_horizontal, left_vertical, right_horizontal, right_vertical):
        dead_zone = 0.05  # これ以下の傾きは無視(デッドゾーン)
        left_angle = -math.degrees(math.atan2(left_vertical, left_horizontal))
        left_r = math.sqrt(left_vertical**2 + left_horizontal**2)
        right_angle = -math.degrees(math.atan2(right_vertical, right_horizontal))
        right_r = math.sqrt(right_vertical**2 + right_horizontal**2)

        # print(left_r, right_r)
        if left_r < dead_zone:
            left_r = 0
        if right_r < dead_zone:
            right_r = 0

        # print(left_angle, left_r)

        self.keyPress.input([Direction(Stick.LEFT, left_angle, left_r), Direction(Stick.RIGHT, right_angle, right_r)])

    def gamepad_l_stick(self):
        if self.setting.setting["key_config"]["joystick"]["direction"]["LStick"]:
            self.GamepadController_worker.set_l_stick(True)

    def gamepad_r_stick(self):
        if self.setting.setting["key_config"]["joystick"]["direction"]["RStick"]:
            self.GamepadController_worker.set_r_stick(True)

    # </editor-fold>

    def connect_capture(self):
        self.thread_1 = QThread()
        self.capture_worker = CaptureWorker(camera_id=int(self.lineEditCameraID.text()))
        self.capture_worker.moveToThread(self.thread_1)

        self.capture_worker.change_pixmap_signal.connect(self.update_image, type=Qt.QueuedConnection)
        self.capture_worker.print_strings.connect(self.callback_string_to_log, type=Qt.QueuedConnection)

        self.thread_1.started.connect(self.capture_worker.run)

        self.thread_1.finished.connect(self.capture_worker.deleteLater)
        self.thread_1.finished.connect(self.thread_1.deleteLater)

    def setup_functions_connect(self):
        # 各ボタンの関数割当
        self.pushButton_PythonStart.pressed.connect(self.start_command)
        self.pushButton_PythonStop.pressed.connect(self.stop_command)
        self.pushButton_PythonReload.clicked.connect(self.reload_commands)
        self.pushButton_MCUReload.clicked.connect(self.reload_commands)
        self.pushButtonReloadPort.clicked.connect(self.activate_serial)
        self.pushButtonScreenShot.clicked.connect(self.screen_shot)
        self.tabWidget.currentChanged.connect(self.set_command_mode)

        # 　各コンボボックス選択時の挙動
        self.comboBoxPython.currentIndexChanged.connect(self.assign_command)
        self.comboBox_MCU.currentIndexChanged.connect(self.assign_command)

        # キャプチャ画像クリック時に座標を返すように
        self.CaptureImageArea.mousePressEvent = self.getPixel

        # Setting.tomlへの保存
        self.lineEditFPS.textChanged.connect(self.assign_fps_to_setting)
        self.lineEditCameraID.textChanged.connect(self.assign_camera_id_to_setting)
        self.lineEditComPort.textChanged.connect(self.assign_com_port_to_setting)
        self.comboBox_MCU.currentIndexChanged.connect(self.assign_mcu_command_to_setting)
        self.comboBoxPython.currentIndexChanged.connect(self.assign_py_command_to_setting)

    def assign_fps_to_setting(self):
        self.setting.setting["main_window"]["must"]["fps"] = self.lineEditFPS.text()

    def assign_camera_id_to_setting(self):
        self.setting.setting["main_window"]["must"]["camera_id"] = self.lineEditCameraID.text()

    def assign_com_port_to_setting(self):
        self.setting.setting["main_window"]["must"]["com_port"] = self.lineEditComPort.text()

    def assign_window_size_to_setting(self):
        self.setting.setting["main_window"]["must"]["com_port"] = self.lineEditComPort.text()

    def assign_mcu_command_to_setting(self):
        self.setting.setting["command"]["mcu_command"] = self.comboBox_MCU.itemText(self.comboBox_MCU.currentIndex())

    def assign_py_command_to_setting(self):
        self.setting.setting["command"]["py_command"] = self.comboBoxPython.itemText(self.comboBoxPython.currentIndex())

    def resizeEvent(self, event: PySide6.QtGui.QResizeEvent) -> None:
        self.setting.setting["main_window"]["option"]["window_size_width"] = self.width()
        self.setting.setting["main_window"]["option"]["window_size_height"] = self.height()

    def set_command_mode(self):
        if self.tabWidget.currentIndex() == 0:
            self.command_mode = "python"
        elif self.tabWidget.currentIndex() == 1:
            self.command_mode = "mcu"
        else:
            raise Exception

    @Slot(QImage)
    def update_image(self, image):
        self.img = image
        pix = QPixmap.fromImage(self.img)
        # pix.scaled(1280, 720, aspectMode=QtCore.Qt.KeepAspectRatio)
        self.CaptureImageArea.setPixmap(pix)

    @Slot(str)
    def update_log(self, s):
        # self.plainTextEdit.insertPlainText(s + "\n")
        pass

    @Slot(bool)
    def img_recognition_return(self):
        return self.img

    def reconnect_camera(self, cam_id):
        self.capture_worker.open_camera(int(cam_id))

    def activate_serial(self):
        if self.ser.isOpened():
            print("Port is already opened and being closed.")
            self.ser.closeSerial()
            self.keyPress = None
            self.activate_serial()
        else:
            if self.ser.openSerial(self.setting.setting["main_window"]["must"]["com_port"], ""):
                self.logger.debug(
                    "COM Port "
                    + str(self.setting.setting["main_window"]["must"]["com_port"])
                    + " connected successfully"
                )
                self.keyPress = KeyPress(self.ser)
        pass

    # Todo キーボード操作できるようにする
    def activate_keyboard(self):
        pass

    def load_commands(self):
        self.py_loader = CommandLoader(ospath("Commands/Python"), CommandBase)  # コマンドの読み込み
        self.mcu_loader = CommandLoader(ospath("Commands/MCU"), McuCommand)
        self.py_classes = self.py_loader.load()
        self.mcu_classes = self.mcu_loader.load()
        self.set_command_items()
        self.assign_command()

    def set_command_items(self):
        for v in [c.NAME for c in self.py_classes]:
            self.comboBoxPython.addItem(v)
        self.comboBoxPython.setCurrentIndex(0)
        for v in [c.NAME for c in self.mcu_classes]:
            self.comboBox_MCU.addItem(v)
        self.comboBox_MCU.setCurrentIndex(0)

    def assign_command(self):
        # 選択されているコマンドを取得する
        self.mcu_cur_command = self.mcu_classes[self.comboBox_MCU.currentIndex()]  # MCUコマンドについて

        self.py_cur_command = self.py_classes[self.comboBoxPython.currentIndex()]

        if self.tabWidget.currentIndex() == 0:
            self.cur_command = self.py_cur_command
        else:
            self.cur_command = self.mcu_cur_command

    def reload_commands(self):
        # 表示しているタブを読み取って、どのコマンドを表示しているか取得、リロード後もそれが選択されるようにする
        oldval_mcu = self.comboBox_MCU.itemText(self.comboBox_MCU.currentIndex())
        oldval_py = self.comboBoxPython.itemText(self.comboBoxPython.currentIndex())

        self.comboBox_MCU.clear()
        self.comboBoxPython.clear()

        self.py_classes = self.py_loader.reload()
        self.mcu_classes = self.mcu_loader.reload()

        # Restore the command selecting state if possible
        self.set_command_items()
        if self.comboBox_MCU.findText(oldval_mcu) != -1:
            self.comboBox_MCU.setCurrentIndex(self.comboBox_MCU.findText(oldval_mcu))
        else:
            self.comboBox_MCU.setCurrentIndex(0)

        if self.comboBoxPython.findText(oldval_py) != -1:
            self.comboBoxPython.setCurrentIndex(self.comboBoxPython.findText(oldval_py))
        else:
            self.comboBoxPython.setCurrentIndex(0)
        self.assign_command()
        self.logger.info("Reloaded commands.")

    def reload_camera(self):
        self.capture_worker.set_fps(self.setting.setting["main_window"]["must"]["fps"])
        pass

    def screen_shot(self):
        try:
            self.capture_worker.saveCapture(capture_dir=self.cur_command.CAPTURE_DIR)
        except Exception as e:
            self.logger.error(e)
            pass
        pass

    def getPixel(self, event):
        print(event.type)
        w = self.CaptureImageArea.width()
        h = self.CaptureImageArea.height()
        x = event.position().x()
        x_ = int(x * 1280 / w)
        y = event.position().y()
        y_ = int(y * 720 / h)
        c = self.img.pixel(x_, y_)
        # c_qobj = QColor
        c_rgb = QColor(c).getRgb()
        self.logger.debug(f"Clicked at x:{x_} y:{y_}, R:{c_rgb[0]} G:{c_rgb[1]} B: {c_rgb[2]}")
        return x, y, c_rgb

    def open_screen_shot_dir(self):
        pass

    def start_command(self):
        self.GamepadController_worker.pause = True
        self.assign_command()
        self.pushButton_PythonStart.setEnabled(False)
        # if self.thread_2 is not None:
        self.stop_command()
        if self.thread_2 is None:
            self.thread_2 = QThread()
        self.worker = self.cur_command()

        self.worker.moveToThread(self.thread_2)

        self.worker.print_strings.connect(self.callback_string_to_log, type=Qt.QueuedConnection)
        self.stop_request.connect(self.worker.stop, type=Qt.QueuedConnection)
        self.worker.stop_function.connect(self.callback_stop_command, type=Qt.QueuedConnection)

        self.worker.serial_input.connect(self.callback_keypress, type=Qt.DirectConnection)
        self.worker.get_image.connect(self.callback_return_img, type=Qt.DirectConnection)
        self.capture_worker.send_img.connect(self.worker.callback_receive_img, type=Qt.DirectConnection)

        self.thread_2.started.connect(self.worker.run)

        self.thread_2.finished.connect(self.worker.deleteLater)
        self.thread_2.finished.connect(self.thread_2.deleteLater)
        self.thread_2.start()

    @staticmethod
    def callback_start_command(self, is_alive: bool):
        try:
            if is_alive:
                print("ALIVE")
            else:
                print("DEAD")

        except Exception as e:
            print(e)
        pass

    def stop_command(self):
        if self.thread_2 and shiboken6.isValid(self.thread_2):
            self.logger.debug("Send Stop Requests.")
            # self.stop_request.emit(True)
            # スレッドが作成されていて、削除されていない
            if self.thread_2.isRunning() or not self.thread_2.isFinished():
                # self.worker.get_image.disconnect()
                print("thread is stopping")
                self.worker.stop()
                self.thread_2.quit()
                self.thread_2.wait()
                print("thread is stopped")
                self.worker = None
                self.thread_2 = None
                try:
                    self.GamepadController_worker.is_alive = True
                    self.GamepadController_worker.pause = False
                except:
                    print("ERROR")
                # self.callback_stop_command()

    @Slot(str, type(logging.DEBUG))
    def callback_string_to_log(self, s, level) -> None:
        match level:
            case logging.DEBUG:
                self.logger.debug(s)
            case logging.INFO:
                self.logger.info(s)
            case logging.WARNING:
                self.logger.warning(s)
            case logging.ERROR:
                self.logger.error(s)
            case logging.CRITICAL:
                self.logger.critical(s)
            case logging.FATAL:
                self.logger.fatal(s)

    def callback_stop_command(self):
        self.pushButton_PythonStart.setEnabled(True)
        self.stop_command()
        pass

    def open_python_commands_dir(self):
        pass

    def open_mcu_commands_dir(self):
        pass

    @Slot(type(Button.A), float, float)
    def callback_keypress(self, buttons, duration, wait):
        self.keyPress.input(buttons)
        self.wait(duration)
        self.keyPress.inputEnd(buttons)
        self.wait(wait)

    @staticmethod
    def wait(wait):
        if float(wait) > 0.1:
            time.sleep(wait)
        else:
            current_time = time.perf_counter()
            while time.perf_counter() < current_time + wait:
                pass

    def callback_return_img(self):
        self.capture_worker.callback_return_img(True)
        pass

    def set_settings(self):

        try:
            self.logger.debug("Load setting")
            self.setting.load()
        except FileNotFoundError:
            self.logger.debug("File Not Found" "Generate setting")
            self.setting.generate()
            self.setting.load()

        self.lineEditFPS.setText(str(self.setting.setting["main_window"]["must"]["fps"]))
        self.lineEditCameraID.setText(str(self.setting.setting["main_window"]["must"]["camera_id"]))
        self.lineEditComPort.setText(str(self.setting.setting["main_window"]["must"]["com_port"]))

        self.keymap = {
            v["assign"]: k for k, v in self.setting.setting["key_config"]["joystick"]["button"].items() if v["state"]
        } | {v["assign"]: k for k, v in self.setting.setting["key_config"]["joystick"]["hat"].items() if v["state"]}

    def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
        self.setting.save()
        try:
            self.thread_1.terminate()
            self.thread_2.terminate()
            # self.GamepadController_worker.p.terminate()
            # self.GamepadController_worker.p.join()
        except Exception:
            pass
        try:
            self.GamepadController_worker.p.terminate()
            self.GamepadController_worker.p.join()
            self.GamepadController_thread.terminate()
        except Exception as e:
            print(000, e)
            pass

        self.logger.debug("Save settings")
        return super().closeEvent(event)


if __name__ == "__main__":
    logger = logging.Logger(__name__)
    # 環境変数にPySide6を登録
    dirname = os.path.dirname(PySide6.__file__)
    pluginPath = os.path.join(dirname, "plugins", "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = pluginPath

    try:
        with open("ui/style.qss", "r") as f:
            style = f.read()
    except:
        style = ""
    # print(style)

    try:
        app = QApplication(sys.argv)
        app.setStyleSheet(style)
        window = MainWindow()
        window.show()
    except Exception as e:
        # app = None
        logger.exception(e)

    sys.exit(app.exec())
