import os
import sys
import threading
import time
from multiprocessing import Array, Process, shared_memory

import numpy as np
import pygame
import pygame.locals
import PySide6
from PySide6 import QtCore, QtGui, QtSerialPort, QtWidgets
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QPushButton

from libs.settings import Setting
from ui.key_config import Ui_Form


class Joystick(QtCore.QObject):
    A_PRESSED = QtCore.Signal()
    B_PRESSED = QtCore.Signal()
    X_PRESSED = QtCore.Signal()
    Y_PRESSED = QtCore.Signal()
    R_PRESSED = QtCore.Signal()
    L_PRESSED = QtCore.Signal()
    UP_PRESSED = QtCore.Signal()
    DOWN_PRESSED = QtCore.Signal()
    LEFT_PRESSED = QtCore.Signal()
    RIGHT_PRESSED = QtCore.Signal()
    VIEW_PRESSED = QtCore.Signal()
    MENU_PRESSED = QtCore.Signal()

    A_RELEASED = QtCore.Signal()
    B_RELEASED = QtCore.Signal()
    X_RELEASED = QtCore.Signal()
    Y_RELEASED = QtCore.Signal()
    R_RELEASED = QtCore.Signal()
    L_RELEASED = QtCore.Signal()
    UP_RELEASED = QtCore.Signal()
    DOWN_RELEASED = QtCore.Signal()
    LEFT_RELEASED = QtCore.Signal()
    RIGHT_RELEASED = QtCore.Signal()
    VIEW_RELEASED = QtCore.Signal()
    MENU_RELEASED = QtCore.Signal()

    AXIS_MOVED = QtCore.Signal(float, float, float, float, float, float)

    def __init__(self, parent):
        super().__init__(parent)
        pygame.init()
        pygame.joystick.init()
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        self.hat_prev = 0

    def get_hat(self):
        hat = self.joystick.get_hat(0)
        val = 0
        val += int(hat[1] == 1) << 0  # up
        val += int(hat[1] == -1) << 1  # down
        val += int(hat[0] == 1) << 2  # right
        val += int(hat[0] == -1) << 3  # left
        val, self.hat_prev = val - self.hat_prev, val
        return val

    def run(self) -> None:
        while True:
            for e in pygame.event.get():
                print(e.type)

                if e.type == pygame.locals.JOYAXISMOTION:
                    self.AXIS_MOVED.emit(
                        self.joystick.get_axis(0),  # left horizontal
                        self.joystick.get_axis(1),  # left vertical
                        self.joystick.get_axis(2),  # right horizontal
                        self.joystick.get_axis(3),  # right vertical
                        self.joystick.get_axis(4),  # left trigger
                        self.joystick.get_axis(5),  # right triggr
                    )

                elif e.type == pygame.locals.JOYHATMOTION:
                    h = self.get_hat()
                    if h > 0:
                        if (h >> 0) & 1:
                            self.UP_PRESSED.emit()
                        if (h >> 1) & 1:
                            self.DOWN_PRESSED.emit()
                        if (h >> 2) & 1:
                            self.RIGHT_PRESSED.emit()
                        if (h >> 3) & 1:
                            self.LEFT_PRESSED.emit()
                    else:
                        if (abs(h) >> 0) & 1:
                            self.UP_RELEASED.emit()
                        if (abs(h) >> 1) & 1:
                            self.DOWN_RELEASED.emit()
                        if (abs(h) >> 2) & 1:
                            self.RIGHT_RELEASED.emit()
                        if (abs(h) >> 3) & 1:
                            self.LEFT_RELEASED.emit()

                elif e.type == pygame.locals.JOYBUTTONDOWN:
                    if e.button == 0:
                        self.A_PRESSED.emit()
                    if e.button == 1:
                        self.B_PRESSED.emit()
                    if e.button == 2:
                        self.X_PRESSED.emit()
                    if e.button == 3:
                        self.Y_PRESSED.emit()
                    if e.button == 4:
                        self.L_PRESSED.emit()
                    if e.button == 5:
                        self.R_PRESSED.emit()
                    if e.button == 6:
                        self.VIEW_PRESSED.emit()
                    if e.button == 7:
                        self.MENU_PRESSED.emit()

                elif e.type == pygame.locals.JOYBUTTONUP:
                    if e.button == 0:
                        self.A_RELEASED.emit()
                    if e.button == 1:
                        self.B_RELEASED.emit()
                    if e.button == 2:
                        self.X_RELEASED.emit()
                    if e.button == 3:
                        self.Y_RELEASED.emit()
                    if e.button == 4:
                        self.L_RELEASED.emit()
                    if e.button == 5:
                        self.R_RELEASED.emit()
                    if e.button == 6:
                        self.VIEW_RELEASED.emit()
                    if e.button == 7:
                        self.MENU_RELEASED.emit()


