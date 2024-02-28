# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'template_match_support.ui'
##
## Created by: Qt User Interface Compiler version 6.3.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QAbstractSpinBox, QApplication, QCheckBox,
    QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QRadioButton, QSizePolicy, QSlider, QSpacerItem,
    QSpinBox, QToolButton, QVBoxLayout, QWidget)

from ui.graphic_view_template import View

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.setWindowModality(Qt.NonModal)
        Form.resize(800, 600)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(800, 600))
        Form.setMaximumSize(QSize(800, 600))
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.frame_9 = QFrame(self.frame)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setFrameShape(QFrame.StyledPanel)
        self.frame_9.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_9)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.pushButtonLoadIMG = QPushButton(self.frame_9)
        self.pushButtonLoadIMG.setObjectName(u"pushButtonLoadIMG")

        self.horizontalLayout_5.addWidget(self.pushButtonLoadIMG)

        self.toolButton = QToolButton(self.frame_9)
        self.toolButton.setObjectName(u"toolButton")

        self.horizontalLayout_5.addWidget(self.toolButton)


        self.verticalLayout_3.addWidget(self.frame_9)

        self.pushButtonReset = QPushButton(self.frame)
        self.pushButtonReset.setObjectName(u"pushButtonReset")

        self.verticalLayout_3.addWidget(self.pushButtonReset)

        self.frame_5 = QFrame(self.frame)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_5)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.radioButton = QRadioButton(self.frame_5)
        self.radioButton.setObjectName(u"radioButton")
        self.radioButton.setChecked(True)

        self.verticalLayout_2.addWidget(self.radioButton)

        self.radioButton_2 = QRadioButton(self.frame_5)
        self.radioButton_2.setObjectName(u"radioButton_2")

        self.verticalLayout_2.addWidget(self.radioButton_2)

        self.radioButton_3 = QRadioButton(self.frame_5)
        self.radioButton_3.setObjectName(u"radioButton_3")

        self.verticalLayout_2.addWidget(self.radioButton_3)

        self.frame_8 = QFrame(self.frame_5)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setFrameShape(QFrame.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_4 = QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_4)

        self.checkBoxSetOtsu = QCheckBox(self.frame_8)
        self.checkBoxSetOtsu.setObjectName(u"checkBoxSetOtsu")
        self.checkBoxSetOtsu.setEnabled(False)
        self.checkBoxSetOtsu.setToolTipDuration(1)

        self.horizontalLayout_4.addWidget(self.checkBoxSetOtsu)


        self.verticalLayout_2.addWidget(self.frame_8)

        self.frame_6 = QFrame(self.frame_5)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_2 = QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.spinBoxThreshold = QSpinBox(self.frame_6)
        self.spinBoxThreshold.setObjectName(u"spinBoxThreshold")
        self.spinBoxThreshold.setEnabled(False)
        self.spinBoxThreshold.setAlignment(Qt.AlignCenter)
        self.spinBoxThreshold.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.spinBoxThreshold.setProperty("showGroupSeparator", False)
        self.spinBoxThreshold.setMaximum(255)
        self.spinBoxThreshold.setValue(128)

        self.horizontalLayout_2.addWidget(self.spinBoxThreshold)


        self.verticalLayout_2.addWidget(self.frame_6)

        self.frame_7 = QFrame(self.frame_5)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_3 = QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)

        self.horizontalSliderThreshold = QSlider(self.frame_7)
        self.horizontalSliderThreshold.setObjectName(u"horizontalSliderThreshold")
        self.horizontalSliderThreshold.setEnabled(False)
        self.horizontalSliderThreshold.setMaximum(255)
        self.horizontalSliderThreshold.setValue(128)
        self.horizontalSliderThreshold.setOrientation(Qt.Horizontal)

        self.horizontalLayout_3.addWidget(self.horizontalSliderThreshold)


        self.verticalLayout_2.addWidget(self.frame_7)

        self.frame_8.raise_()
        self.radioButton.raise_()
        self.radioButton_2.raise_()
        self.radioButton_3.raise_()
        self.frame_6.raise_()
        self.frame_7.raise_()

        self.verticalLayout_3.addWidget(self.frame_5)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.pushButtonSaveImg = QPushButton(self.frame)
        self.pushButtonSaveImg.setObjectName(u"pushButtonSaveImg")

        self.verticalLayout_3.addWidget(self.pushButtonSaveImg)

        self.pushButtonLoadTemplate = QPushButton(self.frame)
        self.pushButtonLoadTemplate.setObjectName(u"pushButtonLoadTemplate")

        self.verticalLayout_3.addWidget(self.pushButtonLoadTemplate)

        self.pushButtonGenerate = QPushButton(self.frame)
        self.pushButtonGenerate.setObjectName(u"pushButtonGenerate")
        self.pushButtonGenerate.setAutoDefault(True)
        self.pushButtonGenerate.setFlat(False)

        self.verticalLayout_3.addWidget(self.pushButtonGenerate)


        self.gridLayout.addWidget(self.frame, 0, 2, 1, 1)

        self.frame_2 = QFrame(Form)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(640, 360))
        self.frame_2.setMaximumSize(QSize(640, 360))
        self.frame_2.setFrameShape(QFrame.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Plain)
        self.verticalLayout = QVBoxLayout(self.frame_2)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.graphicsView = View(self.frame_2)
        self.graphicsView.setObjectName(u"graphicsView")
        self.graphicsView.setMinimumSize(QSize(640, 36))
        self.graphicsView.setMaximumSize(QSize(640, 360))
        self.graphicsView.viewport().setProperty("cursor", QCursor(Qt.CrossCursor))
        self.graphicsView.setFrameShape(QFrame.NoFrame)
        self.graphicsView.setFrameShadow(QFrame.Plain)
        self.graphicsView.setLineWidth(0)
        self.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        self.verticalLayout.addWidget(self.graphicsView)


        self.gridLayout.addWidget(self.frame_2, 0, 0, 1, 2)

        self.frame_3 = QFrame(Form)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Sunken)
        self.gridLayout_2 = QGridLayout(self.frame_3)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(9, 0, -1, -1)
        self.plainTextEdit_2 = QPlainTextEdit(self.frame_3)
        self.plainTextEdit_2.setObjectName(u"plainTextEdit_2")
        self.plainTextEdit_2.setMinimumSize(QSize(764, 132))
        self.plainTextEdit_2.setReadOnly(True)
        self.plainTextEdit_2.setBackgroundVisible(False)

        self.gridLayout_2.addWidget(self.plainTextEdit_2, 1, 0, 1, 1)

        self.frame_4 = QFrame(self.frame_3)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_4)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.frame_4)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.doubleSpinBox = QDoubleSpinBox(self.frame_4)
        self.doubleSpinBox.setObjectName(u"doubleSpinBox")
        self.doubleSpinBox.setMaximum(1.000000000000000)
        self.doubleSpinBox.setSingleStep(0.010000000000000)
        self.doubleSpinBox.setValue(0.800000000000000)

        self.horizontalLayout.addWidget(self.doubleSpinBox)

        self.horizontalSlider = QSlider(self.frame_4)
        self.horizontalSlider.setObjectName(u"horizontalSlider")
        self.horizontalSlider.setMaximumSize(QSize(50, 16777215))
        self.horizontalSlider.setMaximum(100)
        self.horizontalSlider.setSingleStep(1)
        self.horizontalSlider.setPageStep(1)
        self.horizontalSlider.setValue(80)
        self.horizontalSlider.setOrientation(Qt.Horizontal)

        self.horizontalLayout.addWidget(self.horizontalSlider)

        self.line = QFrame(self.frame_4)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.VLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.labelMatch = QLabel(self.frame_4)
        self.labelMatch.setObjectName(u"labelMatch")

        self.horizontalLayout.addWidget(self.labelMatch)

        self.lineEditMatch = QLineEdit(self.frame_4)
        self.lineEditMatch.setObjectName(u"lineEditMatch")
        self.lineEditMatch.setMinimumSize(QSize(80, 22))
        self.lineEditMatch.setMaximumSize(QSize(80, 16777215))

        self.horizontalLayout.addWidget(self.lineEditMatch)

        self.labelCoordinate = QLabel(self.frame_4)
        self.labelCoordinate.setObjectName(u"labelCoordinate")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.labelCoordinate.sizePolicy().hasHeightForWidth())
        self.labelCoordinate.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.labelCoordinate)

        self.lineEditCoordinate = QLineEdit(self.frame_4)
        self.lineEditCoordinate.setObjectName(u"lineEditCoordinate")
        self.lineEditCoordinate.setMaximumSize(QSize(80, 16777215))

        self.horizontalLayout.addWidget(self.lineEditCoordinate)

        self.labelMatchNumber = QLabel(self.frame_4)
        self.labelMatchNumber.setObjectName(u"labelMatchNumber")

        self.horizontalLayout.addWidget(self.labelMatchNumber)

        self.lineEditMatchNum = QLineEdit(self.frame_4)
        self.lineEditMatchNum.setObjectName(u"lineEditMatchNum")
        self.lineEditMatchNum.setMaximumSize(QSize(80, 16777215))

        self.horizontalLayout.addWidget(self.lineEditMatchNum)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.gridLayout_2.addWidget(self.frame_4, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.frame_3, 1, 0, 1, 3)


        self.retranslateUi(Form)
        self.spinBoxThreshold.valueChanged.connect(self.horizontalSliderThreshold.setValue)
        self.horizontalSliderThreshold.valueChanged.connect(self.spinBoxThreshold.setValue)
        self.checkBoxSetOtsu.toggled.connect(self.spinBoxThreshold.setDisabled)
        self.checkBoxSetOtsu.toggled.connect(self.horizontalSliderThreshold.setDisabled)
        self.radioButton_3.toggled.connect(self.checkBoxSetOtsu.setEnabled)
        self.radioButton_3.toggled.connect(self.spinBoxThreshold.setEnabled)
        self.radioButton_3.toggled.connect(self.horizontalSliderThreshold.setEnabled)

        self.pushButtonGenerate.setDefault(True)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.pushButtonLoadIMG.setText(QCoreApplication.translate("Form", u"\u753b\u50cf\u8aad\u307f\u8fbc\u307f", None))
        self.toolButton.setText(QCoreApplication.translate("Form", u"...", None))
        self.pushButtonReset.setText(QCoreApplication.translate("Form", u"\u30ea\u30bb\u30c3\u30c8", None))
        self.radioButton.setText(QCoreApplication.translate("Form", u"Color", None))
        self.radioButton_2.setText(QCoreApplication.translate("Form", u"Gray Scale", None))
        self.radioButton_3.setText(QCoreApplication.translate("Form", u"Binarization", None))
