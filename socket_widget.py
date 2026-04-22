

# standard imports #
import sys											# deal with OS, open files and so
import time 										# delays, and time measurement ?
import random										# random numbers
import os											# dealing with directories

import serial										# required to handle serial communication
import serial.tools.list_ports						# to list already existing ports

import csv
import numpy as np 									# required to handle multidimensional arrays/matrices

import socket

import logging
logging.basicConfig(level=logging.WARNING)			# enable debug messages

#logging.basicConfig(level = logging.WARNING)

# qt imports #
from PySide6.QtWidgets import (
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
	QMessageBox,														# Dialog with extended functionality.
	QCheckBox,

	QSystemTrayIcon,
	QTextEdit,
	QMenu,
	QWidget
)

from PySide6.QtGui import (
	QIcon,
	QKeySequence,
	QColor,
	QShortcut,
	QAction,
	QFont
)

from PySide6.QtCore import(
	Qt,
	QThreadPool,
	QRunnable,
	QObject,
	QSize,
	Signal,															# those two are pyqt specific.
	Slot,
	QTimer																# nasty stuff
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
#from ..pyqt_common_resources.pyqt_custom_palettes import pyqt_custom_palettes


# GLOBAL VARIABLES ###########################################################################

GENERAL_TIMER_PERIOD = 500  # 500ms period for a general purpose timer
LOG_WINDOW_REFRESH_PERIOD_MS = 100                                      # maybe better to move to an event based system.


#DEFAULT_IP = "172.17.235.151"
#DEFAULT_IP = "172.17.235.144"
DEFAULT_IP = "192.168.0.49"

DEFAULT_PORT = 50001
SEPARATOR = "----------------------------------------------------------"

class socket_widget(terminal_widget):

	CONNECTION_TIMEOUT_S = 10
	ip_address = None                                                                       # ip address of the remote device to be used
	port = None                                                                             # port to connect to
	socket = None                                                                           # socket object used to create the connection
	echo_flag = False

	def __init__(self, log_window = None):

		self.log_window_flag = log_window
		print("Log_window_flag parameter on socket_widget initialization")
		print(self.log_window_flag)

		super().__init__(log_window = self.log_window_flag)                                 # VERY IMPORTANT! Need to add the initialization parameters of the parent here!!!b

		# self.layout_main = QVBoxLayout()
		# self.setLayout(self.layout_main)

		# SPECIFIC ITEMS TO ADD TO LAYOUT_SPECIFIC_CONNECTION #
		# IP label #
		self.label_ip = QLabel("IP:")
		self.layout_specific_connection.addWidget(self.label_ip)
		# text box IP #
		self.textbox_ip = QLineEdit()
		self.textbox_ip.setInputMask("000.000.000.000;_")
		self.textbox_ip.setText(DEFAULT_IP)                       # current default value, so we don't have to type it all the time
		self.textbox_ip.setEnabled(True)						        # not enabled until serial port is connected.
		self.layout_specific_connection.addWidget(self.textbox_ip)

		# port label #
		self.label_port = QLabel("Port:")
		self.layout_specific_connection.addWidget(self.label_port)
		# port text box #
		self.textbox_port = QLineEdit()
		self.textbox_port.setText(str(DEFAULT_PORT))                                # default port, so faster for debugging
		self.textbox_port.setEnabled(True)						                    # not enabled until serial port is connected.
		self.layout_specific_connection.addWidget(self.textbox_port)


	def connect(self):
		"""
		Handles connection process
		:return:
		"""
		# conecting the socket #
		try:
			self.socket = socket.socket()
			print(self.socket)
			print(type(self.ip_address))
			print(self.ip_address)
			print(type(self.port))
			print(self.port)
			self.socket.settimeout(
				self.CONNECTION_TIMEOUT_S)  # very important TO KNOW IF SOCKET IS DEAD !!! 10s is probably a big and conservative value ATM.
			try:
				self.socket.connect((self.ip_address, self.port))
			except:
				logging.error("Connection failed")
				self.on_button_disconnect_click()

			# time.sleep(self.CONNECTION_TIMEOUT_S)
		except:
			logging.exception("The socket couldn't connect")
		else:
			logging.debug("Socket connected")
			# self.connect()						# unimplemented

			# enabling a timer to read in the incoming data of the socket #
			self.read_data_timer.start()

	def on_button_connect_click(self):
		# get the ip and the port from the text fields, to use it to connect the socket #
		self.ip_address = self.textbox_ip.text()
		print(self.ip_address)
		self.port = int(self.textbox_port.text())
		print(self.port)

		self.connect()

		self.print_timer.start()

		# UI changes #
		super().on_button_connect_click()											# mostly ui related

	def on_button_disconnect_click(self):
		# critical stuff to stop #
		self.read_data_timer.stop()                              # need to stop the timer, or it will continue trying to get that from the closed socket
		self.socket.close()
		logging.debug("Socket closed")
		# clearing variables #
		self.ip_address = None                              # clear all connection variables
		self.port = None
		self.socket = None                                  #if not closing the socket first, the app crashes
		# updating UI to current state #
		super().on_button_disconnect_click()



		logging.debug("socket.disconnect finished")

	def save_ip(self):
		"""
		Was this to save IP in a file for next executions ???
		:return:
		"""
		pass


	def send_command(self, command):
		# here the serial send command #
		self.message_to_send = command.encode("utf-8")  + self.endline # this should have effect on the serial_thread
		logging.debug("message_to_send")
		logging.debug(self.message_to_send)
		self.socket.send(self.message_to_send)
		# self.new_message_to_send.emit()                         # emits signal, a new message is sent to slave.

		# TRIGGER THE SIGNAL A MESSAGE IS SENT --> SO WE CAN GET THE MESSAGE ON THE LOG WINDOW.

		# print("serial_message_to_send")
		# print(self.serial_message_to_send)
		# self.serial_port.write(self.serial_message_to_send)
		# self.new_message_to_send.emit()                         # emits signal, a new message is sent to slave.



		# add here action trigger, so it can be catched by main window.
	# ADDITIONAL TOOLS METHODS #
	# not to be displayed in the widget, but called by the menus of a main window

	def read_data(self):
		"""
		Method that actually reads data from serial port
		:return:
		"""

		incoming_data = b'' 									# empty string, so at least something is returned
		# try:
		logging.error("About to read incoming data")
		incoming_data = self.socket.read(self.READ_BLOCK_SIZE)  # up to 1000 or as much as in buffer.
		print("incoming_data:")
		print(incoming_data)
		# except Exception as e:
		# self.on_port_error(e)
		self.on_button_disconnect_click()  	# we've crashed the serial, so disconnect and REFRESH PORTS!!!
		# else:
		if(incoming_data):				# do anything actually only if there's data.
			logging.debug(self.SEPARATOR)
			logging.debug("Bytes (incoming_data):")
			logging.debug(incoming_data)
			logging.debug(self.SEPARATOR)

		return(incoming_data)



	def ping_sweep(self):
		import pythonping as ping
		# 1. get my own hostname to know where to scan.
		my_hostname = socket.gethostname()
		my_ip = socket.gethostbyname(my_hostname)
		split_my_ip = my_ip.split('.')
		rest_ip = split_my_ip[0] + '.' + split_my_ip[1] + '.' + split_my_ip[2] + '.'

		# 2. Ping all devices in a range, to know which ones are available.
		for i in range(1, 20):              # this should be a selectable range!!! best option take the ping sweep to another window!!!
			target_ip = rest_ip + str(i)
			print(my_hostname)

			ping_results = ping.ping(target=target_ip, timeout=0.1)
			if (ping_results.success()):
				print("The device with IP " + target_ip + " is available")
				# 3. Check the name of the device
				# name = socket.gethostbyaddr(target_ip)
				# print(name)

			else:
				print("DEVICE " + target_ip + " UNAVAILABLE")

	def find_cacahuete(self):

		device_name = 'CACAHUETE'
		print("Looking for " + device_name + " devices")
		try:
			ip_address = socket.gethostbyname(device_name)
		except Exception as e:
			logging.error(e)
		else:
			print(device_name + " Found on address " + ip_address)
			cacau_dialog = QDialog(device_name + " Found on address " + ip_address)


# MAIN WINDOW #################################################################################

class MainWindow(QMainWindow):
	# class variables #
	serial_data = ""                            # here the processed message(s) after parsing are stored
	serial_lines = []                           # the serial data could contain several lines, this variable holds them.
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
		#self.serial.new_data.connect(self.get_serial_bytes)
		#self.serial.new_message_to_send.connect(self.add_log_outgoing_command)

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
	app.exec()

