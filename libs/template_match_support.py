import logging
import pathlib
import sys
import threading
from typing import Optional

from libs.CommandBase import CommandBase
from libs.enums import ColorType
from libs.keys import Button, Hat, Direction
import timeit
import cv2
import PySide6
import numpy as np
import shiboken6
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QSize, Qt, QThread, Signal, Slot, QPoint, QRect, QRectF
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QVBoxLayout, QLabel, QDialog, \
    QHBoxLayout, QGraphicsView, QFileDialog, QButtonGroup

from ui.template_match_support import Ui_Form


class TemplateMatchSupport(QWidget, Ui_Form):
    get_image = Signal()
    print_strings = Signal(str, type(logging.DEBUG))

    def __init__(self, parent=None):
        super().__init__(parent)

        self.__isCanceled = False
        self.threshold = None
        self.scene: QtWidgets.QGraphicsScene | None = None
        self.image: cv2.imread | None = None
        self.show_image = None
        self.frame = None
        self.pixmap: QtGui.QPixmap | None = None
        self.pixmap_mode = "Color"
        self.pen: QPen = QPen()
        self.pen.setColor(QColor(255, 0, 0))
        self.pen_found: QPen = QPen()
        self.pen_found.setColor(QColor(0, 255, 0))
        self.start: QPoint = QPoint(0, 0)
        self.end: QPoint = QPoint(720, 360)
        self.rect_: QRect = QRect()
        self.template_img: str = ""
        self.color_mode: ColorType = ColorType.COLOR
        self.img_widget: WidgetIMG = None

        self.setupUi(self)
        # self.graphicsView = View(self.frame_2)
        self.setWindowTitle(f"画像認識コマンド生成補助ツール")
        layout = QHBoxLayout()
        layout.addWidget(self)
        self.setLayout(layout)
        self.pushButtonLoadIMG.pressed.connect(self.create_scene)

        self.radioGroup = QButtonGroup(self)
        self.radioGroup.addButton(self.radioButton, ColorType.COLOR.value)
        self.radioGroup.addButton(self.radioButton_2, ColorType.GRAY.value)
        self.radioGroup.addButton(self.radioButton_3, ColorType.BINARY.value)
        self.radioGroup.buttonClicked.connect(self.img_color_setting)

        self.horizontalSliderThreshold.valueChanged.connect(lambda: self.create_scene(get_img=False))
        self.checkBoxSetOtsu.stateChanged.connect(lambda: self.create_scene(get_img=False))
        self.pushButtonLoadTemplate.pressed.connect(self.load_template_image)
        self.pushButtonSaveImg.pressed.connect(self.save_select_area)
        self.horizontalSlider.valueChanged.connect(self.set_slide_bar_to_threshold)
        self.doubleSpinBox.valueChanged.connect(self.set_threshold_to_slide_bar)
        self.pushButtonGenerate.pressed.connect(self.generate_matching_command)
        self.toolButton.pressed.connect(self.set_img_from_file)

    def create_scene(self, prev_image=None, get_img=True):
        if get_img:
            self.get_image.emit()
        if prev_image is not None:
            self.image = prev_image
        else:
            self.frame = self.image
        if self.image is None:
            self.warning("画像を読み込んでください")
            return

        if self.pixmap_mode == "Color":
            h, w, ch = self.image.shape
            bytes_per_line = ch * w
            self.match_img = self.image
            self.show_image = QImage(self.image, w, h, bytes_per_line, QImage.Format.Format_BGR888)
            pass
        elif self.pixmap_mode == "Gray Scale":
            self.show_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            h, w = self.show_image.shape
            self.match_img = self.show_image
            self.show_image = QImage(self.show_image, w, h, QImage.Format.Format_Grayscale8)
        elif self.pixmap_mode == "Binarization":
            self.show_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            h, w = self.show_image.shape

            if self.checkBoxSetOtsu.isChecked():
                # self.debug("Auto has selected")
                self.threshold, self.show_image = cv2.threshold(self.show_image, 0, 255, cv2.THRESH_OTSU)
                self.match_img = self.show_image
                self.show_image = QImage(self.show_image, w, h, QImage.Format.Format_Indexed8)
                self.horizontalSliderThreshold.setValue(int(self.threshold))
            else:
                # self.debug("Slider value has selected")
                self.threshold = self.horizontalSliderThreshold.value()
                self.threshold, self.show_image = cv2.threshold(self.show_image, self.threshold, 255, cv2.THRESH_BINARY)
                self.match_img = self.show_image
                self.show_image = QImage(self.show_image, w, h, QImage.Format.Format_Indexed8)

        # create scene
        self.scene = QtWidgets.QGraphicsScene()
        self.pixmap = QtGui.QPixmap.fromImage(self.show_image)
        self.pixmap = self.pixmap.scaled(640, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.start = self.graphicsView.start
        self.end = self.graphicsView.end
        # self.debug(f"lefttop = {self.start.x()},{self.start.y()}, bottomright = {self.end.x()},{self.end.y()}")
        self.scene.addPixmap(self.pixmap)
        try:
            self.rect_ = (QRectF(self.start, self.end))
            ret = self.scene.addRect(self.rect_, self.pen)
            self.graphicsView.rect = ret
        except Exception:
            pass

        self.assign_scene_to_graphics_view()
        try:
            self.template_matching()
        except AttributeError:
            self.warning("テンプレートを読み込んでください")

    def assign_scene_to_graphics_view(self):
        self.graphicsView.setScene(self.scene)
        self.graphicsView.show()

    def img_color_setting(self, _):
        # self.debug(pathlib.Path.cwd())
        self.graphicsView.remove_object()
        # color_select = self.sender()
        # if color_select.isChecked():
        #     self.debug(color_select.text())
        match ColorType(self.radioGroup.checkedId()):
            case ColorType.COLOR:
                self.color_mode = ColorType.COLOR
                self.pixmap_mode = "Color"
            case ColorType.GRAY:
                self.color_mode = ColorType.GRAY
                self.pixmap_mode = "Gray Scale"
            case ColorType.BINARY:
                self.color_mode = ColorType.BINARY
                self.pixmap_mode = "Binarization"
        self.create_scene(get_img=False)

    def set_binarization_threshold(self, *args):
        self.show_binarization_threshold()

    def show_binarization_threshold(self):
        self.debug(self.threshold)

    def set_threshold_to_slide_bar(self):
        self.horizontalSlider.setValue(int(self.doubleSpinBox.value() * 100))

    def set_slide_bar_to_threshold(self):
        self.doubleSpinBox.setValue(self.horizontalSlider.value() / 100)
        self.create_scene(get_img=False)

    def generate_matching_command(self):
        try:
            if self.color_mode != ColorType.BINARY:
                self.plainTextEdit_2.appendPlainText(
                    f"self.is_contain_template("
                    f"template_path=pathlib.Path(r'{pathlib.Path(self.template_img).relative_to(pathlib.Path.cwd())}'), "
                    f"threshold={float(self.doubleSpinBox.value())}, "
                    f"color_mode={self.color_mode}, "
                    f"trim={[self.left_top_x, self.left_top_y, self.right_bottom_x, self.right_bottom_y]}"
                    f")")
            else:
                self.plainTextEdit_2.appendPlainText(
                    f"self.is_contain_template("
                    f"template_path=pathlib.Path(r'{pathlib.Path(self.template_img).relative_to(pathlib.Path.cwd())}'), "
                    f"threshold={float(self.doubleSpinBox.value())}, "
                    f"color_mode={self.color_mode}, "
                    f"binary_threshold={self.horizontalSliderThreshold.value()}, "
                    f"trim={[self.left_top_x, self.left_top_y, self.right_bottom_x, self.right_bottom_y]}"
                    f")")

        except ValueError:
            self.error("画像が読み込まれていない可能性があります")

    def set_img_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Open file', str(pathlib.Path.cwd()),
                                                   "Image files (*.png)")
        if file_path != "":
            self.set_mat_image(file_path)
        else:
            self.debug("読み込みをキャンセルしました")

    def set_mat_image(self, file_path):
        self.image = cv2.imread(file_path)
        self.create_scene(get_img=False)

    def load_template_image(self):
        _img, _ = QFileDialog.getOpenFileName(self, 'Open file', str(pathlib.Path.cwd()),
                                              "Image files (*.png)")
        if _img != "":
            self.set_template_image(_img)
            self.create_scene(get_img=False)
            self.debug(pathlib.Path(self.template_img).relative_to(pathlib.Path.cwd()))
            self.img_widget = WidgetIMG(pathlib.Path(_img))
            self.img_widget.show()
        else:
            self.debug("読み込みをキャンセルしました")

    def set_template_image(self, img):
        self.template_img = img

    def save_select_area(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save file",
                                                   str(pathlib.Path.cwd()),
                                                   "Image files (*.png)")
        self.debug(file_path)
        if file_path != "" and self.start != QPoint() and self.end != QPoint():
            ret = self.save_cv_image(file_path)

        else:
            self.debug("画像の保存に失敗しました")

        ret = QMessageBox.question(self, "Confirm", "保存した画像をテンプレートとして利用しますか？",
                                   QMessageBox.Ok, QMessageBox.Cancel)
        if ret:
            self.set_template_image(file_path)
            self.create_scene(get_img=False)

    def template_matching(self):
        src = self.match_img

        src_w = 1280
        src_h = 720
        self.left_top_x = 0
        self.right_bottom_x = 1280
        self.left_top_y = 0
        self.right_bottom_y = 720
        if self.start != QPoint() and self.end != QPoint():
            self.left_top_x = int(min(self.start.x(), self.end.x()) * 2)
            self.right_bottom_x = int(max(self.start.x(), self.end.x()) * 2)
            self.left_top_y = int(min(self.start.y(), self.end.y()) * 2)
            self.right_bottom_y = int(max(self.start.y(), self.end.y()) * 2)
            src = src[self.left_top_y:self.right_bottom_y, self.left_top_x:self.right_bottom_x]
            src_w = self.right_bottom_x - self.left_top_x
            src_h = self.right_bottom_y - self.left_top_y
        if self.template_img == "":
            self.warning("テンプレートを読み込んでください")
            return
        template = cv2.imread(self.template_img)

        if self.pixmap_mode == "Color":
            _template = template
        elif self.pixmap_mode == "Gray Scale":
            _template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        elif self.pixmap_mode == "Binarization":
            _template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            if self.checkBoxSetOtsu.isChecked():
                # self.debug("Auto has selected")
                _, _template = cv2.threshold(_template, 0, 255, cv2.THRESH_OTSU)
            else:
                _, _template = cv2.threshold(_template, self.threshold, 255, cv2.THRESH_BINARY)
        else:
            _template = template

        # print(src_w, src_h)

        w, h = _template.shape[1], _template.shape[0]
        if w > src_w or h > src_h:
            self.error("テンプレート画像が選択範囲より大きいため画像認識できません")
            return

        method = cv2.TM_CCOEFF_NORMED
        res = cv2.matchTemplate(src, _template, method)

        positions = np.where(res >= self.doubleSpinBox.value())
        scores = res[positions]
        boxes = []
        for y, x in zip(*positions):
            boxes.append([self.left_top_x + x, self.left_top_y + y,
                          self.left_top_x + x + w - 1, self.left_top_y + y + h - 1])
        boxes = np.array(boxes)
        boxes = self.non_max_suppression(boxes, scores, overlap_thresh=0.8)

        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        self.lineEditMatch.setText(str(round(max_val, 2)))
        self.lineEditCoordinate.setText(str(max_loc))
        found = []
        for i in range(box_n := len(boxes)):
            # self.debug(boxes[i])
            _h, _j, _n, _m = boxes[i]
            found_rect = QRect(QPoint(_h // 2, _j // 2), QSize(w // 2, h // 2))
            found.append(self.scene.addRect(found_rect, self.pen_found))
        self.lineEditMatchNum.setText(str(box_n))

    @staticmethod
    def non_max_suppression(boxes: np.ndarray, scores: np.ndarray, overlap_thresh: float) -> np.ndarray:
        """
        https://pystyle.info/opencv-non-maximum-suppression/ を参考にしました。
        Non Maximum Suppression (NMS) を行う。

        Args:
            scores: 画像認識の結果(一致率)
            boxes: (N, 4) の numpy 配列。矩形の一覧。
            overlap_thresh: [0, 1] の実数。閾値。

        Returns:
            boxes : (M, 4) の numpy 配列。Non Maximum Suppression処理後の矩形の一覧。
        """
        if len(boxes) <= 1:
            return boxes

        # float 型に変換する。
        boxes = boxes.astype("float")

        # (NumBoxes, 4) の numpy 配列を x1, y1, x2, y2 の一覧を表す4つの (NumBoxes, 1) の numpy 配列に分割する。
        x1, y1, x2, y2 = np.squeeze(np.split(boxes, 4, axis=1))

        # 矩形の面積を計算する。
        area = (x2 - x1 + 1) * (y2 - y1 + 1)

        indices = np.argsort(scores)  # スコアを降順にソートしたインデックス一覧
        selected = []  # NMS により選択されたインデックス一覧

        # indices がなくなるまでループする。
        while len(indices) > 0:
            # indices は降順にソートされているので、最後の要素の値 (インデックス) が
            # 残っている中で最もスコアが高い。
            last = len(indices) - 1

            selected_index = indices[last]
            remaining_indices = indices[:last]
            selected.append(selected_index)

            # 選択した短形と残りの短形の共通部分の x1, y1, x2, y2 を計算する。
            i_x1 = np.maximum(x1[selected_index], x1[remaining_indices])
            i_y1 = np.maximum(y1[selected_index], y1[remaining_indices])
            i_x2 = np.minimum(x2[selected_index], x2[remaining_indices])
            i_y2 = np.minimum(y2[selected_index], y2[remaining_indices])

            # 選択した短形と残りの短形の共通部分の幅及び高さを計算する。
            # 共通部分がない場合は、幅や高さは負の値になるので、その場合、幅や高さは 0 とする。
            i_w = np.maximum(0, i_x2 - i_x1 + 1)
            i_h = np.maximum(0, i_y2 - i_y1 + 1)

            # 選択した短形と残りの短形の Overlap Ratio を計算する。
            overlap = (i_w * i_h) / area[remaining_indices]

            # 選択した短形及び Overlap Ratio が閾値以上の短形を indices から削除する。
            indices = np.delete(
                indices, np.concatenate(([last], np.where(overlap > overlap_thresh)[0]))
            )

        # 選択された短形の一覧を返す。
        return boxes[selected].astype("int")

    def save_cv_image(self, filename: pathlib.Path, params: Optional = None) -> bool:
        try:
            img = self.image[self.left_top_y:self.right_bottom_y, self.left_top_x:self.right_bottom_x]
            result, n = cv2.imencode(".png", img, params)

            if result:
                with open(filename, mode="w+b") as f:
                    n.tofile(f)
                return True
            else:
                return False
        except Exception as e:
            print(e)
            self.error(f"Image Write Error: {e}")
        return False

    # ログをメインに飛ばすため
    def debug(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.DEBUG)

    def info(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.INFO)

    def warning(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.WARNING)

    def error(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.ERROR)

    def critical(self, s: any, force=False):
        if force or not self.__isCanceled:
            s = f"thread id={threading.get_ident()} " + str(s)
            self.print_strings.emit(s, logging.CRITICAL)


# PySide6のアプリ本体（ユーザがコーディングしていく部分）
class WidgetIMG(QWidget):
    def __init__(self, path, parent=None):
        # 親クラスの初期化
        super().__init__(parent)
        self.label = None
        self.start = None
        self.end = None
        self.movement = None
        self.pressing = None
        self.processing = False

        # ウィンドウタイトル
        self.setWindowTitle("Image")
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        ret = self.set_label(path)
        if ret:
            self.layout.addWidget(self.label)

    def set_label(self, path: pathlib.Path):
        try:
            # ラベルを使うことを宣言
            self.label = QLabel(self)
            self.label.setAlignment(Qt.AlignCenter)

            # 画像の読み込み
            image = QPixmap(path)

            # 画像サイズの変更
            width = image.size().width() / 2  # 横幅を半分に
            height = image.size().height() / 2  # 高さを半分に
            image = image.scaled(width, height)  # 読み込んだ画像のサイズを変更
            # self.resize(max(100, width), max(100, height))
            self.setFixedSize(max(100, width) + 20, max(100, height) + 20)

            # ラベルに画像を指定
            self.label.setPixmap(image)
            return True
        except Exception:
            return False

    def mousePressEvent(self, event):
        if not self.processing:
            self.start = self.mapToGlobal(event.pos())
            self.pressing = True

    def mouseMoveEvent(self, event):
        print(self.start, self.end)
        if self.pressing and not self.processing:
            self.processing = True
            self.end = self.mapToGlobal(event.pos())
            self.movement = self.end - self.start
            self.setGeometry(self.mapToGlobal(self.movement).x(),
                             self.mapToGlobal(self.movement).y(),
                             self.width(),
                             self.height())
            self.start = self.end
            self.processing = False

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False
