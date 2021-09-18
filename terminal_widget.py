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
logging.basicConfig(level=logging.DEBUG)			# enable debug messages


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

class terminal_widget(QWidget):
    # class variables #

    RECEIVE_TEXT_COLOR = "red"
    SEND_TEXT_COLOR = "green"
    SEPARATOR = "----------------------------------------------------------"

    connected = False
    message_to_send = None              # if not none, is a message to be sent via serial port
    echo_flag = False
    timeouts = 0
    byte_buffer = b''                   # all chars read from serial come here, should it go somewhere else?
    recording = False                   # flag to start/stop recording.
    log_window_flag = None              # when True, shows the reception log window, clear and save buttons, if not, means the data will be handled in a different way.
    log_folder = "logs"                 # in the beginning, log folder, path and filename are fixed
    log_file_name = "log_file"          # all communication in and out (could be) collected here.
    log_file_type = ".txt"              # file extension
    log_full_path = None                # this variable will be the one used to record
    read_data_timer_period = 100        # period in ms to read incoming data
    log_window_refresh_period = 100     # the log windows isn't updated inmediately, but every 100ms
    readed_bytes = b''                  # when reading data using the timer, it ends up in this variable

    endline = "\n"                      # requred to get the data properly interpreted


    new_data = pyqtSignal()             # signal triggered when new data is available, to be used by parent widget.
    new_message_to_send = pyqtSignal()  # a new message is sent to the slave, used by parent to, for example log it.

    def __init__(self, log_window = False):
        super().__init__()
        self.log_window_flag = log_window

        # data timer #
        self.read_data_timer = QTimer()  # we'll use timer instead of thread
        self.read_data_timer.timeout.connect(self.on_read_data_timer)
        self.read_data_timer.start(self.read_data_timer_period)  # period needs to be relatively short
        self.read_data_timer.stop()  # by default the timer will be off, enabled by connect.

        # log print timer #
        self.print_timer = QTimer()  # we'll use timer instead of thread
        self.print_timer.timeout.connect(self.add_lines_to_log)
        self.print_timer.start(self.log_window_refresh_period)  # period needs to be relatively short
        self.print_timer.stop()  # by default the timer will be off, enabled by connect.

        # size policies, COMMON#
        self.setMaximumHeight(100)
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
        self.textbox_send_command.returnPressed.connect(self.send_sock)	# sends command via serial port
        self.textbox_send_command.setEnabled(False)						# not enabled until serial port is connected.
        self.layout_send.addWidget(self.textbox_send_command)
        # send button #
        self.b_send = QPushButton("Send")
        self.b_send.clicked.connect(self.send_sock)					# same action as enter in textbox
        self.b_send.setEnabled(False)
        self.layout_send.addWidget(self.b_send)
        # checkbox echo#
        self.check_echo = QCheckBox("Echo")
        self.check_echo.setChecked(self.echo_flag)                        # whatever the default echo varaible value is
        self.check_echo.clicked.connect(self.on_check_echo)
        self.layout_send.addWidget(self.check_echo)

        # log window layout box #
        self.layout_log_window = QVBoxLayout()
        self.layout_main.addLayout(self.layout_log_window)
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(60)
        self.log_text.setFontPointSize(10)
        self.log_text.setReadOnly(True)
        self.layout_log_window.addWidget(self.log_text)

        # self.serial.new_data.connect(self.get_serial_bytes)
        # self.serial.new_message_to_send.connect(self.add_log_outgoing_command)

        self.buttons_layout = QHBoxLayout()
        self.layout_log_window.addLayout(self.buttons_layout)
        self.button_save_log = QPushButton("Save Log")
        self.button_save_log.clicked.connect(self.save_log)
        self.buttons_layout.addWidget(self.button_save_log)
        # add a separator here
        self.button_clear_log = QPushButton("Clear Log")
        self.button_clear_log.clicked.connect(self.clear_log)
        self.buttons_layout.addWidget(self.button_clear_log)


    #COMMON, BUT UNIMPLEMENTED: we read the data from the given input stream (serial or socket) on a timer basis
    # maybe it's interesting to consider doing it via SIGNAL TRIGGER
    def on_read_data_timer(self):
        pass
    # COMMON: every time this function is called, all completed lines are added to the log window
    def add_lines_to_log(self):
        pass

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
        self.log_text.clear()

    def on_button_connect_click(self):
        pass

    def on_button_disconnect_click(self):
        pass




    #
    #
    #     # size policies #
    #     #self.setMaximumHeight(100)     # as now the textbox is included in the widget, the policy needs to be different
    #     self.setContentsMargins(0,0,0,0)
    #     # general top layout #
    #     self.layout_general = QVBoxLayout()
    #     self.setLayout(self.layout_general)
    #     # CONNECT LAYOUT , which contains the specifis of each conection type #
    #     self.layout_connect = QHBoxLayout()
    #     self.layout_general.addLayout(self.layout_connect)
    #     # specific connection parameters for each type of connection (implemented in child class)
    #     self.layout_specifics = QHBoxLayout()
    #     self.layout_connect.addLayout(self.layout_specifics)
    #     # connect button #
    #     self.button_connect = QPushButton("Connect")
    #     self.button_connect.clicked.connect(self.on_button_connect_click)
    #     self.layout_connect.addWidget(self.button_connect)
    #     # disconnect button #
    #     self.button_disconnect = QPushButton("Disconnect")
    #     self.button_disconnect.clicked.connect(self.on_button_disconnect_click)
    #     self.button_disconnect.setEnabled(False)
    #     self.layout_connect.addWidget(self.button_disconnect)
    #     # SEND DATA DIVISION #
    #     self.layout_send = QHBoxLayout()
    #     self.layout_general.addLayout(self.layout_send)
    #     self.textbox_send = QLineEdit()
    #     self.textbox_send.returnPressed.connect(self.send)	# sends command via serial port
    #     self.textbox_send.setEnabled(False)						# not enabled until serial port is connected.
    #     self.layout_send.addWidget(self.textbox_send)
    #     # send button #
    #     self.button_send = QPushButton("Send")
    #     self.button_send.clicked.connect(self.send)					# same action as enter in textbox
    #     self.layout_send.addWidget(self.button_send)
    #     if(self.log_window_flag == True):
    #     # checkbox echo#
    #         self.check_echo = QCheckBox("Echo")
    #         self.check_echo.setChecked(self.echo_flag)                        # whatever the default echo varaible value is
    #         self.check_echo.clicked.connect(self.on_check_echo)
    #         self.layout_send.addWidget(self.check_echo)
    #     # RECEIVE DATA DIVISION #
    #         self.layout_receive = QVBoxLayout()
    #         self.layout_general.addLayout(self.layout_receive)
    #         # log text #
    #         self.log_text = QTextEdit()
    #         self.log_text.setMinimumHeight(60)
    #         self.log_text.setFontPointSize(10)
    #         self.log_text.setReadOnly(True)
    #         self.layout_receive.addWidget(self.log_text)
    #         # layout for the buttons related with the log
    #         self.layout_receive_buttons = QHBoxLayout()
    #         self.layout_receive.addLayout(self.layout_receive_buttons)
    #         self.button_save_log = QPushButton("Save Log")
    #         self.button_save_log.clicked.connect(self.save_log)
    #         self.layout_receive_buttons.addWidget(self.button_save_log)
    #         # add a separator here
    #         self.button_clear_log = QPushButton("Clear Log")
    #         self.button_clear_log.clicked.connect(self.clear_log)
    #         self.layout_receive_buttons.addWidget(self.button_clear_log)
    #
    #
    # # methods #

    # def connect(self):
    #     pass
    #
    #
    # def on_conn_error(self, e):  # triggered by the serial thread, shows a window saying port is used by sb else.
    #     pass
    #
    # def on_check_echo(self):
    #     val = self.check_echo.checkState()
    #     if(val == 0):
    #         self.echo_flag = False
    #     else:
    #         self.echo_flag = True
    #     logging.debug(self.echo_flag)
    #
    # def send(self):  # may I need another thread for this ???
    #     pass
    #
    #     # TRIGGER THE SIGNAL A MESSAGE IS SENT --> SO WE CAN GET THE MESSAGE ON THE LOG WINDOW.
    #
    #
    # #     # add here action trigger, so it can be catched by main window.
    # #
    # # def get_byte_buffer(self):
    # #     return(self.byte_buffer)
    # #
    # # def clear_byte_buffer(self):
    # #     self.byte_buffer = b''                              # read buffer contains bytes, so initialize to empty bytes
    #
    # def add_lines_to_log(self):
    #     pass
    #     # NOTE: Be careful using print, better logging debug, as print doesn't follow the program flow when multiple threads.
    #     logging.debug("add_lines_to_log() method called")
    #     #self.serial_data = self.parse_serial_bytes(self.serial_bytes)          # doing so, will smash the previously stored data, so don't!!!
    #     #self.parse_bytes(self.readed_bytes)                                     # parse_serial_bytes already handles the modifications over serial_data
    #     #logging.debug(self.serial_data variable:)
    #     # self.serial_data = ""                                                   # clearing variable, data is already used
    #     # for line in self.lines:
    #     #     if(line != ''):                                                     # do nothing in case of empty string
    #     #         color = QColor(RECEIVE_TEXT_COLOR)
    #     #         self.serial_log_text.setTextColor(color)
    #     #         l = ">> " + str(line)                                            # marking for incoming lines
    #     #         self.serial_log_text.append(l)
    #     # self.serial_lines = []                                                  # data is already on text_edit, not needed anymore
    #
    # def parse_bytes(self,bytes):                                         # maybe include this method onto the serial widget, and add different parsing methods.
    #     logging.debug("parse_bytes() method called")
    #     try:
    #         char_buffer = self.readed_bytes.decode("utf-8", errors = "ignore")  # convert bytes to characters, so now variables make reference to chars
    #         self.readed_bytes = b''                                             # clean serial_bytes, or it will keep adding data
    #         logging.debug("data got into char_buffer")
    #     except Exception as e:
    #         logging.debug(SEPARATOR)
    #         # logging.debug(e)
    #         self.serial.on_port_error(e)
    #     else:
    #         # logging.debug(SEPARATOR)
    #         # logging.debug("char_buffer variable :")
    #         # logging.debug(char_buffer)
    #         # logging.debug(type(char_buffer))                                    # is string, so ok
    #         # logging.debug(SEPARATOR)
    #         self.read_data = self.read_data + char_buffer
    #         logging.debug(SEPARATOR)
    #         logging.debug("self.read_data variable:")
    #         logging.debug(self.read_data)
    #         logging.debug(SEPARATOR)
    #         endline_str = self.endline.decode("utf-8")
    #         data_lines = self.read_data.split(endline_str)        # endlines are defined as n
    #         logging.debug("str(self.serial.endline)")
    #         logging.debug(str(self.endline))
    #         self.read_data = data_lines[-1]  # clean the buffer, saving the non completed data_points
    #
    #         complete_lines = data_lines[:-1]
    #
    #         logging.debug(SEPARATOR)
    #         logging.debug("complete_lines variable:")
    #         for data_line in complete_lines:
    #             logging.debug(data_line)
    #
    #         for data_line in complete_lines:  # so all data points except last.
    #             self.serial_lines.append(data_line)
    #
    #
    #
    # def save_log(self):
    #     # popup window to save in user defined location #
    #     name = QFileDialog.getSaveFileName(self,"Save File")
    #     #logging.debug("Variable file:")
    #     #logging.debug(name)
    #     try:
    #         file = open(name[0],'w')                        # first parameter contains the name of the selected file.
    #         file.write(self.log_text.toPlainText())
    #     except:
    #         logging.debug("Error saving to file")
    # def clear_log(self):
    #     self.log_text.clear()
    #

class MainWindow(QMainWindow):
    # class variables #
    serial_bytes = b''                          # here we store what we get from serial port (get_byte_buffer)
    serial_data = ""                            # here the processed message(s) after parsing are stored
    serial_lines = []                           # the serial data could contain several lines, this variable holds them.
    font_size = 10


    # constructor #
    def __init__(self):

        super().__init__()

        # self.print_timer = QTimer()  # we'll use timer instead of thread
        # self.print_timer.timeout.connect(self.add_log_serial_lines)
        # self.print_timer.start(LOG_WINDOW_REFRESH_PERIOD_MS)  # period needs to be relatively short

        #self.widget = QWidget()
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
    window.palette = pyqt_custom_palettes.dark_palette()
    window.setPalette(window.palette)
    window.show()
    app.exec_()