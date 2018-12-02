#!/usr/bin/env python
# encoding: utf-8

"""
@version: 
@author: Li
@license: Apache Licence 
@contact: lishb0523@163.com
@site: http://www.xxx.com
@software: PyCharm
@file: DataToImage.py
@time: 2018/11/17 11:42
"""

import os, sys, math
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from numpy import random
import configparser


class Drawing(QWidget):
    progress_signal = pyqtSignal(float)
    drawstatuschange_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super(Drawing, self).__init__(parent)
        self.resize(300, 200)
        self.setWindowTitle("在窗口中画图")
        self.data = b''
        self._framestart = 0
        self._frameend = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.paintNextFrame)
        self.autofreshEn = False
        self.goingstatus = False
        # self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.lbl_image = QLabel(self)
        self.lbl_image.move(0, 0)
        self.lbl_image.resize(self.size())

    def reset(self):
        self._framestart = 0
        self._frameend = 0
        self.timer.stop()
        self.goingstatus = False
        self.drawstatuschange_signal.emit(self.goingstatus)
        self.progress_signal.emit(int(100 * self._frameend / len(self.data)))
        self.update()

    def _dataToImage(self):
        frameImage = QImage(self.size(), QImage.Format_RGB888)
        for n, v in enumerate(self.data[self._framestart:self._frameend]):
            r = v&0xe0
            g = (v<<3)&0xe0
            b = (v<<6)&0xc0
            pix = qRgb(r, g, b)
            row = n//self.width()
            col = n-row*self.width()
            frameImage.setPixel(col, row, pix)
        return frameImage

    def paintImage(self):
        image = self._dataToImage()
        self.lbl_image.resize(self.size())
        self.lbl_image.setPixmap(QPixmap.fromImage(image))

    # def paintEvent(self, event):
        # # 初始化绘图工具
        # qp = QPainter()
        # # 开始绘图
        # qp.begin(self)
        # self.drawPoints(qp)
        # # paint over
        # qp.end()

    def drawPoints(self, qp):
        qp.setPen(Qt.red)
        for n, v in enumerate(self.data[self._framestart:self._frameend]):
            for ibit in range(8):
                if (v&0x80) == 0x80:
                    y = (n*8 + ibit)//self.width()+1
                    x = (n*8 + ibit)-self.width()*(y-1)
                    qp.drawPoint(x, y)

    # def __getdataframe(self):  #don`t surport get previous frame
    #     startpos = 0
    #     while startpos < len(self.data):
    #         framelen = self.width() * self.height() // 8
    #         yield self.data[startpos: startpos + framelen]
    #         startpos += framelen

    def show(self):
        QWidget.show(self)
        self.raise_()

    def __getnextframe(self):
        framelen = self.width() * self.height()
        if self._frameend >= len(self.data):
            raise IndexError("data index out of range")
        self._framestart = self._frameend
        self._frameend = self._framestart + framelen
        if self._frameend > len(self.data):
            self._frameend = len(self.data)
        self.progress_signal.emit(int(100*self._frameend/len(self.data)))
        # print(self._framestart, self._frameend, len(self.data), int(100*self._frameend/len(self.data)))

    def __getprevframe(self):
        framelen = self.width() * self.height()
        self._frameend = self._framestart
        self._framestart = self._frameend - framelen if self._frameend > framelen else 0
        if self._framestart == 0:
            self._frameend = self._framestart + framelen
        self.progress_signal.emit(int(100*self._frameend / len(self.data)))
        # print(self._framestart, self._frameend)

    def setData(self, data:bytes):
        self.data = data

    def paintNextFrame(self):
        try:
            self.__getnextframe()
            self.paintImage()
            # self.repaint()
            self.update()
        except:
            QMessageBox.information(self, "Message", "all data transmit over!", QMessageBox.Yes, QMessageBox.Yes)
            self.goingstatus = False
            self.drawstatuschange_signal.emit(self.goingstatus)
            self.timer.stop()

    def paintPrevFrame(self):
        try:
            self.__getprevframe()
            self.paintImage()
            self.repaint()
            # self.update()
        except:
            QMessageBox.information(self, "Message", "this is first data frame!", QMessageBox.Yes, QMessageBox.Yes)
            # self.timer.stop()

    def keyPressEvent(self, event: QKeyEvent):
        if (event.key() == Qt.Key_Right) or (event.key() == Qt.Key_Down) or (event.key() == Qt.Key_Space):
            # print("next")
            self.paintNextFrame()
        elif (event.key() == Qt.Key_Left) or (event.key() == Qt.Key_Up):
            # print("prev")
            self.paintPrevFrame()
        else:
            QWidget.keyPressEvent(self, event)

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width())//2, (screen.height()-size.height())//2)

    def timerstart(self, sec):
        if sec > 0 and self.autofreshEn:
            self.goingstatus = True
            self.drawstatuschange_signal.emit(self.goingstatus)
            self.timer.start(int(1000*sec))

    def timerstop(self):
        self.autofreshEn = False
        self.goingstatus = False
        self.drawstatuschange_signal.emit(self.goingstatus)
        self.timer.stop()


