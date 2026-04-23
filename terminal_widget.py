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

logging.basicConfig(level=logging.WARNING)			# enable debug messages

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

	MAX_LINES_LOG_WINDOW = 1000

	def __init__(self):

		super().__init__()

		self.layout_log_window = QVBoxLayout()
		self.setLayout(self.layout_log_window)
		# self.layout_main.addLayout(self.layout_log_window, stretch=2)  # stretch doesn't work...
		self.log_text = QTextEdit()
		self.log_text.document().setMaximumBlockCount(
			self.MAX_LINES_LOG_WINDOW)  # makes sure there's a limit of lines in the log window
		self.log_text.setMinimumHeight(40)
		self.log_text.setFontPointSize(10)
		self.log_text.setReadOnly(True)
		self.layout_log_window.addWidget(self.log_text, stretch=2)

		# self.serial.new_data.connect(self.get_serial_bytes)
		# self.new_message_to_send.connect(self.add_outgoing_lines_to_log)		# !!! THIS IS A FIX BUT INCORRECT!

		self.buttons_layout = QHBoxLayout()
		self.layout_log_window.addLayout(self.buttons_layout)
		self.button_save_log = QPushButton("Save Log")
		self.button_save_log.clicked.connect(self.save_log)
		self.buttons_layout.addWidget(self.button_save_log)
		# add a separator here
		self.button_clear_log = QPushButton("Clear Log")
		self.button_clear_log.clicked.connect(self.clear_log)
		self.buttons_layout.addWidget(self.button_clear_log)


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


# logging.debug("self.log_window_flag")
# logging.debug(self.log_window_flag)
#
# if(self.log_window_flag == True):                           # this only works in "compilation" time.
# 	self.enable_log_window()
# elif(self.log_window_flag == False):                                                       # this only works in "compilation" time.
# 	self.disable_log_window()
# elif(self.log_window_flag == None):
# 	logging.warning("SOMETHING IS QUITE FUCKED UP ON LOG_WINDOW_FLAG")