class SettingWindow(QtWidgets.QWidget, Ui_Form):
    def __init__(self, parent=None, _setting=None):
        super(SettingWindow, self).__init__()
        self.is_alive = False
        self.setupUi(self)
        self.setting = _setting
        self.setting.load()
        print(self.setting.setting)
        self.controller_setting = self.setting.setting["key_config"]["joystick"]
        self.set_config()
        self.set_state()
        self.connect_function()

        pygame.init()
        pygame.joystick.init()
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        self.setWindowTitle(self.joystick.get_name())
        self.hat_prev = 0
        self.keymap = {
            v["assign"]: k for k, v in self.setting.setting["key_config"]["joystick"]["button"].items() if v["state"]
        } | {v["assign"]: k for k, v in self.setting.setting["key_config"]["joystick"]["hat"].items() if v["state"]}
        # print(self.keymap)

        self.Controller_worker = GamepadController()
        self.Controller_thread = QtCore.QThread()
        self.Controller_worker.moveToThread(self.Controller_thread)
        self.Controller_thread.started.connect(self.Controller_worker.run)
        self.Controller_worker.set_keymap(self.keymap)
        self.Controller_thread.start()

    def connect_function(self):
        self.lineEdit.textChanged.connect(self.btn_ZL)
        self.lineEdit.textChanged.connect(self.btn_ZL)
        self.lineEdit_2.textChanged.connect(self.btn_L)
        self.lineEdit_3.textChanged.connect(self.btn_LCLICK)
        self.lineEdit_4.textChanged.connect(self.btn_MINUS)
        self.lineEdit_5.textChanged.connect(self.hat_TOP)
        self.lineEdit_6.textChanged.connect(self.hat_BTM)
        self.lineEdit_7.textChanged.connect(self.hat_LEFT)
        self.lineEdit_8.textChanged.connect(self.hat_RIGHT)
        self.lineEdit_9.textChanged.connect(self.btn_CAPTURE)
        self.lineEdit_10.textChanged.connect(self.btn_ZR)
        self.lineEdit_11.textChanged.connect(self.btn_R)
        self.lineEdit_12.textChanged.connect(self.btn_RCLICK)
        self.lineEdit_13.textChanged.connect(self.btn_PLUS)
        self.lineEdit_14.textChanged.connect(self.btn_A)
        self.lineEdit_15.textChanged.connect(self.btn_B)
        self.lineEdit_16.textChanged.connect(self.btn_X)
        self.lineEdit_17.textChanged.connect(self.btn_Y)
        self.lineEdit_18.textChanged.connect(self.btn_HOME)

        self.checkBox.stateChanged.connect(self.btn_ZL)
        self.checkBox_2.stateChanged.connect(self.btn_L)
        self.checkBox_3.stateChanged.connect(self.btn_LCLICK)
        self.checkBox_4.stateChanged.connect(self.btn_MINUS)
        self.checkBox_5.stateChanged.connect(self.hat_TOP)
        self.checkBox_6.stateChanged.connect(self.hat_BTM)
        self.checkBox_7.stateChanged.connect(self.hat_LEFT)
        self.checkBox_8.stateChanged.connect(self.hat_RIGHT)
        self.checkBox_9.stateChanged.connect(self.btn_CAPTURE)
        self.checkBox_10.stateChanged.connect(self.btn_ZR)
        self.checkBox_11.stateChanged.connect(self.btn_R)
        self.checkBox_12.stateChanged.connect(self.btn_RCLICK)
        self.checkBox_13.stateChanged.connect(self.btn_PLUS)
        self.checkBox_14.stateChanged.connect(self.btn_A)
        self.checkBox_15.stateChanged.connect(self.btn_B)
        self.checkBox_16.stateChanged.connect(self.btn_X)
        self.checkBox_17.stateChanged.connect(self.btn_Y)
        self.checkBox_18.stateChanged.connect(self.btn_HOME)

        self.checkBox_21.stateChanged.connect(self.dir_L)
        self.checkBox_22.stateChanged.connect(self.dir_R)

        self.pushButton.clicked.connect(self.set_btn_ZL)
        self.pushButton_2.clicked.connect(self.set_btn_L)
        self.pushButton_3.clicked.connect(self.set_btn_LCLICK)
        self.pushButton_4.clicked.connect(self.set_btn_MINUS)
        self.pushButton_5.clicked.connect(self.set_hat_TOP)
        self.pushButton_6.clicked.connect(self.set_hat_BTM)
        self.pushButton_7.clicked.connect(self.set_hat_LEFT)
        self.pushButton_8.clicked.connect(self.set_hat_RIGHT)
        self.pushButton_9.clicked.connect(self.set_btn_CAPTURE)
        self.pushButton_10.clicked.connect(self.set_btn_ZR)
        self.pushButton_11.clicked.connect(self.set_btn_R)
        self.pushButton_12.clicked.connect(self.set_btn_RCLICK)
        self.pushButton_13.clicked.connect(self.set_btn_PLUS)
        self.pushButton_14.clicked.connect(self.set_btn_A)
        self.pushButton_15.clicked.connect(self.set_btn_B)
        self.pushButton_16.clicked.connect(self.set_btn_X)
        self.pushButton_17.clicked.connect(self.set_btn_Y)
        self.pushButton_18.clicked.connect(self.set_btn_HOME)

        self.pushButton_19.clicked.connect(self.remap_key)

    def set_config(self):
        self.lineEdit.setText(self.controller_setting["button"]["ZL"]["assign"])
        self.lineEdit_2.setText(self.controller_setting["button"]["L"]["assign"])
        self.lineEdit_3.setText(self.controller_setting["button"]["LCLICK"]["assign"])
        self.lineEdit_4.setText(self.controller_setting["button"]["MINUS"]["assign"])
        self.lineEdit_5.setText(self.controller_setting["hat"]["TOP"]["assign"])
        self.lineEdit_6.setText(self.controller_setting["hat"]["BTM"]["assign"])
        self.lineEdit_7.setText(self.controller_setting["hat"]["LEFT"]["assign"])
        self.lineEdit_8.setText(self.controller_setting["hat"]["RIGHT"]["assign"])
        self.lineEdit_9.setText(self.controller_setting["button"]["CAPTURE"]["assign"])
        self.lineEdit_10.setText(self.controller_setting["button"]["ZR"]["assign"])
        self.lineEdit_11.setText(self.controller_setting["button"]["R"]["assign"])
        self.lineEdit_12.setText(self.controller_setting["button"]["RCLICK"]["assign"])
        self.lineEdit_13.setText(self.controller_setting["button"]["PLUS"]["assign"])
        self.lineEdit_14.setText(self.controller_setting["button"]["A"]["assign"])
        self.lineEdit_15.setText(self.controller_setting["button"]["B"]["assign"])
        self.lineEdit_16.setText(self.controller_setting["button"]["X"]["assign"])
        self.lineEdit_17.setText(self.controller_setting["button"]["Y"]["assign"])
        self.lineEdit_18.setText(self.controller_setting["button"]["HOME"]["assign"])

    def set_state(self):
        if self.controller_setting["button"]["ZL"]["state"]:
            self.checkBox.toggle()
        if self.controller_setting["button"]["L"]["state"]:
            self.checkBox_2.toggle()
        if self.controller_setting["button"]["LCLICK"]["state"]:
            self.checkBox_3.toggle()
        if self.controller_setting["button"]["MINUS"]["state"]:
            self.checkBox_4.toggle()
        if self.controller_setting["hat"]["TOP"]["state"]:
            self.checkBox_5.toggle()
        if self.controller_setting["hat"]["BTM"]["state"]:
            self.checkBox_6.toggle()
        if self.controller_setting["hat"]["LEFT"]["state"]:
            self.checkBox_7.toggle()
        if self.controller_setting["hat"]["RIGHT"]["state"]:
            self.checkBox_8.toggle()
        if self.controller_setting["button"]["CAPTURE"]["state"]:
            self.checkBox_9.toggle()
        if self.controller_setting["button"]["ZR"]["state"]:
            self.checkBox_10.toggle()
        if self.controller_setting["button"]["R"]["state"]:
            self.checkBox_11.toggle()
        if self.controller_setting["button"]["RCLICK"]["state"]:
            self.checkBox_12.toggle()
        if self.controller_setting["button"]["PLUS"]["state"]:
            self.checkBox_13.toggle()
        if self.controller_setting["button"]["A"]["state"]:
            self.checkBox_14.toggle()
        if self.controller_setting["button"]["B"]["state"]:
            self.checkBox_15.toggle()
        if self.controller_setting["button"]["X"]["state"]:
            self.checkBox_16.toggle()
        if self.controller_setting["button"]["Y"]["state"]:
            self.checkBox_17.toggle()
        if self.controller_setting["button"]["HOME"]["state"]:
            self.checkBox_18.toggle()

        if self.controller_setting["direction"]["LStick"]:
            self.checkBox_21.toggle()
        if self.controller_setting["direction"]["RStick"]:
            self.checkBox_22.toggle()

    def remap_key(self):
        self.keymap = {
            v["assign"]: k for k, v in self.setting.setting["key_config"]["joystick"]["button"].items() if v["state"]
        } | {v["assign"]: k for k, v in self.setting.setting["key_config"]["joystick"]["hat"].items() if v["state"]}
        try:
            self.Controller_worker.set_keymap(self.keymap)
        except Exception as e:
            pass
        print(self.keymap)

    def btn_ZL(self):
        self.setting.setting["key_config"]["joystick"]["button"]["ZL"] = {
            "state": self.checkBox.isChecked(),
            "assign": self.lineEdit.text(),
        }

    def btn_L(self):
        self.setting.setting["key_config"]["joystick"]["button"]["L"] = {
            "state": self.checkBox_2.isChecked(),
            "assign": self.lineEdit_2.text(),
        }

    def btn_LCLICK(self):
        self.setting.setting["key_config"]["joystick"]["button"]["LCLICK"] = {
            "state": self.checkBox_3.isChecked(),
            "assign": self.lineEdit_3.text(),
        }

    def btn_MINUS(self):
        self.setting.setting["key_config"]["joystick"]["button"]["MINUS"] = {
            "state": self.checkBox_4.isChecked(),
            "assign": self.lineEdit_4.text(),
        }

    def hat_TOP(self):
        self.setting.setting["key_config"]["joystick"]["hat"]["TOP"] = {
            "state": self.checkBox_5.isChecked(),
            "assign": self.lineEdit_5.text(),
        }

    def hat_BTM(self):
        self.setting.setting["key_config"]["joystick"]["hat"]["BTM"] = {
            "state": self.checkBox_6.isChecked(),
            "assign": self.lineEdit_6.text(),
        }

    def hat_LEFT(self):
        self.setting.setting["key_config"]["joystick"]["hat"]["LEFT"] = {
            "state": self.checkBox_7.isChecked(),
            "assign": self.lineEdit_7.text(),
        }

    def hat_RIGHT(self):
        self.setting.setting["key_config"]["joystick"]["hat"]["RIGHT"] = {
            "state": self.checkBox_8.isChecked(),
            "assign": self.lineEdit_8.text(),
        }

    def btn_CAPTURE(self):
        self.setting.setting["key_config"]["joystick"]["button"]["CAPTURE"] = {
            "state": self.checkBox_9.isChecked(),
            "assign": self.lineEdit_9.text(),
        }

    def btn_ZR(self):
        self.setting.setting["key_config"]["joystick"]["button"]["ZR"] = {
            "state": self.checkBox_10.isChecked(),
            "assign": self.lineEdit_10.text(),
        }

    def btn_R(self):
        self.setting.setting["key_config"]["joystick"]["button"]["R"] = {
            "state": self.checkBox_11.isChecked(),
            "assign": self.lineEdit_11.text(),
        }

    def btn_RCLICK(self):
        self.setting.setting["key_config"]["joystick"]["button"]["RCLICK"] = {
            "state": self.checkBox_12.isChecked(),
            "assign": self.lineEdit_12.text(),
        }

    def btn_PLUS(self):
        self.setting.setting["key_config"]["joystick"]["button"]["PLUS"] = {
            "state": self.checkBox_13.isChecked(),
            "assign": self.lineEdit_13.text(),
        }

    def btn_A(self):
        self.setting.setting["key_config"]["joystick"]["button"]["A"] = {
            "state": self.checkBox_14.isChecked(),
            "assign": self.lineEdit_14.text(),
        }

    def btn_B(self):
        self.setting.setting["key_config"]["joystick"]["button"]["B"] = {
            "state": self.checkBox_15.isChecked(),
            "assign": self.lineEdit_15.text(),
        }

    def btn_X(self):
        self.setting.setting["key_config"]["joystick"]["button"]["X"] = {
            "state": self.checkBox_16.isChecked(),
            "assign": self.lineEdit_16.text(),
        }

    def btn_Y(self):
        self.setting.setting["key_config"]["joystick"]["button"]["Y"] = {
            "state": self.checkBox_17.isChecked(),
            "assign": self.lineEdit_17.text(),
        }

    def btn_HOME(self):
        self.setting.setting["key_config"]["joystick"]["button"]["HOME"] = {
            "state": self.checkBox_18.isChecked(),
            "assign": self.lineEdit_18.text(),
        }

    def dir_L(self):
        self.setting.setting["key_config"]["joystick"]["direction"]["LStick"] = self.checkBox_21.isChecked()

    def dir_R(self):
        self.setting.setting["key_config"]["joystick"]["direction"]["RStick"] = self.checkBox_22.isChecked()

    def set_btn_ZL(self):
        ret = self.set_key()
        self.lineEdit.setText(str(ret))

    def set_btn_L(self):
        ret = self.set_key()
        self.lineEdit_2.setText(str(ret))

    def set_btn_LCLICK(self):
        ret = self.set_key()
        self.lineEdit_3.setText(str(ret))

    def set_btn_MINUS(self):
        ret = self.set_key()
        self.lineEdit_4.setText(str(ret))

    def set_hat_TOP(self):
        ret = self.set_key()
        self.lineEdit_5.setText(str(ret))

    def set_hat_BTM(self):
        ret = self.set_key()
        self.lineEdit_6.setText(str(ret))

    def set_hat_LEFT(self):
        ret = self.set_key()
        self.lineEdit_7.setText(str(ret))

    def set_hat_RIGHT(self):
        ret = self.set_key()
        self.lineEdit_8.setText(str(ret))

    def set_btn_CAPTURE(self):
        ret = self.set_key()
        self.lineEdit_9.setText(str(ret))

    def set_btn_ZR(self):
        ret = self.set_key()
        self.lineEdit_10.setText(str(ret))

    def set_btn_R(self):
        ret = self.set_key()
        self.lineEdit_11.setText(str(ret))

    def set_btn_RCLICK(self):
        ret = self.set_key()
        self.lineEdit_12.setText(str(ret))

    def set_btn_PLUS(self):
        ret = self.set_key()
        self.lineEdit_13.setText(str(ret))

    def set_btn_A(self):
        ret = self.set_key()
        self.lineEdit_14.setText(str(ret))

    def set_btn_B(self):
        ret = self.set_key()
        self.lineEdit_15.setText(str(ret))

    def set_btn_X(self):
        ret = self.set_key()
        self.lineEdit_16.setText(str(ret))

    def set_btn_Y(self):
        ret = self.set_key()
        self.lineEdit_17.setText(str(ret))

    def set_btn_HOME(self):
        ret = self.set_key()
        self.lineEdit_18.setText(str(ret))

    @staticmethod
    def set_key():
        ret = None
        while True:
            for e in pygame.event.get():

                if e.type == pygame.locals.JOYAXISMOTION:
                    # print(e)
                    # print(self.joystick.get_axis(0))  # left horizontal
                    # print(self.joystick.get_axis(1))  # left vertical
                    # print(self.joystick.get_axis(2))  # right horizontal
                    # print(self.joystick.get_axis(3))  # right vertical
                    # print(self.joystick.get_axis(4))  # left trigger
                    # print(self.joystick.get_axis(5))  # right trigger
                    if e.axis == 4 or e.axis == 5:
                        ret = f"axis.{e.axis}"
                        print(e)
                    pass

                elif e.type == pygame.locals.JOYHATMOTION:
                    ret = e
                    print(e)
                    pass

                elif e.type == pygame.locals.JOYBUTTONDOWN:
                    ret = f"button.{e.button}"
                    print(e, e.button)
                    pass

                elif e.type == pygame.locals.JOYBUTTONUP:
                    pass
            if ret is not None:
                break
        return ret

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.setting.save()
        self.Controller_worker.is_alive = False
        # self.Controller_thread.quit()
        return super().closeEvent(a0)


