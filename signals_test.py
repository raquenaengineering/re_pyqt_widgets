


# standard imports #
import sys											# deal with OS, open files and so
import time 										# delays, and time measurement ?
import random										# random numbers
import os											# dealing with directories

import serial										# required to handle serial communication
import serial.tools.list_ports						# to list already existing ports

import csv
import numpy as np 									# required to handle multidimensional arrays/matrices

import logging
#logging.basicConfig(level=logging.DEBUG)			# enable debug messages
logging.basicConfig(level = logging.WARNING)

# qt imports #
from PyQt5.QtWidgets import (
	QApplication,
	QMainWindow,
	QVBoxLayout,
	QHBoxLayout,
	QLabel,
	QComboBox,
	QLineEdit,
	QPushButton,
	QMenuBar,
	QToolBar,
	QStatusBar,
	QDialog,
	QMessageBox,														# Dialog with extended functionality.
	QShortcut,
	QCheckBox,

	QSystemTrayIcon,
	QTextEdit,
	QMenu,
	QAction,
	QWidget
)

from PyQt5.QtGui import (
	QIcon,
	QKeySequence
)

from PyQt5.QtCore import(
	Qt,
	QThreadPool,
	QRunnable,
	QObject,
	QSize,
	pyqtSignal,															# those two are pyqt specific.
	pyqtSlot,
	QTimer																# nasty stuff

)


class MainWindow(QMainWindow):

	def __init__(self):
		super().__init__()
		self.widget = QWidget()
		self.setCentralWidget(self.widget)
		self.layout = QVBoxLayout()
		self.widget.setLayout(self.layout)
		self.subwidget = subwidget()
		self.subwidget.dataready.connect(self.print_something)

	# triggered when there is new data available on serial_buffer
	def print_something(self):
		print(self.subwidget.data)

class subwidget(QWidget):

	dataready = pyqtSignal()  # signal to be emitted somewhen
	data = []

	def __init__(self):
		super().__init__()

		#self.dataready.connect(self.on_data_ready)

		self.timer = QTimer()
		self.timer.timeout.connect(self.on_timeout)
		self.timer.start(1000)  # period needs to be relatively short

	def on_timeout(self):
		self.data.append(random.randrange(1,10))
		self.dataready.emit()

	# def on_data_ready(self):
	# 	return(self.data)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()