#if QT_CONFIG(tooltip)
        self.checkBoxSetOtsu.setToolTip(QCoreApplication.translate("Form", u"\u5927\u6d25\u6cd5", None))
#endif // QT_CONFIG(tooltip)
        self.checkBoxSetOtsu.setText(QCoreApplication.translate("Form", u"Auto", None))
        self.spinBoxThreshold.setSuffix("")
        self.spinBoxThreshold.setPrefix("")
        self.pushButtonSaveImg.setText(QCoreApplication.translate("Form", u"\u9078\u629e\u7bc4\u56f2\u3092\u4fdd\u5b58", None))
        self.pushButtonLoadTemplate.setText(QCoreApplication.translate("Form", u"\u30c6\u30f3\u30d7\u30ec\u30fc\u30c8\u8aad\u8fbc", None))
        self.pushButtonGenerate.setText(QCoreApplication.translate("Form", u"\u30b3\u30de\u30f3\u30c9\u751f\u6210", None))
        self.plainTextEdit_2.setPlainText("")
        self.plainTextEdit_2.setPlaceholderText(QCoreApplication.translate("Form", u"\u751f\u6210\u30b3\u30de\u30f3\u30c9\u306e\u8868\u793a\u67a0", None))
        self.label.setText(QCoreApplication.translate("Form", u"\u95be\u5024", None))
        self.labelMatch.setText(QCoreApplication.translate("Form", u"\u4e00\u81f4\u7387", None))
        self.labelCoordinate.setText(QCoreApplication.translate("Form", u"\u5ea7\u6a19", None))
        self.labelMatchNumber.setText(QCoreApplication.translate("Form", u"\u4e00\u81f4\u6570", None))
    # retranslateUi