class GamepadController(QObject):
    ZL_PRESSED = QtCore.Signal()
    L_PRESSED = QtCore.Signal()
    LCLICK_PRESSED = QtCore.Signal()
    MINUS_PRESSED = QtCore.Signal()
    TOP_PRESSED = QtCore.Signal()
    BTM_PRESSED = QtCore.Signal()
    LEFT_PRESSED = QtCore.Signal()
    RIGHT_PRESSED = QtCore.Signal()
    CAPTURE_PRESSED = QtCore.Signal()
    ZR_PRESSED = QtCore.Signal()
    R_PRESSED = QtCore.Signal()
    RCLICK_PRESSED = QtCore.Signal()
    PLUS_PRESSED = QtCore.Signal()
    A_PRESSED = QtCore.Signal()
    B_PRESSED = QtCore.Signal()
    X_PRESSED = QtCore.Signal()
    Y_PRESSED = QtCore.Signal()
    HOME_PRESSED = QtCore.Signal()

    ZL_RELEASED = QtCore.Signal()
    L_RELEASED = QtCore.Signal()
    LCLICK_RELEASED = QtCore.Signal()
    MINUS_RELEASED = QtCore.Signal()
    TOP_RELEASED = QtCore.Signal()
    BTM_RELEASED = QtCore.Signal()
    LEFT_RELEASED = QtCore.Signal()
    RIGHT_RELEASED = QtCore.Signal()
    CAPTURE_RELEASED = QtCore.Signal()
    ZR_RELEASED = QtCore.Signal()
    R_RELEASED = QtCore.Signal()
    RCLICK_RELEASED = QtCore.Signal()
    PLUS_RELEASED = QtCore.Signal()
    A_RELEASED = QtCore.Signal()
    B_RELEASED = QtCore.Signal()
    X_RELEASED = QtCore.Signal()
    Y_RELEASED = QtCore.Signal()
    HOME_RELEASED = QtCore.Signal()

    AXIS_MOVED = QtCore.Signal(float, float, float, float)

    def __init__(self):
        super(GamepadController, self).__init__()
        self.use_Rstick = None
        self.use_Lstick = None
        self.is_alive = True
        self.keymap = {}
        self.pause = False
        pygame.init()
        if not self.connect_joystick():
            self.no_joystick = True

        self._stick = np.zeros((4, 1))
        self._btn_down = np.array([0])
        self._btn_up = np.array([0])

        self.shm = shared_memory.SharedMemory(create=True, size=self._stick.nbytes, name="stick")  # 共有メモリを作成

        self.stick = np.ndarray(self._stick.shape, dtype=self._stick.dtype, buffer=self.shm.buf)

        if not self.no_joystick:
            self.p = Process(target=j_stick)

    def connect_joystick(self):
        try:
            pygame.joystick.init()
            self.joystick_ = pygame.joystick.Joystick(0)
            self.joystick_.init()
            print("init joystick")
            self.no_joystick = False
            return True
        except:
            print("No joystick")
            return False

    def reconnect_subprocess(self):
        self.p.kill()
        self.p = Process(target=j_stick)
        self.p.start()

    def set_keymap(self, keymap):
        self.keymap = keymap

    def set_l_stick(self, v):
        self.use_Lstick = v

    def set_r_stick(self, v):
        self.use_Rstick = v

    def run(self):
        # print(self.joystick.get_name())
        # self.joystick_.init()
        try:
            self.p.start()
        except:
            pass
        # while self.is_alive:
        while True:
            if self.pause is True or self.no_joystick is True:
                time.sleep(1.0)
                continue
            # print(f"running {threading.get_ident()}")
            start = time.perf_counter()

            if self.use_Lstick and self.use_Rstick:
                # self.AXIS_MOVED.emit(
                #     self.joystick_.get_axis(0),  # left horizontal
                #     self.joystick_.get_axis(1),  # left vertical
                #     self.joystick_.get_axis(2),  # right horizontal
                #     self.joystick_.get_axis(3),  # right vertical
                # )
                self.AXIS_MOVED.emit(
                    self.stick[0][0],  # left horizontal
                    self.stick[1][0],  # left vertical
                    self.stick[2][0],  # right horizontal
                    self.stick[3][0],  # right vertical
                )
            elif self.use_Lstick:
                # self.AXIS_MOVED.emit(
                #     self.joystick_.get_axis(0),  # left horizontal
                #     self.joystick_.get_axis(1),  # left vertical
                #     0,
                #     0,
                # )
                self.AXIS_MOVED.emit(
                    self.stick[0][0],  # left horizontal
                    self.stick[1][0],  # left vertical
                    0,
                    0,
                )
            elif self.use_Rstick:
                # self.AXIS_MOVED.emit(
                #     0,
                #     0,
                #     self.joystick_.get_axis(2),  # right horizontal
                #     self.joystick_.get_axis(3),  # right vertical
                # )
                self.AXIS_MOVED.emit(
                    0,
                    0,
                    self.stick[2][0],  # right horizontal
                    self.stick[3][0],  # right vertical
                )
            for e in pygame.event.get():
                # print(type(e))
                match e.type:
                    case pygame.locals.JOYAXISMOTION:
                        if self.keymap.get(f"axis.{e.axis}") is not None:  # ここはキー入力なので値を1, -1に丸めてもよい
                            # print("axis, ", self.keymap.get(f"axis.{e.axis}"), self.joystick.get_axis(e.axis))
                            val = int(round(self.joystick_.get_axis(e.axis), 0))
                            match self.keymap.get(f"axis.{e.axis}"):
                                case "ZL":
                                    if val == 1:
                                        self.ZL_PRESSED.emit()
                                    elif val == -1:
                                        self.ZL_RELEASED.emit()
                                case "L":
                                    if val == 1:
                                        self.L_PRESSED.emit()
                                    elif val == -1:
                                        self.L_RELEASED.emit()
                                case "LCLICK":
                                    if val == 1:
                                        self.LCLICK_PRESSED.emit()
                                    elif val == -1:
                                        self.LCLICK_RELEASED.emit()
                                case "MINUS":
                                    if val == 1:
                                        self.MINUS_PRESSED.emit()
                                    elif val == -1:
                                        self.MINUS_RELEASED.emit()
                                case "TOP":
                                    if val == 1:
                                        self.TOP_PRESSED.emit()
                                    elif val == -1:
                                        self.TOP_RELEASED.emit()
                                case "BTM":
                                    if val == 1:
                                        self.BTM_PRESSED.emit()
                                    elif val == -1:
                                        self.BTM_RELEASED.emit()
                                case "LEFT":
                                    if val == 1:
                                        self.LEFT_PRESSED.emit()
                                    elif val == -1:
                                        self.LEFT_RELEASED.emit()
                                case "RIGHT":
                                    if val == 1:
                                        self.RIGHT_PRESSED.emit()
                                    elif val == -1:
                                        self.RIGHT_RELEASED.emit()
                                case "CAPTURE":
                                    if val == 1:
                                        self.CAPTURE_PRESSED.emit()
                                    elif val == -1:
                                        self.CAPTURE_RELEASED.emit()
                                case "ZR":
                                    if val == 1:
                                        self.ZR_PRESSED.emit()
                                    elif val == -1:
                                        self.ZR_RELEASED.emit()
                                case "R":
                                    if val == 1:
                                        self.R_PRESSED.emit()
                                    elif val == -1:
                                        self.R_RELEASED.emit()
                                case "RCLICK":
                                    if val == 1:
                                        self.RCLICK_PRESSED.emit()
                                    elif val == -1:
                                        self.RCLICK_RELEASED.emit()
                                case "PLUS":
                                    if val == 1:
                                        self.PLUS_PRESSED.emit()
                                    elif val == -1:
                                        self.PLUS_RELEASED.emit()
                                case "A":
                                    if val == 1:
                                        self.A_PRESSED.emit()
                                    elif val == -1:
                                        self.A_RELEASED.emit()
                                case "B":
                                    if val == 1:
                                        self.B_PRESSED.emit()
                                    elif val == -1:
                                        self.B_RELEASED.emit()
                                case "X":
                                    if val == 1:
                                        self.X_PRESSED.emit()
                                    elif val == -1:
                                        self.X_RELEASED.emit()
                                case "Y":
                                    if val == 1:
                                        self.Y_PRESSED.emit()
                                    elif val == -1:
                                        self.Y_RELEASED.emit()
                                case "HOME":
                                    if val == 1:
                                        self.HOME_PRESSED.emit()
                                    elif val == -1:
                                        self.HOME_RELEASED.emit()

                    case pygame.locals.JOYBUTTONDOWN:

                        # print(self.btn_down)
                        if self.keymap.get(f"button.{e.button}") is not None:
                            # print("button-down, ", self.keymap.get(f"button.{e.button}"))
                            match self.keymap.get(f"button.{e.button}"):
                                case "ZL":
                                    self.ZL_PRESSED.emit()
                                case "L":
                                    self.L_PRESSED.emit()
                                case "LCLICK":
                                    self.LCLICK_PRESSED.emit()
                                case "MINUS":
                                    self.MINUS_PRESSED.emit()
                                case "TOP":
                                    self.TOP_PRESSED.emit()
                                case "BTM":
                                    self.BTM_PRESSED.emit()
                                case "LEFT":
                                    self.LEFT_PRESSED.emit()
                                case "RIGHT":
                                    self.RIGHT_PRESSED.emit()
                                case "CAPTURE":
                                    self.CAPTURE_PRESSED.emit()
                                case "ZR":
                                    self.ZR_PRESSED.emit()
                                case "R":
                                    self.R_PRESSED.emit()
                                case "RCLICK":
                                    self.RCLICK_PRESSED.emit()
                                case "PLUS":
                                    self.PLUS_PRESSED.emit()
                                case "A":
                                    self.A_PRESSED.emit()
                                case "B":
                                    self.B_PRESSED.emit()
                                case "X":
                                    self.X_PRESSED.emit()
                                case "Y":
                                    self.Y_PRESSED.emit()
                                case "HOME":
                                    self.HOME_PRESSED.emit()
                    case pygame.locals.JOYBUTTONUP:
                        if self.keymap.get(f"button.{e.button}") is not None:
                            # print("button-up, ", self.keymap.get(f"button.{e.button}"))
                            match self.keymap.get(f"button.{e.button}"):
                                case "ZL":
                                    self.ZL_RELEASED.emit()
                                case "L":
                                    self.L_RELEASED.emit()
                                case "LCLICK":
                                    self.LCLICK_RELEASED.emit()
                                case "MINUS":
                                    self.MINUS_RELEASED.emit()
                                case "TOP":
                                    self.TOP_RELEASED.emit()
                                case "BTM":
                                    self.BTM_RELEASED.emit()
                                case "LEFT":
                                    self.LEFT_RELEASED.emit()
                                case "RIGHT":
                                    self.RIGHT_RELEASED.emit()
                                case "CAPTURE":
                                    self.CAPTURE_RELEASED.emit()
                                case "ZR":
                                    self.ZR_RELEASED.emit()
                                case "R":
                                    self.R_RELEASED.emit()
                                case "RCLICK":
                                    self.RCLICK_RELEASED.emit()
                                case "PLUS":
                                    self.PLUS_RELEASED.emit()
                                case "A":
                                    self.A_RELEASED.emit()
                                case "B":
                                    self.B_RELEASED.emit()
                                case "X":
                                    self.X_RELEASED.emit()
                                case "Y":
                                    self.Y_RELEASED.emit()
                                case "HOME":
                                    self.HOME_RELEASED.emit()
            time.sleep(max(1 / 60 - (time.perf_counter() - start), 0.0001))

        print("DEAD")
        self.p.kill()

    def check(self):
        print(self.is_alive)

    def stop(self):
        self.is_alive = False
        self.p.kill()


def j_stick():
    print(os.getpid())
    pygame.init()
    pygame.joystick.init()
    joystick = pygame.joystick.Joystick(0)

    stick_shm = shared_memory.SharedMemory(name="stick")  # 共有メモリを取得
    stick = np.ndarray((4, 1), dtype=np.float64, buffer=stick_shm.buf)

    while True:
        for e in pygame.event.get():
            if e.type == pygame.locals.JOYAXISMOTION:
                stick[0] = joystick.get_axis(0)  # left horizontal
                stick[1] = joystick.get_axis(1)  # left vertical
                stick[2] = joystick.get_axis(2)  # right horizontal
                stick[3] = joystick.get_axis(3)  # right vertical


if __name__ == "__main__":
    # 環境変数にPySide6を登録
    dir_name = os.path.dirname(PySide6.__file__)
    pluginPath = os.path.join(dir_name, "plugins", "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = pluginPath
    setting = Setting.alternate("../config/settings.toml")

    app = QtWidgets.QApplication(sys.argv)
    w = SettingWindow(_setting=setting)
    w.show()
    app.exec()
