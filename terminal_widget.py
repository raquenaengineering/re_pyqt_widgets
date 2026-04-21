# this class is made to be the parent class of:
#     - serial_widget
#     - socket_widget
#     - ble_widget?
#     - bluetooth_widget?

# Why to do this ???
# Most of the communication types require a very similar user interface:

# 1.CONNECT - Connect/disconnect to/from a remote device
#   1.1 - SPECIFIC PARAMTERS - Specific connection parameters (this will be extended for each child class)
#   1.2 - CONNECT AND DISCONNECT BUTTONS
# 2.SEND DATA - Text entry to send commands to the remote device (MAYBE ALSO A LOAD TO LOAD A LIST OF COMMANDS COULD BE INTERESTING !!!)
# 3.RECEIVE DATA
#   3.1 - Multiple lines text entry, where the incoming data will be displayed
#   3.2 - Clear and save buttons



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

# from future.backports.html.parser import incomplete

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

from PySide6 import *

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


class log_window_widget(QWidget):               # future implementation of the log window will be a different widget.
	pass


class terminal_widget(QWidget):
	# class variables #

	RECEIVE_TEXT_COLOR = "red"
	SEND_TEXT_COLOR = "green"
	SEPARATOR = "----------------------------------------------------------"

	# LOG_WINDOW_REFRESH_PERIOD_MS = 5000  # maybe better to move to an event based system.
	MAX_TEXT_SIZE = 30
	MIN_TEXT_SIZE = 5

	connected = False
	message_to_send = None              # if not none, is a message to be sent via serial port
	echo_flag = False                   # to enable/disable echoing sent messages to the log window
	timeouts = 0
	byte_buffer = b''                   # buffer where the received bytes are stored until used.
	readed_bytes = b''                  # bytes received in the last read
	recording = False                   # flag to start/stop recording.
	log_window_flag = False             # when True, shows the reception log window, clear and save buttons, if not, means the data will be handled in a different way.
	log_folder = "logs"                 # in the beginning, log folder, path and filename are fixed
	log_file_name = "log_file"          # all communication in and out (could be) collected here.
	log_file_type = ".txt"              # file extension
	log_full_path = None                # this variable will be the one used to record
	service_timer_period = 10			# is for important things, so period is short
	read_data_timer_period = 1000       # period in ms to read incoming data
	log_window_refresh_period =3000     # the log windows isn't updated inmediately, but every 100ms
	incoming_data = ""                  # characters converted from readed_bytes, to be converted in lines
	incoming_lines = []                 # contains all incoming data separated by lines, to print it on the log_window
	save_to_log_file = True				# by default, all data written to the log window will also be dumped to a logfile.

	log_window_buffer = []				# contains the data which is to be printed on the log window.
	log_file_buffer = []				# same for the data which has to be saved to file.

	#endline = "\n"                      # requred to get the data properly interpreted
	endline = b'\n'                   # probably this is a better option, but it will require some changes, fix !!!


	new_data = Signal()             # signal triggered when new data is available, to be used by parent widget.
	# new_message_to_send = Signal()  # a new message is sent to the slave, used by parent to, for example log it.

	def __init__(self, log_window = False):

		super().__init__()

		print("log_window")
		print(log_window)


		self.log_window_flag = log_window

		# service timer #
		self.service_timer = QTimer()  									# for periodic checks, like buffers getting too big.
		self.service_timer.timeout.connect(self.on_service_timer)
		self.service_timer.start(self.service_timer_period)  # period needs to be relatively short
		self.service_timer.stop()  # by default the timer will be off, enabled by connect.


		# data timer #
		self.read_data_timer = QTimer()  # we'll use timer instead of thread
		self.read_data_timer.timeout.connect(self.on_read_data_timer)
		self.read_data_timer.start(self.read_data_timer_period)  # period needs to be relatively short
		self.read_data_timer.stop()  # by default the timer will be off, enabled by connect.

		# log print timer #
		self.print_timer = QTimer()  # we'll use timer instead of thread
		self.print_timer.timeout.connect(self.on_print_timer)
		self.print_timer.start(self.log_window_refresh_period)  # period needs to be relatively short
		self.print_timer.stop()  # by default the timer will be off, enabled by connect.

		# size policies, COMMON#
		#self.setMaximumHeight(180)              # this is only valid if there's no log window, change this policy if log window enabled.
		self.setContentsMargins(0, 0, 0, 0)

		# general top layout #
		self.layout_main = QVBoxLayout()
		self.setLayout(self.layout_main)

		# layout containing specific connection plus connect and disconnect buttons #
		self.layout_upper = QHBoxLayout()
		self.layout_main.addLayout(self.layout_upper)

		self.layout_specific_connection = QHBoxLayout()
		self.layout_specific_connection.setContentsMargins(0,0,0,0)
		self.layout_upper.addLayout(self.layout_specific_connection)

		self.layout_connect_disconnect = QHBoxLayout()
		self.layout_connect_disconnect.setContentsMargins(0,0,0,0)
		self.layout_upper.addLayout(self.layout_connect_disconnect)

		# connect button COMMON#
		self.button_connect = QPushButton("Connect")
		self.button_connect.clicked.connect(self.on_button_connect_click)
		self.button_connect.setEnabled(True)
		self.layout_connect_disconnect.addWidget(self.button_connect)

		# disconnect button COMMON #
		self.button_disconnect = QPushButton("Disconnect")
		self.button_disconnect.clicked.connect(self.on_button_disconnect_click)
		self.button_disconnect.setEnabled(False)
		self.layout_connect_disconnect.addWidget(self.button_disconnect)

		# layout to send data to remote device COMMON #
		self.layout_send = QHBoxLayout()
		self.layout_main.addLayout(self.layout_send)
		# text box command #
		self.textbox_send_command = QLineEdit()
		self.textbox_send_command.returnPressed.connect(self.on_button_send_click)	# sends command via serial port
		self.textbox_send_command.setEnabled(False)						# not enabled until serial port is connected.
		self.layout_send.addWidget(self.textbox_send_command)
		# send button #
		self.button_send = QPushButton("Send")
		self.button_send.clicked.connect(self.on_button_send_click)					# same action as enter in textbox
		self.button_send.setEnabled(False)
		self.layout_send.addWidget(self.button_send)
		# checkbox echo#
		self.check_echo = QCheckBox("Echo")
		self.check_echo.setChecked(self.echo_flag)                        # whatever the default echo varaible value is
		self.check_echo.clicked.connect(self.on_check_echo)
		self.layout_send.addWidget(self.check_echo)

		# log window layout box #
		self.layout_log_window = QVBoxLayout()
		self.layout_main.addLayout(self.layout_log_window, stretch=2)		# stretch doesn't work...
		self.log_text = QTextEdit()
		self.log_text.setMinimumHeight(40)
		self.log_text.setFontPointSize(10)
		self.log_text.setReadOnly(True)
		self.layout_log_window.addWidget(self.log_text,stretch=2)

		# self.serial.new_data.connect(self.get_serial_bytes)
		# self.new_message_to_send.connect(self.add_outgoing_lines_to_log)

		self.buttons_layout = QHBoxLayout()
		self.layout_log_window.addLayout(self.buttons_layout)
		self.button_save_log = QPushButton("Save Log")
		self.button_save_log.clicked.connect(self.save_log)
		self.buttons_layout.addWidget(self.button_save_log)
		# add a separator here
		self.button_clear_log = QPushButton("Clear Log")
		self.button_clear_log.clicked.connect(self.clear_log)
		self.buttons_layout.addWidget(self.button_clear_log)


		print("self.log_window_flag")
		print(self.log_window_flag)

		if(self.log_window_flag == True):                           # this only works in "compilation" time.
			self.enable_log_window()
		elif(self.log_window_flag == False):                                                       # this only works in "compilation" time.
			self.disable_log_window()
		elif(self.log_window_flag == None):
			logging.warning("SOMETHING IS QUITE FUCKED UP ON LOG_WINDOW_FLEG")

	#COMMON, BUT UNIMPLEMENTED: we read the data from the given input stream (serial or socket) on a timer basis
	# maybe it's interesting to consider doing it via SIGNAL TRIGGER

	def on_service_timer(self):
		"""
		Used for checks about things exploding, for example:
		log_window_buffer = []	GETTING TOO BIG!
		log_file_buffer = [] GETTING TOO BIG!
		byte_buffer GETTING TOO BIG1
		:return:
		"""
		logging.debug("on_service_timer()")
		if(len(self.log_window_buffer) > 100000):
			logging.error("log_window_buffer got too big")


	def on_read_data_timer(self):
		"""
		To be reimplemented on each child class.
		Callback to run every tick of the data timer.
		This should contain reads to wherever the incoming data comes from
		For example: Serial port, Socket port.
		The current implementation will add some random data to use as an example.
		:return:
		"""
		# could also read random bullshit from a file, for example.

		# READ THE DATA TO A BUFFER #
		logging.warning("on_read_data_timer()")
		try:
			self.readed_bytes = self.simulate_incoming_data()
			# self.log_window_buffer = self.readed_bytes						# until I figure out how to do it better CREATE TWO BUFFERS; ONE FOR THE LOG WINDOW AND ONE FOR THE LOG FILE
			# self.log_file_buffer = self.readed_bytes						# until I figure out how to do it better CREATE TWO BUFFERS; ONE FOR THE LOG WINDOW AND ONE FOR THE LOG FILE
			print("self.readed_bytes")
			print(self.readed_bytes)
		except Exception as e:
			logging.error("couldn't read bytes from anywhere")
		else:
			if(self.readed_bytes):
				print("new input data")
				# we could consider deleting those loggings
				logging.debug("Chars:")
				logging.debug(self.SEPARATOR)
				logging.debug(self.incoming_data)
				logging.debug(self.SEPARATOR)
				logging.debug("Bytes:")
				logging.debug(self.SEPARATOR)
				logging.debug(self.readed_bytes)
				logging.debug(self.SEPARATOR)


				# ADD DATA TO LOG WILL HAPPEN BASED ON ITS CORRESPONDING TIMER;(THE PRINT TIMER)
				# so read and print are completely independent. Remove window print and log print from this method.

				# # if (self.incoming_data[0] != '\0'):  # empty strings won't be saved to file
				# if (self.log_window_flag == True):				# if the log window is disabled no need to do the job ???
				# 	print("self.log_window_flag is True")
				# 	self.log_window_buffer = self.log_window_buffer + [self.readed_bytes]
				# 	# PRINT TO LOG WINDOW -->
				# 	# should I keep the text printing to the log window just in case I decide to enable it interactively ???
				# 	self.add_incoming_lines_to_log()  # print to log window

				# if (self.save_to_log_file == True):
				# 	# SAVE TO LOGFILE #
				# 	file = open("incoming_data.txt", 'a', newline='')  # saving data to file.
				# 	logging.debug("saved to file")
				# 	file.write(self.incoming_data)
				# 	file.write('\n')
				# 	chars = None  # indeed there's no new information/messages.

					# logging.debug(byte_buffer)
					# after collecting some data on the byte buffer, store it in a static variable, and
					# emit a signal, so another window can subscribe to it, and handle the data when needed.
				self.new_data.emit()
				self.byte_buffer = self.byte_buffer + self.readed_bytes  # only reading the bytes, but NO PARSING

		logging.debug("self.readed_bytes")
		logging.debug(self.readed_bytes)
		logging.debug("self.byte_buffer")
		logging.debug(self.byte_buffer)

	def on_print_timer(self):
		logging.warning("on_print_timer()")
		# if (self.incoming_data[0] != '\0'):  # empty strings won't be saved to file
		if (self.log_window_flag == True):  # if the log window is disabled no need to do the job ???
			print("self.log_window_flag is True")
			self.log_window_buffer = self.log_window_buffer + [self.readed_bytes]
			# PRINT TO LOG WINDOW -->
			# should I keep the text printing to the log window just in case I decide to enable it interactively ???
			self.add_incoming_lines_to_log()  # print to log window

		if (self.save_to_log_file == True):
			# SAVE TO LOGFILE #
			file = open("incoming_data.txt", 'a', newline='')  # saving data to file.
			logging.debug("saved to file")
			file.write(self.incoming_data)
			file.write('\n')
			chars = None  # indeed there's no new information/messages.


	def enable_log_window(self):
		print("enable_log_window method called")
		self.setMinimumHeight(300)  # add more space, so we can properly see the log window.
		self.log_text.setVisible(True)
		self.button_save_log.setVisible(True)
		self.button_clear_log.setVisible(True)
	def disable_log_window(self):
		print("disable_log_window method called")
		self.setMaximumHeight(160)  # add more space, so we can properly see the log window.
		#self.setFixedHeight(80)
		self.log_text.setVisible(False)
		self.button_save_log.setVisible(False)
		self.button_clear_log.setVisible(False)

	def add_incoming_lines_to_log(self):
		# NOTE: Be careful using print, better logging debug, as print doesn't follow the program flow when multiple threads.
		logging.warning("add_incoming_lines_to_log() method called")

		# self.parse_bytes(self.readed_bytes)                                     # parse_serial_bytes already handles the modifications over serial_data
		self.log_text.append(self.SEPARATOR)
		logging.debug("self.readed_bytes variable:")
		logging.debug(self.readed_bytes)
		# self.incoming_data = ""                                               # clearing variable, data is already used
		for line in self.incoming_lines:
			if(line != ''):                                                     # do nothing in case of empty string
				color = QColor(self.RECEIVE_TEXT_COLOR)
				self.log_text.setTextColor(color)
				l = ">> " + str(line)                                           # marking for incoming lines
				self.log_text.append(l)
		self.incoming_lines = []                                                # data is already on text_edit, not needed anymore

	def add_outgoing_lines_to_log(self):
		"""
		This method is used when we need to have local echo of the sent commands
		The current implementation is not great !!! --> find a better way to do this

		:return:
		"""
		logging.debug("add_outgoing_lines_to_log method called")
		if (self.echo_flag == True):
			logging.debug("echo flag enabled, echoing message on log window")
			color = QColor(self.SEND_TEXT_COLOR)								# sent text goes in green
			self.log_text.setTextColor(color)									# sent text goes in green
			logging.debug("self.message_to_send")
			logging.debug(self.message_to_send)
			logging.warning("typeof self.message_to_send")
			logging.warning(type(self.message_to_send))
			l = "<< " + self.message_to_send									# messages sent add << in front instead of >>
			self.log_text.append(l)												# add to log

	# COMMON: both serial and socket have a button to save the current log #
	def save_log(self):
		# popup window to save in user defined location #
		name = QFileDialog.getSaveFileName(self,"Save File")
		#logging.debug("Variable file:")
		#logging.debug(name)
		try:
			file = open(name[0],'w')                        # first parameter contains the name of the selected file.
			file.write(self.log_text.toPlainText())
		except:
			logging.debug("Error saving to file")
	def clear_log(self):
		"""
		Clears the log window, but doesn't delete the buffer containing the data that will be printed there.
		:return:
		"""
		self.log_text.clear()

	def on_button_connect_click(self):                      # SPECIFIC depending on the type of connection
		"""
		Dummy, changes the enabled widgets as it had real functionality.
		can be used as self.parent.on_button_connect_click() to implement some functionality.

		:return:
		"""
		self.button_connect.setEnabled(False)
		self.button_disconnect.setEnabled(True)
		self.textbox_send_command.setEnabled(True)
		self.button_send.setEnabled(True)
		self.read_data_timer.start()
		# consider also starting stopping the print_timer()

		self.read_data_timer.start(self.read_data_timer_period)  # period needs to be relatively short


	def on_button_disconnect_click(self):                   # SPECIFIC depending on the type of connection
		"""
		Dummy, changes the enabled widgets as it had real functionality.
		can be used as self.parent.on_button_disconnect_click() to implement some functionality.
		:return:
		"""
		self.button_connect.setEnabled(True)
		self.button_disconnect.setEnabled(False)
		self.textbox_send_command.setEnabled(False)
		self.button_send.setEnabled(False)
		self.read_data_timer.stop()




	def on_button_send_click(self):                         # SPECIFIC depending on the type of connection
		"""
		Dummy function to test the proper
		functioning of the log window and other widgets.
		On sending anything, it adds it to incoming_lines.
		:return:
		"""
		self.add_outgoing_lines_to_log()

		# ONLY FOR TESTING !!!! #
		# ECHOES ALL STRINGS SENT AS THEY WERE RECEIVED BACK #
		self.message_to_send = self.textbox_send_command.text()		# maybe better to do this with method input parameters, using class variables obfuscates its use.
		print("text gotten from textbox:", self.message_to_send)
		# self.incoming_lines.append("Received text:   " + self.message_to_send)

	def on_check_echo(self):
		val = self.check_echo.checkState()
		if(val == 0):
			self.echo_flag = False
		else:
			self.echo_flag = True
		logging.debug(self.echo_flag)

	# def parse_bytes(self,bytes):                                         					# maybe include this method onto the serial widget, and add different parsing methods.
	# 	logging.debug("parse_bytes() method called")
	# 	try:
	# 		char_buffer = self.readed_bytes.decode("utf-8", errors = "ignore") 	# convert bytes to characters, so now variables make reference to chars
	# 		self.readed_bytes = b''                                             			# clean serial_bytes, or it will keep adding data
	# 	except Exception as e:
	# 		logging.debug(self.SEPARATOR)
	# 		logging.debug(e)
	#
	# 	else:
	# 		# logging.debug(SEPARATOR)
	# 		# logging.debug("char_buffer variable :")
	# 		# logging.debug(char_buffer)
	# 		# logging.debug(type(char_buffer))                                    # is string, so ok
	# 		# logging.debug(SEPARATOR)
	# 		self.serial_data = self.incoming_data + char_buffer
	# 		logging.debug(self.SEPARATOR)
	# 		logging.debug("self.serial_data variable:")
	# 		logging.debug(self.incoming_data)
	# 		logging.debug(self.SEPARATOR)
	# 		endline_str = self.endline.decode("utf-8")              # this needs to be unified between socket and serial.
	# 		#endline_str = self.endline
	# 		data_lines = self.serial_data.split(endline_str)        # endlines are defined as n
	# 		logging.debug("str(self.endline)")
	# 		logging.debug(str(self.endline))
	# 		self.incoming_data = data_lines[-1]                     # clean the buffer, saving the non completed data_points
	#
	# 		complete_lines = data_lines[:-1]
	#
	# 		logging.debug(self.SEPARATOR)
	# 		logging.debug("complete_lines variable:")
	# 		for data_line in complete_lines:
	# 			logging.debug(data_line)
	#
	# 		for data_line in complete_lines:  # so all data points except last.
	# 			self.incoming_lines.append(data_line)

	# def add_incoming_lines_to_log(self):
	# 	pass

	def simulate_incoming_data(self):
		"""
		Used to simulate incoming data, as this widget is generic
		and no communication interface is implemented.
		:return: fake incoming data
		"""
		logging.warning("simulate_incoming_data method called")

		incoming_data = b"lorem ipsum dolor"
		incoming_data = incoming_data + b'\n'
		incoming_data = incoming_data + b"sit amet constectetuer"
		incoming_data = incoming_data + b'\n'

		print("incoming data before:", incoming_data)

		# # this is GETTING STUCK ACTUALLY not happening for whatever reason
		jmax = random.randint(10,20)
		imax = random.randint(10,100)
		for j in range(jmax):							# up to 20 random phrases.
			print("j="+str(j))
			for i in range(imax):						# with a lenght from 10, to 100
				print("i=" + str(i))
				incoming_data = incoming_data + bytes([random.randint(ord('0'), ord('z'))])
				print("incoming data:", incoming_data)

			incoming_data = incoming_data + b'\n'



		print("incoming data after random loop:", incoming_data)


		return(incoming_data)



class MainWindow(QMainWindow):
	# class variables #
	serial_bytes = b''                          # here we store what we get from serial port (get_byte_buffer)
	serial_data = ""                            # here the processed message(s) after parsing are stored
	#serial_lines = []                           # the serial data could contain several lines, this variable holds them.
	font_size = 10


	# constructor #
	def __init__(self):

		super().__init__()

		self.terminal = terminal_widget(log_window = True)
		self.terminal.print_timer.start(self.terminal.log_window_refresh_period)
		self.setCentralWidget(self.terminal)
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