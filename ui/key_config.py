# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'key_config.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(690, 337)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QSize(690, 0))
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.frame_2 = QFrame(Form)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(325, 287))
        self.frame_2.setMaximumSize(QSize(325, 287))
        self.frame_2.setFrameShape(QFrame.NoFrame)
        self.gridLayout_3 = QGridLayout(self.frame_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.lineEdit_12 = QLineEdit(self.frame_2)
        self.lineEdit_12.setObjectName(u"lineEdit_12")
        self.lineEdit_12.setEnabled(False)
        self.lineEdit_12.setMinimumSize(QSize(100, 0))
        self.lineEdit_12.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_12.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_12.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_12, 6, 6, 1, 1)

        self.checkBox_22 = QCheckBox(self.frame_2)
        self.checkBox_22.setObjectName(u"checkBox_22")

        self.gridLayout_3.addWidget(self.checkBox_22, 0, 5, 1, 2)

        self.pushButton_12 = QPushButton(self.frame_2)
        self.pushButton_12.setObjectName(u"pushButton_12")
        self.pushButton_12.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_12, 6, 5, 1, 1)

        self.pushButton_18 = QPushButton(self.frame_2)
        self.pushButton_18.setObjectName(u"pushButton_18")
        self.pushButton_18.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_18, 17, 5, 1, 1)

        self.label_10 = QLabel(self.frame_2)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_10, 17, 3, 1, 1)

        self.lineEdit_17 = QLineEdit(self.frame_2)
        self.lineEdit_17.setObjectName(u"lineEdit_17")
        self.lineEdit_17.setEnabled(False)
        self.lineEdit_17.setMinimumSize(QSize(100, 0))
        self.lineEdit_17.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_17.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_17.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_17, 15, 6, 1, 1)

        self.label_15 = QLabel(self.frame_2)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_15, 11, 3, 1, 1)

        self.label_11 = QLabel(self.frame_2)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_11, 8, 3, 1, 1)

        self.lineEdit_13 = QLineEdit(self.frame_2)
        self.lineEdit_13.setObjectName(u"lineEdit_13")
        self.lineEdit_13.setEnabled(False)
        self.lineEdit_13.setMinimumSize(QSize(100, 0))
        self.lineEdit_13.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_13.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_13.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_13, 8, 6, 1, 1)

        self.lineEdit_15 = QLineEdit(self.frame_2)
        self.lineEdit_15.setObjectName(u"lineEdit_15")
        self.lineEdit_15.setEnabled(False)
        self.lineEdit_15.setMinimumSize(QSize(100, 0))
        self.lineEdit_15.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_15.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_15.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_15, 13, 6, 1, 1)

        self.label_17 = QLabel(self.frame_2)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_17, 14, 3, 1, 1)

        self.lineEdit_16 = QLineEdit(self.frame_2)
        self.lineEdit_16.setObjectName(u"lineEdit_16")
        self.lineEdit_16.setEnabled(False)
        self.lineEdit_16.setMinimumSize(QSize(100, 0))
        self.lineEdit_16.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_16.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_16.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_16, 14, 6, 1, 1)

        self.lineEdit_10 = QLineEdit(self.frame_2)
        self.lineEdit_10.setObjectName(u"lineEdit_10")
        self.lineEdit_10.setEnabled(False)
        self.lineEdit_10.setMinimumSize(QSize(100, 0))
        self.lineEdit_10.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_10.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_10.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_10, 2, 6, 1, 1)

        self.pushButton_15 = QPushButton(self.frame_2)
        self.pushButton_15.setObjectName(u"pushButton_15")
        self.pushButton_15.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_15, 13, 5, 1, 1)

        self.pushButton_11 = QPushButton(self.frame_2)
        self.pushButton_11.setObjectName(u"pushButton_11")
        self.pushButton_11.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_11, 4, 5, 1, 1)

        self.pushButton_13 = QPushButton(self.frame_2)
        self.pushButton_13.setObjectName(u"pushButton_13")
        self.pushButton_13.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_13, 8, 5, 1, 1)

        self.label_14 = QLabel(self.frame_2)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_14, 13, 3, 1, 1)

        self.pushButton_14 = QPushButton(self.frame_2)
        self.pushButton_14.setObjectName(u"pushButton_14")
        self.pushButton_14.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_14, 11, 5, 1, 1)

        self.label_13 = QLabel(self.frame_2)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_13, 2, 3, 1, 1)

        self.pushButton_10 = QPushButton(self.frame_2)
        self.pushButton_10.setObjectName(u"pushButton_10")
        self.pushButton_10.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_10, 2, 5, 1, 1)

        self.checkBox_14 = QCheckBox(self.frame_2)
        self.checkBox_14.setObjectName(u"checkBox_14")

        self.gridLayout_3.addWidget(self.checkBox_14, 11, 2, 1, 1, Qt.AlignHCenter)

        self.pushButton_17 = QPushButton(self.frame_2)
        self.pushButton_17.setObjectName(u"pushButton_17")
        self.pushButton_17.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_17, 15, 5, 1, 1)

        self.label_12 = QLabel(self.frame_2)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_12, 4, 3, 1, 1)

        self.lineEdit_11 = QLineEdit(self.frame_2)
        self.lineEdit_11.setObjectName(u"lineEdit_11")
        self.lineEdit_11.setEnabled(False)
        self.lineEdit_11.setMinimumSize(QSize(100, 0))
        self.lineEdit_11.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_11.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_11.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_11, 4, 6, 1, 1)

        self.lineEdit_14 = QLineEdit(self.frame_2)
        self.lineEdit_14.setObjectName(u"lineEdit_14")
        self.lineEdit_14.setEnabled(False)
        self.lineEdit_14.setMinimumSize(QSize(100, 0))
        self.lineEdit_14.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_14.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_14.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_14, 11, 6, 1, 1)

        self.label_16 = QLabel(self.frame_2)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_16, 6, 3, 1, 1)

        self.pushButton_16 = QPushButton(self.frame_2)
        self.pushButton_16.setObjectName(u"pushButton_16")
        self.pushButton_16.setEnabled(False)

        self.gridLayout_3.addWidget(self.pushButton_16, 14, 5, 1, 1)

        self.label_18 = QLabel(self.frame_2)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_18, 15, 3, 1, 1)

        self.checkBox_20 = QCheckBox(self.frame_2)
        self.checkBox_20.setObjectName(u"checkBox_20")

        self.gridLayout_3.addWidget(self.checkBox_20, 0, 2, 1, 1)

        self.lineEdit_18 = QLineEdit(self.frame_2)
        self.lineEdit_18.setObjectName(u"lineEdit_18")
        self.lineEdit_18.setEnabled(False)
        self.lineEdit_18.setMinimumSize(QSize(100, 0))
        self.lineEdit_18.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_18.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_18.setReadOnly(True)

        self.gridLayout_3.addWidget(self.lineEdit_18, 17, 6, 1, 1)

        self.checkBox_12 = QCheckBox(self.frame_2)
        self.checkBox_12.setObjectName(u"checkBox_12")

        self.gridLayout_3.addWidget(self.checkBox_12, 6, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_10 = QCheckBox(self.frame_2)
        self.checkBox_10.setObjectName(u"checkBox_10")

        self.gridLayout_3.addWidget(self.checkBox_10, 2, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_11 = QCheckBox(self.frame_2)
        self.checkBox_11.setObjectName(u"checkBox_11")

        self.gridLayout_3.addWidget(self.checkBox_11, 4, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_13 = QCheckBox(self.frame_2)
        self.checkBox_13.setObjectName(u"checkBox_13")

        self.gridLayout_3.addWidget(self.checkBox_13, 8, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_18 = QCheckBox(self.frame_2)
        self.checkBox_18.setObjectName(u"checkBox_18")

        self.gridLayout_3.addWidget(self.checkBox_18, 17, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_17 = QCheckBox(self.frame_2)
        self.checkBox_17.setObjectName(u"checkBox_17")

        self.gridLayout_3.addWidget(self.checkBox_17, 15, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_16 = QCheckBox(self.frame_2)
        self.checkBox_16.setObjectName(u"checkBox_16")

        self.gridLayout_3.addWidget(self.checkBox_16, 14, 2, 1, 1, Qt.AlignHCenter)

        self.checkBox_15 = QCheckBox(self.frame_2)
        self.checkBox_15.setObjectName(u"checkBox_15")

        self.gridLayout_3.addWidget(self.checkBox_15, 13, 2, 1, 1, Qt.AlignHCenter)


        self.gridLayout.addWidget(self.frame_2, 0, 2, 1, 1, Qt.AlignHCenter|Qt.AlignVCenter)

        self.line = QFrame(Form)
        self.line.setObjectName(u"line")
        self.line.setMinimumSize(QSize(5, 0))
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setLineWidth(1)
        self.line.setFrameShape(QFrame.VLine)

        self.gridLayout.addWidget(self.line, 0, 1, 1, 1, Qt.AlignHCenter)

        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(325, 287))
        self.frame.setMaximumSize(QSize(325, 287))
        self.gridLayout_2 = QGridLayout(self.frame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.pushButton = QPushButton(self.frame)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton, 1, 3, 1, 1)

        self.pushButton_3 = QPushButton(self.frame)
        self.pushButton_3.setObjectName(u"pushButton_3")
        self.pushButton_3.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_3, 3, 3, 1, 1)

        self.lineEdit_7 = QLineEdit(self.frame)
        self.lineEdit_7.setObjectName(u"lineEdit_7")
        self.lineEdit_7.setEnabled(False)
        self.lineEdit_7.setMinimumSize(QSize(100, 0))
        self.lineEdit_7.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_7.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_7.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_7, 7, 4, 1, 1)

        self.lineEdit_9 = QLineEdit(self.frame)
        self.lineEdit_9.setObjectName(u"lineEdit_9")
        self.lineEdit_9.setEnabled(False)
        self.lineEdit_9.setMinimumSize(QSize(100, 0))
        self.lineEdit_9.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_9.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_9.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_9, 9, 4, 1, 1)

        self.checkBox_9 = QCheckBox(self.frame)
        self.checkBox_9.setObjectName(u"checkBox_9")

        self.gridLayout_2.addWidget(self.checkBox_9, 9, 0, 1, 1, Qt.AlignHCenter)

        self.checkBox_3 = QCheckBox(self.frame)
        self.checkBox_3.setObjectName(u"checkBox_3")

        self.gridLayout_2.addWidget(self.checkBox_3, 3, 0, 1, 1, Qt.AlignHCenter)

        self.checkBox = QCheckBox(self.frame)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_2.addWidget(self.checkBox, 1, 0, 1, 1, Qt.AlignHCenter)

        self.lineEdit = QLineEdit(self.frame)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setEnabled(False)
        self.lineEdit.setMinimumSize(QSize(100, 0))
        self.lineEdit.setMaximumSize(QSize(100, 16777215))
        self.lineEdit.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit, 1, 4, 1, 1)

        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_2, 2, 1, 1, 1)

        self.lineEdit_3 = QLineEdit(self.frame)
        self.lineEdit_3.setObjectName(u"lineEdit_3")
        self.lineEdit_3.setEnabled(False)
        self.lineEdit_3.setMinimumSize(QSize(100, 0))
        self.lineEdit_3.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_3.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_3.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_3, 3, 4, 1, 1)

        self.pushButton_4 = QPushButton(self.frame)
        self.pushButton_4.setObjectName(u"pushButton_4")
        self.pushButton_4.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_4, 4, 3, 1, 1)

        self.lineEdit_4 = QLineEdit(self.frame)
        self.lineEdit_4.setObjectName(u"lineEdit_4")
        self.lineEdit_4.setEnabled(False)
        self.lineEdit_4.setMinimumSize(QSize(100, 0))
        self.lineEdit_4.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_4.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_4.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_4, 4, 4, 1, 1)

        self.lineEdit_8 = QLineEdit(self.frame)
        self.lineEdit_8.setObjectName(u"lineEdit_8")
        self.lineEdit_8.setEnabled(False)
        self.lineEdit_8.setMinimumSize(QSize(100, 0))
        self.lineEdit_8.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_8.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_8.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_8, 8, 4, 1, 1)

        self.label_6 = QLabel(self.frame)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_6, 6, 1, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_5, 5, 1, 1, 1)

        self.pushButton_5 = QPushButton(self.frame)
        self.pushButton_5.setObjectName(u"pushButton_5")
        self.pushButton_5.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_5, 5, 3, 1, 1)

        self.pushButton_8 = QPushButton(self.frame)
        self.pushButton_8.setObjectName(u"pushButton_8")
        self.pushButton_8.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_8, 8, 3, 1, 1)

        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_3, 3, 1, 1, 1)

        self.label_7 = QLabel(self.frame)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_7, 7, 1, 1, 1)

        self.checkBox_4 = QCheckBox(self.frame)
        self.checkBox_4.setObjectName(u"checkBox_4")

        self.gridLayout_2.addWidget(self.checkBox_4, 4, 0, 1, 1, Qt.AlignHCenter)

        self.checkBox_7 = QCheckBox(self.frame)
        self.checkBox_7.setObjectName(u"checkBox_7")

        self.gridLayout_2.addWidget(self.checkBox_7, 7, 0, 1, 1, Qt.AlignHCenter)

        self.label_9 = QLabel(self.frame)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_9, 9, 1, 1, 1)

        self.checkBox_5 = QCheckBox(self.frame)
        self.checkBox_5.setObjectName(u"checkBox_5")

        self.gridLayout_2.addWidget(self.checkBox_5, 5, 0, 1, 1, Qt.AlignHCenter)

        self.lineEdit_2 = QLineEdit(self.frame)
        self.lineEdit_2.setObjectName(u"lineEdit_2")
        self.lineEdit_2.setEnabled(False)
        self.lineEdit_2.setMinimumSize(QSize(100, 0))
        self.lineEdit_2.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_2.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_2.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_2, 2, 4, 1, 1)

        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_4, 4, 1, 1, 1)

        self.pushButton_7 = QPushButton(self.frame)
        self.pushButton_7.setObjectName(u"pushButton_7")
        self.pushButton_7.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_7, 7, 3, 1, 1)

        self.pushButton_2 = QPushButton(self.frame)
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.pushButton_2.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_2, 2, 3, 1, 1)

        self.checkBox_6 = QCheckBox(self.frame)
        self.checkBox_6.setObjectName(u"checkBox_6")

        self.gridLayout_2.addWidget(self.checkBox_6, 6, 0, 1, 1, Qt.AlignHCenter)

        self.checkBox_2 = QCheckBox(self.frame)
        self.checkBox_2.setObjectName(u"checkBox_2")

        self.gridLayout_2.addWidget(self.checkBox_2, 2, 0, 1, 1, Qt.AlignHCenter)

        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label, 1, 1, 1, 1)

        self.checkBox_8 = QCheckBox(self.frame)
        self.checkBox_8.setObjectName(u"checkBox_8")

        self.gridLayout_2.addWidget(self.checkBox_8, 8, 0, 1, 1, Qt.AlignHCenter)

        self.pushButton_9 = QPushButton(self.frame)
        self.pushButton_9.setObjectName(u"pushButton_9")
        self.pushButton_9.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_9, 9, 3, 1, 1)

        self.lineEdit_6 = QLineEdit(self.frame)
        self.lineEdit_6.setObjectName(u"lineEdit_6")
        self.lineEdit_6.setEnabled(False)
        self.lineEdit_6.setMinimumSize(QSize(100, 0))
        self.lineEdit_6.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_6.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_6.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_6, 6, 4, 1, 1)

        self.lineEdit_5 = QLineEdit(self.frame)
        self.lineEdit_5.setObjectName(u"lineEdit_5")
        self.lineEdit_5.setEnabled(False)
        self.lineEdit_5.setMinimumSize(QSize(100, 0))
        self.lineEdit_5.setMaximumSize(QSize(100, 16777215))
        self.lineEdit_5.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit_5.setReadOnly(True)

        self.gridLayout_2.addWidget(self.lineEdit_5, 5, 4, 1, 1)

        self.pushButton_6 = QPushButton(self.frame)
        self.pushButton_6.setObjectName(u"pushButton_6")
        self.pushButton_6.setEnabled(False)

        self.gridLayout_2.addWidget(self.pushButton_6, 6, 3, 1, 1)

        self.label_8 = QLabel(self.frame)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignCenter)

        self.gridLayout_2.addWidget(self.label_8, 8, 1, 1, 1)

        self.checkBox_19 = QCheckBox(self.frame)
        self.checkBox_19.setObjectName(u"checkBox_19")

        self.gridLayout_2.addWidget(self.checkBox_19, 0, 0, 1, 1, Qt.AlignHCenter)

        self.checkBox_21 = QCheckBox(self.frame)
        self.checkBox_21.setObjectName(u"checkBox_21")

        self.gridLayout_2.addWidget(self.checkBox_21, 0, 3, 1, 2)


        self.gridLayout.addWidget(self.frame, 0, 0, 1, 1, Qt.AlignHCenter|Qt.AlignVCenter)

        self.frame_3 = QFrame(Form)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_3)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.pushButton_20 = QPushButton(self.frame_3)
        self.pushButton_20.setObjectName(u"pushButton_20")
        self.pushButton_20.setEnabled(False)
        self.pushButton_20.setFlat(False)

        self.horizontalLayout.addWidget(self.pushButton_20)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pushButton_19 = QPushButton(self.frame_3)
        self.pushButton_19.setObjectName(u"pushButton_19")

        self.horizontalLayout.addWidget(self.pushButton_19)

        self.pushButton_21 = QPushButton(self.frame_3)
        self.pushButton_21.setObjectName(u"pushButton_21")

        self.horizontalLayout.addWidget(self.pushButton_21)


        self.gridLayout.addWidget(self.frame_3, 1, 0, 1, 3)


        self.retranslateUi(Form)
        self.pushButton_20.clicked["bool"].connect(self.checkBox.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_2.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_3.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_4.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_5.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_6.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_7.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_8.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_9.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_12.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_16.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_18.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_11.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_10.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_17.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_13.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_15.setChecked)
        self.pushButton_20.clicked["bool"].connect(self.checkBox_14.setChecked)
        self.pushButton_20.clicked.connect(self.lineEdit.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_2.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_3.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_4.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_5.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_6.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_7.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_8.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_9.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_18.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_17.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_16.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_15.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_14.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_13.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_12.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_11.clear)
        self.pushButton_20.clicked.connect(self.lineEdit_10.clear)
        self.pushButton_21.clicked.connect(Form.close)
        self.checkBox.toggled.connect(self.pushButton.setEnabled)
        self.checkBox.toggled.connect(self.lineEdit.setEnabled)
        self.checkBox_2.toggled.connect(self.pushButton_2.setEnabled)
        self.checkBox_2.toggled.connect(self.lineEdit_2.setEnabled)
        self.checkBox_3.toggled.connect(self.pushButton_3.setEnabled)
        self.checkBox_3.toggled.connect(self.lineEdit_3.setEnabled)
        self.checkBox_4.toggled.connect(self.pushButton_4.setEnabled)
        self.checkBox_4.toggled.connect(self.lineEdit_4.setEnabled)
        self.checkBox_5.toggled.connect(self.pushButton_5.setEnabled)
        self.checkBox_5.toggled.connect(self.lineEdit_5.setEnabled)
        self.checkBox_6.toggled.connect(self.pushButton_6.setEnabled)
        self.checkBox_7.toggled.connect(self.pushButton_7.setEnabled)
        self.checkBox_8.toggled.connect(self.pushButton_8.setEnabled)
        self.checkBox_9.toggled.connect(self.pushButton_9.setEnabled)
        self.checkBox_9.toggled.connect(self.lineEdit_9.setEnabled)
        self.checkBox_6.toggled.connect(self.lineEdit_6.setEnabled)
        self.checkBox_7.toggled.connect(self.lineEdit_7.setEnabled)
        self.checkBox_8.toggled.connect(self.lineEdit_8.setEnabled)
        self.checkBox_14.toggled.connect(self.pushButton_14.setEnabled)
        self.checkBox_15.toggled.connect(self.pushButton_15.setEnabled)
        self.checkBox_13.toggled.connect(self.pushButton_13.setEnabled)
        self.checkBox_17.toggled.connect(self.pushButton_17.setEnabled)
        self.checkBox_10.toggled.connect(self.pushButton_10.setEnabled)
        self.checkBox_11.toggled.connect(self.pushButton_11.setEnabled)
        self.checkBox_18.toggled.connect(self.pushButton_18.setEnabled)
        self.checkBox_16.toggled.connect(self.pushButton_16.setEnabled)
        self.checkBox_12.toggled.connect(self.pushButton_12.setEnabled)
        self.checkBox_14.toggled.connect(self.lineEdit_14.setEnabled)
        self.checkBox_15.toggled.connect(self.lineEdit_15.setEnabled)
        self.checkBox_13.toggled.connect(self.lineEdit_13.setEnabled)
        self.checkBox_17.toggled.connect(self.lineEdit_17.setEnabled)
        self.checkBox_10.toggled.connect(self.lineEdit_10.setEnabled)
        self.checkBox_11.toggled.connect(self.lineEdit_11.setEnabled)
        self.checkBox_18.toggled.connect(self.lineEdit_18.setEnabled)
        self.checkBox_16.toggled.connect(self.lineEdit_16.setEnabled)
        self.checkBox_12.toggled.connect(self.lineEdit_12.setEnabled)
        self.checkBox_19.toggled.connect(self.checkBox.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_2.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_3.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_4.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_5.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_6.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_7.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_8.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_9.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_12.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_16.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_11.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_10.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_17.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_13.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_15.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_14.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_18.setChecked)
        self.checkBox_19.toggled.connect(self.checkBox_21.setChecked)
        self.checkBox_20.toggled.connect(self.checkBox_22.setChecked)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.checkBox_22.setText(QCoreApplication.translate("Form", u"R\u30b9\u30c6\u30a3\u30c3\u30af", None))
        self.pushButton_12.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_18.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_10.setText(QCoreApplication.translate("Form", u"\u30db\u30fc\u30e0", None))
        self.label_15.setText(QCoreApplication.translate("Form", u"A", None))
        self.label_11.setText(QCoreApplication.translate("Form", u"\uff0b", None))
        self.label_17.setText(QCoreApplication.translate("Form", u"X", None))
        self.pushButton_15.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_11.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_13.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_14.setText(QCoreApplication.translate("Form", u"B", None))
        self.pushButton_14.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_13.setText(QCoreApplication.translate("Form", u"ZR", None))
        self.pushButton_10.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_17.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_12.setText(QCoreApplication.translate("Form", u"R", None))
        self.label_16.setText(QCoreApplication.translate("Form", u"Rstick\u62bc\u3057\u8fbc\u307f", None))
        self.pushButton_16.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_18.setText(QCoreApplication.translate("Form", u"Y", None))
        self.checkBox_20.setText(QCoreApplication.translate("Form", u"all", None))
        self.pushButton.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_3.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"L", None))
        self.pushButton_4.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"\u25bc", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"\u25b2", None))
        self.pushButton_5.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_8.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Lstick\u62bc\u3057\u8fbc\u307f", None))
        self.label_7.setText(QCoreApplication.translate("Form", u"\u25c0", None))
        self.label_9.setText(QCoreApplication.translate("Form", u"\u30ad\u30e3\u30d7\u30c1\u30e3", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"\uff0d", None))
        self.pushButton_7.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_2.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label.setText(QCoreApplication.translate("Form", u"ZL", None))
        self.pushButton_9.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.pushButton_6.setText(QCoreApplication.translate("Form", u"\u8a2d\u5b9a", None))
        self.label_8.setText(QCoreApplication.translate("Form", u"\u25b6", None))
        self.checkBox_19.setText(QCoreApplication.translate("Form", u"all", None))
        self.checkBox_21.setText(QCoreApplication.translate("Form", u"L\u30b9\u30c6\u30a3\u30c3\u30af", None))
        self.pushButton_20.setText(QCoreApplication.translate("Form", u"\u521d\u671f\u5316", None))
        self.pushButton_19.setText(QCoreApplication.translate("Form", u"\u4fdd\u5b58", None))
        self.pushButton_21.setText(QCoreApplication.translate("Form", u"\u9589\u3058\u308b", None))
    # retranslateUi

