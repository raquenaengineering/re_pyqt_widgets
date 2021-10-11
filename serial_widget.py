

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
	QMessageBox,														# Dialog with extended functionality.
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


class serial_widget(terminal_widget):

	# class constants #
	SERIAL_BUFFER_SIZE = 2000  # buffer size to store the incoming data from serial, to afterwards process it.

	# class variables #
	serial_ports = list  # list of serial ports detected
	serial_port = None  # serial port used for the communication
	serial_connected = False
	c = False  # variable to poll if port connected or not (useful for parent)
	serial_port_name = None  # used to pass it to the worker dealing with the serial port.
	serial_baudrate = None  # default baudrate

	endline = None  # no default value for endline, will be assigned on initialisation.
	error_type = None  # flag to transmit data to the error handling
	# terminal_widget has already message_to_send #serial_message_to_send = None  # if not none, is a message to be sent via serial port
	# terminal_widget #echo_flag = False
	timeouts = 0
	# terminal_widget #byte_buffer = b''  # all chars read from serial come here, should it go somewhere else?
	# terminal_widget log_folder = "logs"  # in the beginning, log folder, path and filename are fixed
	# terminal_widget log_file_name = "serial_log_file"  # all communication in and out (could be) collected here.
	#terminal_widget log_file_type = ".txt"  # file extension
	#terminal_widget log_full_path = None  # this variable will be the one used to record
	#terminal_widget echo_flag = False

	SERIAL_SPEEDS = [
		"300",
		"1200",
		"2400",
		"4800",
		"9600",
		"19200",
		"38400",
		"57600",
		"74880",
		"115200",
		"230400",
		"250000",
		"500000",
		"1000000",
		"2000000"
	]
	ENDLINE_OPTIONS = [
		"No Line Adjust",
		"New Line",
		"Carriage Return",
		"Both NL & CR"
	]

	def __init__(self, log_window=None):

		self.log_window_flag = log_window
		print("Log_window_flag parameter on socket_widget initialization")
		print(self.log_window_flag)

		super().__init__(
			log_window=self.log_window_flag)  # VERY IMPORTANT! Need to add the initialization parameters of the parent here!!!b

		# SPECIFIC ITEMS TO ADD TO LAYOUT_SPECIFIC_CONNECTION #
		# Button Update serial ports #
		self.button_update_ports = QPushButton("Update")
		self.layout_specific_connection.addWidget(self.button_update_ports)
		self.button_update_ports.clicked.connect(self.update_serial_ports)
		# port label #
		self.label_port = QLabel("Port:")
		self.layout_specific_connection.addWidget(self.label_port)
		# combo serial port #
		self.combo_serial_port = QComboBox()
		self.layout_specific_connection.addWidget(self.combo_serial_port)
		self.update_serial_ports()
		self.combo_serial_port.currentTextChanged.connect(
			# changing something at this label, triggers on_port select, which should trigger a serial port characteristics update.
			self.on_port_select)
		self.on_port_select(
			self.combo_serial_port.currentText())  # runs the method to ensure the port displayed at the textbox matches the port we're using

		# baud label #
		self.label_baud = QLabel("Baud:")
		self.layout_specific_connection.addWidget(self.label_baud)
		# combo serial speed #
		self.combo_serial_speed = QComboBox()
		self.combo_serial_speed.setEditable(False)  # by default it isn't editable, but just in case.
		self.combo_serial_speed.addItems(self.SERIAL_SPEEDS)
		self.combo_serial_speed.setCurrentIndex(9)  # this index corresponds to 115200 as default baudrate.
		self.combo_serial_speed.currentTextChanged.connect(
			# on change on the serial speed textbox, we call the connected mthod
			self.change_serial_speed)  # we'll figure out which is the serial speed at the method (would be possible to use a lambda?)
		self.change_serial_speed()  # sets the default serial speed (different from None)
		self.layout_specific_connection.addWidget(self.combo_serial_speed)  #

		# combo endline #
		self.combo_endline_params = QComboBox()
		self.combo_endline_params.addItems(self.ENDLINE_OPTIONS)
		self.combo_endline_params.setCurrentIndex(1)  # defaults to endline with NL
		self.combo_endline_params.currentTextChanged.connect(self.change_endline_style)
		self.change_endline_style()  # sets the default endline style
		self.layout_specific_connection.addWidget(self.combo_endline_params)

	def on_read_data_timer(self):
		logging.debug("on_read_data_timer()")
		try:
			self.readed_bytes = self.serial_port.read(self.SERIAL_BUFFER_SIZE)  # up to 1000 or as much as in buffer.
		except Exception as e:
			self.on_port_error(e)
			self.on_button_disconnect_click()  # we've crashed the serial, so disconnect and REFRESH PORTS!!!
		else:
			logging.debug("Chars:")
			logging.debug(self.SEPARATOR)
			logging.debug(self.incoming_data)
			logging.debug(self.SEPARATOR)
			logging.debug("Bytes:")
			logging.debug(self.SEPARATOR)
			logging.debug(self.readed_bytes)
			logging.debug(self.SEPARATOR)
			#if (self.incoming_data[0] != '\0'):  # empty strings won't be saved to file
			if(True):
				self.add_incoming_lines_to_log()  # print to log window (atm not working)
				file = open("incoming_data.txt", 'a', newline='')  # saving data to file.
				logging.debug("saved to file")
				file.write(self.incoming_data)
				file.write('\n')
				chars = None  # indeed there's no new information/messages.

				# logging.debug(byte_buffer)
				# after collecting some data on the byte buffer, store it in a static variable, and
				# emit a signal, so another window can subscribe to it, and handle the data when needed.
				self.new_data.emit()
				self.byte_buffer = self.byte_buffer + self.readed_bytes  # only reading the bytes, but NO PARSING

		logging.debug("self.readed_bytes")
		logging.debug(self.readed_bytes)
		logging.debug("self.byte_buffer")
		logging.debug(self.byte_buffer)






	def on_button_connect_click(self):  # this button changes text to disconnect when a connection is succesful.
		logging.debug("Connect Button Clicked")  # how to determine a connection was succesful ???
		self.button_connect.setEnabled(False)
		self.button_disconnect.setEnabled(True)
		self.combo_serial_port.setEnabled(False)
		self.button_update_ports.setEnabled(False)
		self.combo_serial_speed.setEnabled(False)
		self.combo_endline_params.setEnabled(False)
		self.textbox_send_command.setEnabled(True)
		# self.status_bar.showMessage("Connecting...")  # showing sth is happening.
		self.start_serial()

		self.first_toggles = 0
		# UI changes #
		self.button_connect.setEnabled(False)
		self.button_disconnect.setEnabled(True)
		self.textbox_send_command.setEnabled(True)
		self.b_send.setEnabled(True)
	def on_button_disconnect_click(self):
		logging.debug("on_button_disconnect_click() method called")
		self.button_disconnect.setEnabled(False)  # toggle the enable of the connect/disconnect buttons
		self.button_connect.setEnabled(True)
		self.button_update_ports.setEnabled(True)
		self.combo_serial_port.setEnabled(True)
		self.combo_serial_speed.setEnabled(True)
		self.combo_endline_params.setEnabled(True)
		self.textbox_send_command.setEnabled(False)
		self.byte_buffer = b''  # clear byte buffer
		self.serial_connected = False
		# self.status_bar.showMessage("Disconnected")    # showing sth is happening.
		try:
			self.serial_port.close()
		except:
			logging.warning("Tried  to close serial port, but was already closed")
		self.read_data_timer.stop()
		logging.debug(self.SEPARATOR)
	def on_button_send_click(self):  # do I need another thread for this ???
		self.send_serial()
	def send_serial(self):  # do I need another thread for this ???
		logging.debug("send_serial() method called")
		logging.debug("Send Serial")
		command = self.textbox_send_command.text()  # get what's on the textbox.
		self.textbox_send_command.setText("")
		# here the serial send command #

		self.message_to_send = command.encode("utf-8")  							# this should have effect on the serial_thread
		print("type of message_to_send")
		print(type(self.message_to_send))
		print("type of endline")
		print(type(self.endline))
		self.message_to_send = self.message_to_send + self.endline

		print("serial_message_to_send")
		print(self.message_to_send)
		self.serial_port.write(self.message_to_send)
		self.new_message_to_send.emit()  # emits signal, a new message is sent to slave.

		# TRIGGER THE SIGNAL A MESSAGE IS SENT --> SO WE CAN GET THE MESSAGE ON THE LOG WINDOW.

		# add here action trigger, so it can be catched by main window.



	def change_serial_speed(self):  # this function is useless ATM, as the value is asked when serial open again.
		logging.debug("change_serial_speed method called")
		text_baud = self.combo_serial_speed.currentText()
		baudrate = int(text_baud)
		# self.serial_port.baudrate.set(baudrate)
		self.serial_baudrate = baudrate
		logging.debug(text_baud)
	def change_endline_style(self):  # this and previous method are the same, use lambdas?
		logging.debug("change_endline_speed method called")
		endline_style = self.combo_endline_params.currentText()
		logging.debug(endline_style)
		# FIND A MORE ELEGANT AND PYTHONIC WAY TO DO THIS.
		if (endline_style == self.ENDLINE_OPTIONS[0]):  # "No Line Adjust"
			pass  # self.endline = b""                                        # doesn't seem to work with empty, and this is the character determining end of string.
		elif (endline_style == self.ENDLINE_OPTIONS[1]):  # "New Line"
			self.endline = b"\n"
		elif (endline_style == self.ENDLINE_OPTIONS[2]):  # "Carriage Return"
			self.endline = b"\r"
		elif (endline_style == self.ENDLINE_OPTIONS[3]):  # "Both NL & CR"
			self.endline = b"\r\n"

		logging.debug(self.endline)

		print("Endline:")
		print(self.endline)
	# TRIGGER THE SIGNAL A MESSAGE IS SENT --> SO WE CAN GET THE MESSAGE ON THE LOG WINDOW.

	# print("serial_message_to_send")
	# print(self.serial_message_to_send)
	# self.serial_port.write(self.serial_message_to_send)
	# self.new_message_to_send.emit()                         # emits signal, a new message is sent to slave.

	# add here action trigger, so it can be catched by main window.
	# ADDITIONAL TOOLS METHODS #
	# not to be displayed in the widget, but called by the menus of a main window

	def update_serial_ports(self):  # we update the list every time we go over the list of serial ports.
		# here we need to add an entry for each serial port avaiable at the computer
		# 1. How to get the list of available serial ports ?
		# self.serial_port_menu.clear()  # not existing in a monolythic widget.
		logging.debug("self.update_serial_ports() method called")
		self.combo_serial_port.clear()
		self.get_serial_ports()  # meeded to list the serial ports at the menu
		# 3. How to ensure which serial ports are available ? (grey out the unusable ones)
		# 4. How to display properly each available serial port at the menu ?
		logging.debug(self.serial_ports)
		if self.serial_ports != []:
			# for port in self.serial_ports:
			#     port_name = port[0]
			#     logging.debug(port_name)
			#     b = self.serial_port_menu.addAction(port_name)
			#     # WE WON'T TRIGGER THE CONNECTION FROM THE BUTTON PUSH ANYMORE.
			#     b.triggered.connect((lambda serial_connect, port_name=port_name: self.on_port_select(
			#         port_name)))  # just need to add somehow the serial port name here, and we're done.

			# here we need to add the connect method to the action click, and its result

			for port in self.serial_ports:  # same as adding all ports to action menu, but now using combo box.
				port_name = port[0]
				item = self.combo_serial_port.addItem(port_name)  # add new items
				self.serial_port_name = port_name  # not the best, but works: update the name for the serial port to be used
		else:
			# self.noserials = self.serial_port_menu.addAction("No serial Ports detected")
			self.noserials.setDisabled(True)
	def get_serial_ports(self):  # REWRITE THIS FUNCTION TO USE A DICTIONARY, AND MAKE IT WAY CLEANER !!!

		logging.debug('Running get_serial_ports')
		serial_port = None
		self.serial_ports = list(
			serial.tools.list_ports.comports())  # THIS IS THE ONLY PLACE WHERE THE OS SERIAL PORT LIST IS READ.

		port_names = []  # we store all port names in this variable
		port_descs = []  # all descriptions
		port_btenums = []  # all bluetooth enumerations, if proceeds
		for port in self.serial_ports:
			port_names.append(port[0])  # here all names get stored
			port_descs.append(port[1])
			port_btenums.append(port[2])

		for name in port_names:
			logging.debug(name)
		logging.debug("---------------------------------------------------")

		for desc in port_descs:
			logging.debug(desc)
		logging.debug("---------------------------------------------------")

		for btenum in port_btenums:
			logging.debug(btenum)
		logging.debug("---------------------------------------------------")

		# remove bad BT ports (windows creates 2 ports, only one is useful to connect)

		for port in self.serial_ports:

			port_desc = port[1]

			if (port_desc.find(
					"Bluetooth") != -1):  # Bluetooth found on description,so is a BT port (good or bad, dunno yet)

				# Using the description as the bt serial ports to find out the "good" bluetooth port.
				port_btenum = port[2]
				port_btenum = str(port_btenum)
				splitted_enum = port_btenum.split('&')
				logging.debug(
					splitted_enum)  # uncomment this to see why this parameter was used to differentiate bt ports.
				last_param = splitted_enum[
					-1]  # this contains the last parameter of the bt info, which is different between incoming and outgoing bt serial ports.
				last_field = last_param.split(
					'_')  # here there is the real difference between the two created com ports
				last_field = last_field[-1]  # we get only the part after the '_'
				logging.debug(last_field)

				if (last_field == "C00000000"):  # this special string is what defines what are the valid COM ports.
					discarded = 0  # the non-valid COM ports have a field liked this: "00000001", and subsequent.
				else:
					discarded = 1
					logging.debug("This port should be discarded!")
					self.serial_ports.remove(port)  # removes by matching description
	def on_port_select(self, port_name):  # callback when COM port is selected at the menu.
		# 1. get the selected port name via the text.
		# 2. delete the old list, and regenerate it, so when we push again the com port list is updated.
		# 3. create a thread for whatever related with the serial communication, and start running it.
		# . open a serial communication. --> this belongs to the thread.

		# START THE THREAD WHICH WILL BE IN CHARGE OF RECEIVING THE SERIAL DATA #
		# self.serial_connect(port_name)
		logging.debug("Method on_port_select called	")
		self.serial_port_name = port_name
		logging.debug(self.serial_port_name)
	def start_serial(self):
		# first ensure connection os properly made
		self.serial_connect(self.serial_port_name)
		# 2. move status to connected
		# 3. start the timer to collect the data
		self.read_data_timer.start()
		self.connected = True
	def serial_connect(self, port_name):								# serial_connect, could also be called simply connect, and
		logging.debug("serial_connect method called")
		logging.debug(port_name)
		logging.debug("port name " + port_name)

		try:  # closing port just in case was already open. (SHOULDN'T BE !!!)
			self.serial_port.close()
			logging.debug("Serial port closed")
			logging.debug(
				"IT SHOULD HAVE BEEN ALWAYS CLOSED, REVIEW CODE!!!")  # even though the port can't be closed, this message is shown. why ???
		except:
			logging.debug("serial port couldn't be closed")
			logging.debug("Wasn't open, as it should always be")

		try:  # try to establish serial connection
			self.serial_port = serial.Serial(  # serial constructor
				port=port_name,
				baudrate=self.serial_baudrate,
				# baudrate = 115200,
				# bytesize=EIGHTBITS,
				# parity=PARITY_NONE,
				# stopbits=STOPBITS_ONE,
				# timeout=None,
				timeout=0,  # whenever there's no dat on the buffer, returns inmediately (spits '\0')
				xonxoff=False,
				rtscts=False,
				write_timeout=None,
				dsrdtr=False,
				inter_byte_timeout=None,
				exclusive=None
			)

		except Exception as e:  # both port open, and somebody else blocking the port are IO errors.
			logging.debug("ERROR OPENING SERIAL PORT")
			self.on_port_error(e)

		else:  # IN CASE THERE'S NO EXCEPTION (I HOPE)
			logging.debug("SERIAL CONNECTION SUCCESFUL !")
		# self.status_bar.showMessage("Connected")
		# here we should also add going  to the "DISCONNECT" state.

		logging.debug("serial_port.is_open:")
		try:
			logging.debug(self.serial_port.is_open)
		except:
			logging.debug("No serial port object was created")
		logging.debug("done: ")
	def on_port_error(self, e):  # triggered by the serial thread, shows a window saying port is used by sb else.

		desc = str(e)
		logging.debug(type(e))
		logging.debug(desc)
		error_type = None
		i = desc.find("Port is already open.")
		if (i != -1):
			logging.debug("PORT ALREADY OPEN BY THIS APPLICATION")
			error_type = 1
			logging.debug(i)
		i = desc.find("FileNotFoundError")
		if (i != -1):
			logging.debug("DEVICE IS NOT CONNECTED, EVEN THOUGH PORT IS LISTED")
			error_type = 2  #
		i = desc.find("PermissionError")
		if (i != -1):
			logging.debug("SOMEONE ELSE HAS OPEN THE PORT")
			error_type = 3  # shows dialog the por is used (better mw or thread?) --> MW, IT'S GUI.

		i = desc.find("OSError")
		if (i != -1):
			logging.debug("BLUETOOTH DEVICE NOT REACHABLE ?")
			error_type = 4

		i = desc.find("ClearCommError")
		if (i != -1):
			logging.debug("DEVICE CABLE UNGRACEFULLY DISCONNECTED")
			error_type = 5

		# ~ i = desc.find("'utf-8' codec can't decode byte")			# NOT WORKING !!! (GIVING MORE ISSUES THAN IT SOLVED)
		# ~ if(i != -1):
		# ~ logging.debug("WRONG SERIAL BAUDRATE?")
		# ~ error_type = 6

		self.error_type = error_type

		# ~ logging.debug("Error on serial port opening detected: ")
		# ~ logging.debug(self.error_type)
		self.handle_errors_flag = True  # more global variables to fuck things up even more.
		self.handle_port_errors()
	def handle_port_errors(self):  # made a trick, port_errors is a class variable (yup, dirty as fuck !!!)

		if (self.error_type == 1):  # this means already open, should never happen.
			logging.warning("ERROR TYPE 1")
			d = QMessageBox.critical(
				self,
				"Serial port Blocked",
				"The serial port selected is in use by other application",
				buttons=QMessageBox.Ok
			)
		if (self.error_type == 2):  # this means device not connected
			logging.warning("ERROR TYPE 2")
			d = QMessageBox.critical(
				self,
				"Serial Device is not connected",
				"Device not connected.\n Please check your cables/connections.  ",
				buttons=QMessageBox.Ok
			)
		if (self.error_type == 3):  # this means locked by sb else.
			d = QMessageBox.critical(
				self,
				"Serial port Blocked",
				"The serial port selected is in use by other application.  ",
				buttons=QMessageBox.Ok
			)

			self.on_button_disconnect_click()  # resetting to the default "waiting for connect" situation
			self.handle_errors_flag = False
		if (self.error_type == 4):  # this means device not connected
			logging.warning("ERROR TYPE 4")
			d = QMessageBox.critical(
				self,
				"Serial Device Unreachable",
				"Serial device couldn't be reached,\n Bluetooth device too far? ",
				buttons=QMessageBox.Ok
			)
		if (self.error_type == 5):  # this means device not connected
			logging.warning("ERROR TYPE 5")
			d = QMessageBox.critical(
				self,
				"Serial Cable disconnected while transmitting",
				"Serial device was ungracefully disconnected, please check the cables",
				buttons=QMessageBox.Ok
			)
		if (self.error_type == 6):  # this means device not connected
			logging.warning("ERROR TYPE 6")
			d = QMessageBox.critical(
				self,
				"Serial wrong decoding",
				"There are problems decoding the data\n probably due to a wrong baudrate.",
				buttons=QMessageBox.Ok
			)
		self.on_button_disconnect_click()  # resetting to the default "waiting for connect" situation
		self.handle_errors_flag = False
		self.error_type = None  # cleaning unhnandled errors flags.


# 4. Initialization stuff required by the remote serial device:
# self.init_emg_sensor()

# MAIN WINDOW ##########################################################################################################

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
        self.serial_widget = serial_widget()
        self.layout.addWidget(self.serial_widget)
        #self.serial.new_data.connect(self.get_serial_bytes)
        #self.serial.new_message_to_send.connect(self.add_log_outgoing_command)

        # stylesheet, so I don't get blind with tiny characters #
        self.sty = "QWidget {font-size: 10pt}"
        self.setStyleSheet(self.sty)

        font = self.font()
        font.setPointSize(24)

## MAIN ################################################################################################################

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # required to use it here
    window = MainWindow()
    window.show()
    app.exec_()

