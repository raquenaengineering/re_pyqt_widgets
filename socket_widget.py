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

logging.basicConfig(level=logging.DEBUG)  # enable debug messages

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
		self.socket = socket.socket()  				# socket object used to create the connection
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



	def connect(self):
		"""
		Connects a socket to the IP address and port given by the textboxes on the UI
		:return: True on succesful connection, False on failed.
		"""

		ret = False

		self.ip_address = self.textbox_ip.text()
		self.port = int(self.textbox_port.text())
		logging.debug(self.ip_address)
		logging.debug(self.port)

		try:
			self.socket = socket.socket()							# socket needs to be created new for each connection ???
			self.socket.connect((self.ip_address,self.port))
			self.socket.settimeout(
				5)  # very important TO KNOW IF SOCKET IS DEAD !!! 10s is probably a big and conservative value ATM.

		except:
			logging.warning("Socket couldn't connect")
			ret = False
		else:
			logging.debug("socket connected")
			self.read_data_timer.start()
			ret = True

		return(ret)

	def disconnect(self):
		self.socket.close()
		logging.debug("Socket closed")



	def on_button_connect_click(self):					# redefinition of terminal_widget class method

		connected = self.connect()

		if(connected):
			# UI changes #
			self.button_connect.setEnabled(False)
			self.button_disconnect.setEnabled(True)
			self.textbox_send_command.setEnabled(True)
			self.b_send.setEnabled(True)

	def on_button_disconnect_click(self):
		# main functionality #
		self.disconnect()
		# UI changes #
		self.button_disconnect.setEnabled(False)
		self.button_connect.setEnabled(True)
		self.textbox_send_command.setEnabled(False)
		self.textbox_send_command.clear()
		self.textbox_send_command.clear()
		self.b_send.setEnabled(False)

	def send_message(self, message):
		"""
		Sends a message using a socket to a slave/server device.
		This method is blocking, it will not return until the message is sent or an error arises.
		:param message: message to be sent to the slave/server device.
		:return: 0 if no issues sending the message
		"""
		logging.debug("socket_widget.send_message method called")
		message_b = message.encode("utf-8") + self.endline
		self.socket.send(message_b)

	def receive_message(self):
		"""
		receives a message from a slave/server.
		At the moment this method is blocking, with a given timeout of 0.1s

		:return: the message received will be returned
		"""
		logging.debug("socket_widget.receive_message method called")
		self.socket.settimeout(0.1)
		try:
			message = self.socket.recv(1024)											# it will return when buffer is empty anyway
		except:
			pass
			logging.debug("nothing to receive")
		else:
			print(message)
			return(message)


	def on_read_data_timer(self):
		self.receive_message()

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