class terminal_widget(QWidget):
	# class variables #

	RECEIVE_TEXT_COLOR = "red"
	SEND_TEXT_COLOR = "green"
	SEPARATOR = "----------------------------------------------------------"

	# LOG_WINDOW_REFRESH_PERIOD_MS = 5000  # maybe better to move to an event based system.
	MAX_TEXT_SIZE = 30
	MIN_TEXT_SIZE = 5

	MAX_BYTE_BUFFER_SIZE = 100000		# if bytebuffer exceeds this size without doing anything with the data, throws error and trims old data in buffer.
	READ_BLOCK_SIZE = 1000				# how big is the block to be read at once from a given input device.
	MAX_LINES_LOG_WINDOW = 2000			# maximum number of lines on log window, when limit reached old get discarded.

	connected = False
	message_to_send = None              # if not none, is a message to be sent via serial port
	echo_flag = True                   	# to enable/disable echoing sent messages to the log window
	timeouts = 0
	byte_buffer = b''                   # buffer where the received bytes are stored until used.
	readed_bytes = b''                  # bytes received in the last read
	recording = False                   # flag to start/stop recording.
	log_window_flag = True             	# when True, shows the reception log window, clear and save buttons, if not, means the data will be handled in a different way.
	log_folder = "logs"                 # in the beginning, log folder, path and filename are fixed
	log_file_name = "log_file"          # all communication in and out (could be) collected here.
	log_file_type = ".txt"              # file extension
	log_full_path = None                # this variable will be the one used to record
	service_timer_period = 10			# is for important things, so period is short
	read_data_timer_period = 50       # period in ms to read incoming data
	log_window_refresh_period =100     	# the log windows isn't updated inmediately, but every 100ms
	incoming_data = ""                  # characters converted from readed_bytes, to be converted in lines
	incoming_lines = []                 # contains all incoming data separated by lines, to print it on the log_window
	save_to_log_file = True				# by default, all data written to the log window will also be dumped to a logfile.

	log_window_buffer = []				# contains the data which is to be printed on the log window.
	log_file_buffer = []				# same for the data which has to be saved to file.

	# endline = b'\n'                   # default endline style
	endline = b'\r\n'

	new_data = Signal()             	# signal triggered when new data is available, to be used by parent widget.
	new_lines = Signal(list)
	connected_signal = Signal()			# other widgets need to know about the status of the connetion.
	disconnected_signal = Signal()
	# new_message_to_send = Signal()  # a new message is sent to the slave, used by parent to, for example log it.

	def __init__(self, log_window = True):

		super().__init__()

		logging.debug("log_window")
		logging.debug(log_window)

		self.log_window_flag = log_window

		# service timer #
		self.service_timer = QTimer()  									# for periodic checks, like buffers getting too big.
		self.service_timer.timeout.connect(self.on_service_timer)
		self.service_timer.start(self.service_timer_period)  # period needs to be relatively short
		# self.service_timer.stop()  # by default the timer will be off, enabled by connect.


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

		self.log_window = log_window_widget()
		self.layout_main.addWidget(self.log_window)

		# self.log_window_flag = False
		if(self.log_window_flag == False):
			self.log_window.setVisible(False)



	#COMMON, BUT UNIMPLEMENTED: we read the data from the given input stream (serial or socket) on a timer basis
	# maybe it's interesting to consider doing it via SIGNAL TRIGGER

	def on_service_timer(self):
		"""
		Used for checks about things exploding, for example:
		log_window_buffer = []	GETTING TOO BIG!
		log_file_buffer = [] GETTING TOO BIG!
		byte_buffer GETTING TOO BIG1
		NOTE: IF THIS DELAYS EXECUTION GET RID OF IT !!!
		:return:
		"""
		# logging.debug("on_service_timer()")
		if(len(self.byte_buffer) > self.MAX_BYTE_BUFFER_SIZE):
			logging.error("byte buffer full")
			logging.error("MAX_BYTE_BUFFER_SIZE:" + str(self.MAX_BYTE_BUFFER_SIZE))
			self.byte_buffer = self.byte_buffer[:self.MAX_BYTE_BUFFER_SIZE//2]											# // means integer division, or it will spit a float
		if(len(self.log_window_buffer) > 100000):
			logging.error("log_window_buffer full")


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
		# logging.error("on_read_data_timer()")
		try:
			self.readed_bytes = self.read_data()
			# self.log_window_buffer = self.readed_bytes
			# self.log_file_buffer = self.readed_bytes
			logging.debug("self.readed_bytes")
			logging.debug(self.readed_bytes)
		except Exception as e:
			logging.error("couldn't read bytes from anywhere")
		else:
			if(self.readed_bytes):
				self.new_data.emit()											# emit signal there's new data (as far as I know, unused for now)
				self.byte_buffer = self.byte_buffer + self.readed_bytes  		# add the new readed bytes to the buffer.
				self.log_file_buffer = self.byte_buffer							# until I figure out how to do it better CREATE TWO BUFFERS; ONE FOR THE LOG WINDOW AND ONE FOR THE LOG FILE
				self.log_window_buffer = self.log_window_buffer					# until I figure out how to do it better CREATE TWO BUFFERS; ONE FOR THE LOG WINDOW AND ONE FOR THE LOG FILE
				logging.debug("new input data")

				# self.byte_buffer, lines = self.get_complete_lines(self.byte_buffer)
				# self.add_incoming_lines_to_log(lines)

		logging.debug("self.readed_bytes")
		logging.debug(self.readed_bytes)
		logging.debug("self.byte_buffer")
		logging.debug(self.byte_buffer)

	def on_print_timer(self):
		# logging.error("on_print_timer()")
		# if (self.incoming_data[0] != '\0'):  # empty strings won't be saved to file
		logging.debug("log_window_flag");
		logging.debug(self.log_window_flag)
		if (self.log_window_flag == True):  # if the log window is disabled no need to do the job ???
			logging.debug("self.log_window_flag is True")
			self.log_window_buffer = self.log_window_buffer + [self.readed_bytes]
			# PRINT TO LOG WINDOW -->
			# should I keep the text printing to the log window just in case I decide to enable it interactively ???
			# KEEP IN MIND CASE THERE IS NO ENDLINE!!!
			self.byte_buffer, lines = self.get_complete_lines(self.byte_buffer)
			if lines:													# only if there are new lines, of course.
				self.new_lines.emit(lines)								# emits a signal to catch it from other widgets.
				self.add_incoming_lines_to_log(lines)					# add lines to log
		if (self.save_to_log_file == True):
			# SAVE TO LOGFILE #
			file = open("incoming_data.txt", 'a', newline='')  	# saving data to file.
			logging.debug("saved to file")
			file.write(self.incoming_data)
			# file.write(self.endline)
			file.write('\n')									# for writing to file, this may be the correct endline! ???
			chars = None  # indeed there's no new information/messages.

	def on_connected(self):
		"""
		Actions to be performed when connection is established
		:return:
		"""
		self.connected_signal.emit()

	def on_disconnected(self):
		"""
		Actions to be performed when connection is closed
		pass
		:return:
		"""
		self.disconnected_signal.emit()

	def get_complete_lines(self, buffer):
		if not buffer:
			return b'', []

		data_lines = buffer.split(self.endline)

		incomplete_line = data_lines[-1]
		complete_lines = [
			line.decode("utf-8", errors="ignore")
			for line in data_lines[:-1]
			if line != b''
		]

		return incomplete_line, complete_lines

	def enable_log_window(self):
		print("enable_log_window method called")
		self.log_window.setVisible(True)
		self.log_window.setMinimumHeight(300)  # add more space, so we can properly see the log window.
	def disable_log_window(self):
		print("disable_log_window method called")
		self.log_window.setVisible(False)
		self.setMaximumHeight(160)  # add more space, so we can properly see the log window.


	def add_incoming_lines_to_log(self,lines):
		# NOTE: Be careful using print, better logging debug, as print doesn't follow the program flow when multiple threads.
		logging.debug("add_incoming_lines_to_log() method called")

		# self.parse_bytes(self.readed_bytes)                                     # parse_serial_bytes already handles the modifications over serial_data
		# self.log_text.append(self.SEPARATOR)		# why a separator here?
		logging.debug("self.readed_bytes variable:")
		logging.debug(self.readed_bytes)
		# self.incoming_data = ""                                               # clearing variable, data is already used
		for line in lines:
			if(line != ''):                                                     # do nothing in case of empty string
				color = QColor(self.RECEIVE_TEXT_COLOR)
				self.log_window.log_text.setTextColor(color)
				l = ">> " + str(line)                                           # marking for incoming lines
				self.log_window.log_text.append(l)
		self.incoming_lines = []                                                # data is already on text_edit, not needed anymore

	def add_outgoing_lines_to_log(self,line):
		"""
		This method is used when we need to have local echo of the sent commands
		The current implementation is not great !!! --> find a better way to do this

		:return:
		"""
		logging.debug("add_outgoing_lines_to_log method called")
		if (self.echo_flag == True):
			logging.debug("echo flag enabled, echoing message on log window")
			color = QColor(self.SEND_TEXT_COLOR)								# sent text goes in green
			self.log_window.log_text.setTextColor(color)									# sent text goes in green
			l = "<< " + line									# messages sent add << in front instead of >>
			self.log_window.log_text.append(l)												# add to log

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
		self.print_timer.start(self.log_window_refresh_period)
		self.on_connected()

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
		# consider also starting stopping the print_timer()
		self.print_timer.stop()
		self.on_disconnected()





	def on_button_send_click(self):                         				# SPECIFIC depending on the type of connection
		"""
		Actions to perform when the send button is pressed.
		Get the text to be sent
		Add it to the log window if needed
		Add text to the self.message_to_send variable, so it is sent. 
		:return:
		"""
		self.message_to_send = self.textbox_send_command.text()				# messages to be sent happen also asynchronously # maybe better to do this with method input parameters, using class variables obfuscates its use.
		self.add_outgoing_lines_to_log(self.message_to_send)				# outgoing messages happens asynchronously (everytime we press send button)
		self.send_command(self.message_to_send)
		self.textbox_send_command.clear()
		# ONLY FOR TESTING !!!! #
		# ECHOES ALL STRINGS SENT AS THEY WERE RECEIVED BACK #
		# logging.debug("text gotten from textbox:", self.message_to_send)
		# self.incoming_lines.append("Received text:   " + self.message_to_send)

	def on_check_echo(self):
		val = self.check_echo.checkState()
		if(val == 0):
			self.echo_flag = False
		else:
			self.echo_flag = True
		logging.debug(self.echo_flag)

	def read_data(self):
		"""
		Used to SIMULATE incoming data, as this widget is generic
		and no communication interface is implemented.
		:return: fake incoming data
		"""
		logging.debug("simulate_incoming_data method called")
		incoming_data = b''									# defined, so it exists to return it.
		jackpot = random.randint(0,20)						# not every time we read there is data actually.
		logging.debug("jackpot = " + str(jackpot))
		if (jackpot == 0):

			incoming_data = b"lorem ipsum dolor"
			incoming_data = incoming_data + self.endline
			incoming_data = incoming_data + b"sit amet constectetuer"
			incoming_data = incoming_data + self.endline

			# # this is GETTING STUCK ACTUALLY not happening for whatever reason

			# extra layer of randomness:

			# print("JACKPOT !!!")

			jmax = random.randint(2,5)
			imax = random.randint(2,10)
			for j in range(jmax):							# up to 20 random phrases.
				# print("j="+str(j))
				for i in range(imax):						# with a lenght from 10, to 100
					# print("i=" + str(i))
					incoming_data = incoming_data + bytes([random.randint(ord('0'), ord('z'))])
					# print("incoming data:", incoming_data)

				incoming_data = incoming_data + self.endline

			# logging.debug("incoming data after random loop:", incoming_data)


		return(incoming_data)

	def send_command(self, command):
		"""
		SIMULATES sending the commands written on the terminal somewhere,
		as it is useful for debugging functionality of UI.
		also cleans the command textbox.
		:return:
		"""
		if(command):															# if command is an empty string, do nothing
			logging.debug("send_command() method called")
			self.textbox_send_command.setText("")								# clean content of textbox.
			logging.debug("Command sent:", command)


	def handle_comm_errors(self):
		"""
		To be extended at each specific communication widget
		:return:
		"""
		pass



class MainWindow(QMainWindow):
	# class variables #
	serial_bytes = b''                          # here we store what we get from serial port (get_byte_buffer)
	serial_data = ""                            # here the processed message(s) after parsing are stored
	font_size = 10


	# constructor #
	def __init__(self):

		super().__init__()

		self.terminal = terminal_widget(log_window = True)
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