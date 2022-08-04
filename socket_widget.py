# standard imports #
import sys  # deal with OS, open files and so
import time  # delays, and time measurement ?
import random  # random numbers
import os  # dealing with directories

import serial  # required to handle serial communication
import serial.tools.list_ports  # to list already existing ports

import csv
import numpy as np  # required to handle multidimensional arrays/matrices

import socket

import logging

logging.basicConfig(level=logging.WARNING)  # enable debug messages

# logging.basicConfig(level = logging.WARNING)

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
	QFileDialog,
	QMessageBox,  # Dialog with extended functionality.
	QShortcut,
	QCheckBox,

	QSystemTrayIcon,
	QTextEdit,
	QMenu,
	QAction,
	QWidget
)

from PyQt5 import *

from PyQt5.QtGui import (
	QIcon,
	QKeySequence,
	QColor,
	QFont
)

from PyQt5.QtCore import (
	Qt,
	QThreadPool,
	QRunnable,
	QObject,
	QSize,
	pyqtSignal,  # those two are pyqt specific.
	pyqtSlot,
	QTimer  # nasty stuff
)

# custom imports #
from re_pyqt_widgets.terminal_widget import terminal_widget

# importing the custom palettes from a parent directory, if not found, just ignore palettes #
try:
	import os, sys

	currentdir = os.path.dirname(os.path.realpath(__file__))
	parentdir = os.path.dirname(currentdir)
	sys.path.append(parentdir)

	import pyqt_common_resources.pyqt_custom_palettes as pyqt_custom_palettes

except:
	logging.debug("Custom palettes not found, customization ignored")
# from ..pyqt_common_resources.pyqt_custom_palettes import pyqt_custom_palettes


# GLOBAL VARIABLES ###########################################################################

GENERAL_TIMER_PERIOD = 500  # 500ms period for a general purpose timer
LOG_WINDOW_REFRESH_PERIOD_MS = 100  # maybe better to move to an event based system.

DEFAULT_IP = "192.168.0.221"
DEFAULT_PORT = 5000

SEPARATOR = "----------------------------------------------------------"


class socket_widget(terminal_widget):


	def __init__(self, log_window_enabled = True):
		"""
		Initalizes all required internal widgets (buttons, labels and so on)
		:param log_window_enabled: Enables or disables the log window, useful when using this widget to read the incoming data.
		"""

		# object variables #

		self.ip_address = None  					# ip address of the remote device to be used
		self.port = None  							# port to connect to
		self.socket = None  						# socket object used to create the connection
		self.echo_flag = False						# by default echo is disabled
		self.log_window_flag = log_window_enabled	# enables low window

		logging.debug("Log_window_flag parameter on socket_widget initialization")
		logging.debug(self.log_window_flag)

		super().__init__(
			log_window=self.log_window_flag)  # VERY IMPORTANT! Need to add the initialization parameters of the parent here!!!b

		# self.layout_main = QVBoxLayout()
		# self.setLayout(self.layout_main)

		# SPECIFIC ITEMS TO ADD TO LAYOUT_SPECIFIC_CONNECTION #
		# IP label #
		self.label_ip = QLabel("IP:")
		self.layout_specific_connection.addWidget(self.label_ip)
		# text box IP #
		self.textbox_ip = QLineEdit()
		self.textbox_ip.setInputMask("000.000.000.000;_")
		self.textbox_ip.setText(DEFAULT_IP)  # current default value, so we don't have to type it all the time
		self.textbox_ip.setEnabled(True)  # not enabled until serial port is connected.
		self.layout_specific_connection.addWidget(self.textbox_ip)

		# port label #
		self.label_port = QLabel("Port:")
		self.layout_specific_connection.addWidget(self.label_port)
		# port text box #
		self.textbox_port = QLineEdit()
		self.textbox_port.setText(str(DEFAULT_PORT))  # default port, so faster for debugging
		self.textbox_port.setEnabled(True)  # not enabled until serial port is connected.
		self.layout_specific_connection.addWidget(self.textbox_port)

	def on_button_disconnect_click(self):
		pass

	logging.debug("socket.disconnect finished")

	def on_button_send_click(self):  # do I need another thread for this ???
		pass


# MAIN WINDOW #################################################################################

class MainWindow(QMainWindow):
	# class variables #
	serial_data = ""  # here the processed message(s) after parsing are stored
	serial_lines = []  # the serial data could contain several lines, this variable holds them.
	font_size = 10

	# constructor #
	def __init__(self):
		super().__init__()

		# self.print_timer = QTimer()  # we'll use timer instead of thread
		# self.print_timer.timeout.connect(self.add_log_serial_lines)
		# self.print_timer.start(LOG_WINDOW_REFRESH_PERIOD_MS)  # period needs to be relatively short

		self.widget = QWidget()
		self.setCentralWidget(self.widget)
		self.layout = QVBoxLayout()
		self.widget.setLayout(self.layout)
		self.sock_widget = socket_widget()
		self.layout.addWidget(self.sock_widget)
		# self.serial.new_data.connect(self.get_serial_bytes)
		# self.serial.new_message_to_send.connect(self.add_log_outgoing_command)

		# stylesheet, so I don't get blind with tiny characters #
		self.sty = "QWidget {font-size: 10pt}"
		self.setStyleSheet(self.sty)

		font = self.font()
		font.setPointSize(24)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	app.setStyle("Fusion")  # required to use it here
	window = MainWindow()
	window.show()
	app.exec_()
