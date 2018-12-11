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
from PyQt5.QtCore import *
from numpy import random
import configparser
from queue import Queue
import struct

class ImageGenerator(QThread):
    def __init__(self, fileinfo:str, datain:bytes, imagesize:QSize, qout:Queue):
        super(ImageGenerator, self).__init__()
        self.infor = fileinfo
        self.data = datain
        self.size = imagesize
        self.outque = qout
        self._value = struct.pack("<HI{}s".format(len(self.infor)), len(self.infor), len(self.data),
                                  self.infor.encode("utf-8")) + self.data
        self._pos = 0
        self._framenum = len(self._value)//(self.size.height()*self.size.width()//9-2-4-2)*8
        self.imagecorner = [[qRgb(255, 255, 255), qRgb(0, 0, 0),       qRgb(255, 255, 255)],
                            [qRgb(0, 0, 0),       qRgb(0, 0, 0),       qRgb(255, 255, 255)],
                            [qRgb(255, 255, 255), qRgb(255, 255, 255), qRgb(255, 255, 255)]]

    def _datatoimage(self):
        frameImage = QImage(self.size, QImage.Format_RGB888)
        try:
            for row in range(self.size.height()//3):
                for col in range(self.size.width()//3):
                    if row == 0 and col == 0:
                        continue
                    elif row == self.size.height()//3-1 and col == self.size.width()//3-1:
                        continue
                    elif row == 0 and 1 <= col < 5:
                        v = struct.pack("I", self._framenum)
                        r = v[col-1] & 0xe0
                        g = (v[col-1] << 3) & 0xe0
                        b = (v[col-1] << 6) & 0xc0
                        for irow in range(3):
                            for icol in range(3):
                                frameImage.setPixel(3*col+icol, 3*row+irow, qRgb(r, g, b))
                    else:
                        v = self.data[self._pos]
                        self._pos += 1
                        r = v & 0xe0
                        g = (v << 3) & 0xe0
                        b = (v << 6) & 0xc0
                        for irow in range(3):
                            for icol in range(3):
                                frameImage.setPixel(3*col+icol, 3*row+irow, qRgb(r,g,b))
        # except Exception as e:
        #     print(e)
        finally:
            for row in range(3):
                for col in range(3):
                    frameImage.setPixel(col, row, self.imagecorner[row][col])
                    frameImage.setPixel(self.size.width()//3*3 - col - 1, self.size.height()//3*3 - row - 1,
                                        self.imagecorner[row][col])
            self._framenum -= 1
            return self._pos, frameImage

    def run(self):
        while True:
            n, img = self._datatoimage()
            self.outque.put([n, img])
            # print(n, len(self.data), self.outque.qsize())
            if n == len(self.data):
                break


class Drawing(QWidget):
    progress_signal = pyqtSignal(int)
    drawstatuschange_signal = pyqtSignal(int)

    def __init__(self, imageque:Queue, parent=None):
        super(Drawing, self).__init__(parent)
        self.resize(300, 200)
        self.setWindowTitle("在窗口中画图")
        self.imageque = imageque
        self.datalen = 1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.paintNextFrame)
        self.autofreshEn = False
        self.goingstatus = 0
        # self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.lbl_image = QLabel(self)
        self.lbl_image.move(0, 0)
        self.lbl_image.resize(self.size())

    def reset(self):
        self.timer.stop()
        self.goingstatus = 0
        self.drawstatuschange_signal.emit(self.goingstatus)
        self.progress_signal.emit(0)
        self.update()

    def show(self):
        QWidget.show(self)
        self.raise_()

    def paintNextFrame(self):
        try:
            self.lbl_image.resize(self.size())
            n, img = self.imageque.get(timeout=1)
            self.lbl_image.setPixmap(QPixmap.fromImage(img))
            # self.repaint()
            self.update()
            self.progress_signal.emit(100*(n)/self.datalen)
            if n == self.datalen:
                raise EOFError
        except Exception as e:
            # QMessageBox.information(self, "Message", "all data transmit over!", QMessageBox.Yes, QMessageBox.Yes)
            self.goingstatus = 0
            self.drawstatuschange_signal.emit(self.goingstatus)
            self.timer.stop()

    def keyPressEvent(self, event: QKeyEvent):
        if (event.key() == Qt.Key_Right) or (event.key() == Qt.Key_Down) or (event.key() == Qt.Key_Space):
            # print("next")
            self.paintNextFrame()
        else:
            QWidget.keyPressEvent(self, event)

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width())//2, (screen.height()-size.height())//2)

    def timerstart(self, sec):
        if sec > 0 and self.autofreshEn:
            self.goingstatus = 1
            self.drawstatuschange_signal.emit(self.goingstatus)
            self.timer.start(int(1000*sec))

    def timerstop(self):
        self.autofreshEn = False
        self.goingstatus = 2
        self.drawstatuschange_signal.emit(self.goingstatus)
        self.timer.stop()

    def timercontinue(self):
        self.autofreshEn = True
        self.goingstatus = 1
        self.drawstatuschange_signal.emit(self.goingstatus)
        self.timer.start()


class ControlPanel(QWidget):
    Qimg = Queue(300)

    def __init__(self, parent=None):
        super(ControlPanel, self).__init__(parent)
        self.config = configparser.ConfigParser()
        self.canvas = Drawing(self.Qimg)
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
                        self.imggenerator = ImageGenerator(os.path.basename(self.getfiledir()), f.read(size), self.canvas.size(), self.Qimg)
                        self.imggenerator.start(priority=QThread.HighestPriority)
                        self.canvas.datalen = size
                        self.canvas.autofreshEn = True
                        self.canvas.timerstart(self.getperiod())
                except:
                    raise
        elif self.btn_start.text() == "STOP":
            self.canvas.timerstop()
        else:
            self.canvas.timercontinue()

    def changePeriod(self):
        # print("get signal")
        self.canvas.timerstop()
        self.canvas.autofreshEn = True
        self.canvas.timerstart(self.getperiod())

    def btn_start_reverse(self, canvasstatus:int):
        if canvasstatus == 0:
            self.btn_start.setText("START")
        elif canvasstatus == 1:
            self.btn_start.setText("STOP")
        elif canvasstatus == 2:
            self.btn_start.setText("CONTINUE")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = ControlPanel()
    mw.show()
    sys.exit(app.exec_())