class ControlPanel(QWidget):
    def __init__(self, parent=None):
        super(ControlPanel, self).__init__(parent)
        self.config = configparser.ConfigParser()

        self.canvas = Drawing()
        self.setupUI()
        self.getConfig()

    def setupUI(self):
        self.resize(300, 100)
        self.setFixedSize(self.size())
        self.setWindowTitle("控制台")
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.cb_file = QComboBox()
        self.cb_file.setFixedSize(200, 23)
        self.cb_file.setEditable(True)
        self.btn_selectfile = QPushButton("import")
        self.btn_selectfile.setFixedSize(60, 23)
        self.btn_selectfile.released.connect(self.__getSouceFile)
        lbl_timer = QLabel("Timer Trig(s):", self)
        self.le_period = QLineEdit()
        self.le_period.setFixedSize(60, 23)
        self.le_period.setText("1")
        self.le_period.editingFinished.connect(self.changePeriod)
        self.btn_start = QPushButton("START")
        self.btn_start.setFixedSize(45, 45)
        self.btn_start.released.connect(self.startTransmit)
        self.btn_reset = QPushButton("Reset", self)
        self.btn_reset.setFixedSize(38,20)
        self.btn_reset.released.connect(self.canvas.reset)
        self.pbar = QProgressBar(self)
        self.pbar.setFixedSize(230, 16)

        self.canvas.progress_signal.connect(self.pbar.setValue)
        self.canvas.drawstatuschange_signal.connect(self.btn_start_reverse)

        layout.addWidget(self.cb_file, 0, 0, 1, 2)
        layout.addWidget(self.btn_selectfile, 0, 2, alignment=Qt.AlignRight)
        layout.addWidget(lbl_timer, 1, 0)
        layout.addWidget(self.le_period, 1, 1, alignment=Qt.AlignLeft)
        layout.addWidget(self.btn_start, 1, 2, 2, 1, alignment=Qt.AlignCenter)
        layout.addWidget(self.pbar, 2, 0, 1, 2)
        self.setLayout(layout)
        self.btn_reset.move(190, 43)
        self.center()

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width())//2, (screen.height()-size.height())//2)

    def __getSouceFile(self):
        file, filetype = QFileDialog.getOpenFileName(self, "select file", os.path.curdir, "All File(*)")
        self.cb_file.addItem(file)
        self.cb_file.setCurrentIndex(self.cb_file.count()-1)

    def setfiledir(self, filedir):
        self.cb_file.setCurrentText(filedir)

    def getfiledir(self):
        return self.cb_file.currentText()

    def setperiod(self, sec):
        self.le_period.setText(str(sec))

    def getperiod(self):
        return float(self.le_period.text())

    def closeEvent(self, event):
        """
        重写closeEvent方法，实现dialog窗体关闭时执行一些代码
        :param event: close()触发的事件
        :return: None
        """
        reply = QMessageBox.question(self, '本程序', "是否要退出程序？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.canvas.isWindow():
                self.configsav(self.canvas.x(), self.canvas.y(), self.canvas.width(), self.canvas.height())
                self.canvas.close()
            event.accept()
        else:
            event.ignore()

    def show(self):
        self.canvas.show()
        QWidget.show(self)

    def getConfig(self):
        try:
            self.config.read("config.ini")
            self.setfiledir(self.config.get("config", "defaultdir"))
            self.setperiod(float(self.config.get("config", "period")))
            self.canvas.move(int(self.config.get("config", "canvasposx")), int(self.config.get("config", "canvasposy")))
            self.canvas.resize(int(self.config.get("config", "canvaswidth")), int(self.config.get("config", "canvasheith")))
        except:
            if os.path.exists("config.ini"):
                os.remove("config.ini")
            self.config.clear()
            self.config.add_section("config")
            self.config.set("config", "defaultdir", os.path.curdir)
            self.config.set("config", "period", str(self.getperiod()))
            self.config.set("config", "canvasposx", str(self.canvas.x()))
            self.config.set("config", "canvasposy", str(self.canvas.y()))
            self.config.set("config", "canvaswidth", str(self.canvas.width()))
            self.config.set("config", "canvasheith", str(self.canvas.height()))
            self.config.write(open("config.ini", "w+"))
            raise

    def configsav(self, x, y, w, h):
        try:
            self.config.clear()
            self.config.add_section("config")
            self.config.set("config", "defaultdir", self.getfiledir())
            self.config.set("config", "period", str(self.getperiod()))
            self.config.set("config", "canvasposx", str(x))
            self.config.set("config", "canvasposy", str(y))
            self.config.set("config", "canvaswidth", str(w))
            self.config.set("config", "canvasheith", str(h))
            self.config.write(open("config.ini", "w+"))
        except:
            QMessageBox.warning(self, "Warning!", "配置保存失败", QMessageBox.Yes, QMessageBox.Yes)

    def startTransmit(self):
        if self.btn_start.text() == "START":
            if os.path.isfile(self.getfiledir()):
                try:
                    self.canvas.show()
                    # self.canvas.reset()
                    size = os.path.getsize(self.getfiledir())
                    with open(self.getfiledir(), "rb") as f:
                        self.canvas.autofreshEn = True
                        self.canvas.setData(f.read(size))
                        self.canvas.timerstart(self.getperiod())
                except:
                    raise
        else:
            self.canvas.timerstop()

    def changePeriod(self):
        # print("get signal")
        self.canvas.timerstop()
        self.canvas.autofreshEn = True
        self.canvas.timerstart(self.getperiod())

    def btn_start_reverse(self, canvasstatus:bool):
        if canvasstatus:
            self.btn_start.setText("STOP")
        else:
            self.btn_start.setText("START")



if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = ControlPanel()
    mw.show()
    sys.exit(app.exec_())
