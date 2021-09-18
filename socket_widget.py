

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

# custom imports #
from terminal_widget import terminal_widget

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
DEFAULT_IP = "192.168.0.7"

DEFAULT_PORT = 8051

SEPARATOR = "----------------------------------------------------------"

class socket_widget(terminal_widget):


    ip_address = None                                                                       # ip address of the remote device to be used
    port = None                                                                             # port to connect to
    socket = None                                                                           # socket object used to create the connection

    sock_message_to_send = None

    echo_flag = False

    def __init__(self, log_window = False):
        self.log_window_flag = log_window

        super().__init__()


        # self.set


        # self.layout_main = QVBoxLayout()
        # self.setLayout(self.layout_main)

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
        self.textbox_port.setText(str(DEFAULT_PORT))                                  # default port, so faster for debugging
        self.textbox_port.setEnabled(True)						        # not enabled until serial port is connected.
        self.layout_specific_connection.addWidget(self.textbox_port)


        # # connect button #
        # self.button_sock_connect = QPushButton("Connect")
        # self.button_sock_connect.clicked.connect(self.on_button_connect_click)
        # self.button_sock_connect.setEnabled(True)
        # self.layout_specific_connection.addWidget(self.button_connect)
        # # disconnect button #
        # self.button_sock_disconnect = QPushButton("Disconnect")
        # self.button_sock_disconnect.clicked.connect(self.on_button_disconnect_click)
        # self.button_sock_disconnect.setEnabled(False)
        # self.layout_specific_connection.addWidget(self.button_disconnect)


        # self.layout_send = QHBoxLayout()
        # self.layout_main.addLayout(self.layout_send)
        # # text box command #
        # self.textbox_send_command = QLineEdit()
        # self.textbox_send_command.returnPressed.connect(self.send_sock)	# sends command via serial port
        # self.textbox_send_command.setEnabled(False)						# not enabled until serial port is connected.
        # self.layout_send.addWidget(self.textbox_send_command)
        # # send button #
        # self.b_send = QPushButton("Send")
        # self.b_send.clicked.connect(self.send_sock)					# same action as enter in textbox
        # self.b_send.setEnabled(False)
        # self.layout_send.addWidget(self.b_send)
        # # checkbox echo#
        # self.check_echo = QCheckBox("Echo")
        # self.check_echo.setChecked(self.echo_flag)                        # whatever the default echo varaible value is
        # self.check_echo.clicked.connect(self.on_check_echo)
        # self.layout_send.addWidget(self.check_echo)

    #
    # def on_read_data_timer(self):
    #
    #     # try:
    #     #     self.socket.send(bytes('?', 'utf-8'))
    #     # except Error as e:
    #     #     logging.debug(e)
    #
    #
    #     try:
    #         bytes = self.socket.recv(1000)                                          # tested with 2000*8 samples on the ESP32 side
    #     except:
    #         logging.error("Couldn't read data from remote device")
    #         logging.error("Is the device still connected?")
    #         self.on_button_disconnect_click()                                       # maybe should be self.disconnect instead...
    #         d = QMessageBox.critical(
    #             self,
    #             "Remote device Unreachable",
    #             "Is not possible to reach the remote device, please check its battery status.\n"
    #             "If this message shows when the remote is working for sure, try to increase the connection timeout",
    #
    #             buttons=QMessageBox.Ok
    #         )
    #     else:
    #         chars = bytes.decode('utf-8')
    #         #print(chars)
    #         file = open("incoming_data.txt",'a', newline = '')
    #         logging.debug("saved to file")
    #
    #         file.write(chars)




    def on_read_data_timer(self):

        # try:
        #     self.socket.send(bytes('?', 'utf-8'))
        # except Error as e:
        #     logging.debug(e)


        try:
            bytes = self.socket.recv(1000)                                          # tested with 2000*8 samples on the ESP32 side
        except:
            logging.error("Couldn't read data from remote device")
            logging.error("Is the device still connected?")
            self.on_button_disconnect_click()                                       # maybe should be self.disconnect instead...
            d = QMessageBox.critical(
                self,
                "Remote device Unreachable",
                "Is not possible to reach the remote device, please check its battery status.\n"
                "If this message shows when the remote is working for sure, try to increase the connection timeout",

                buttons=QMessageBox.Ok
            )
        else:
            chars = bytes.decode('utf-8')
            #print(chars)
            file = open("incoming_data.txt",'a', newline = '')
            logging.debug("saved to file")

            file.write(chars)


    def on_button_connect_click(self):
        # get the ip and the port from the text fields, to use it to connect the socket #
        self.ip_address = self.textbox_ip.text()
        print(self.ip_address)
        self.port = int(self.textbox_port.text())
        print(self.port)

        # conecting the socket #
        try:
            self.socket = socket.socket()
            self.socket.connect((self.ip_address,self.port))
            self.socket.settimeout(5)                                               # very important TO KNOW IF SOCKET IS DEAD !!! 10s is probably a big and conservative value ATM.

        except:
            logging.exception("The socket couldn't connect")
        else:
            logging.debug("Socket connected")

        # enabling a timer to read in the incoming data of the socket #
        self.read_data_timer.start()

        print("PENIS")

        # UI changes #
        self.button_connect.setEnabled(False)
        self.button_disconnect.setEnabled(True)
        self.textbox_send_command.setEnabled(True)
        self.b_send.setEnabled(True)



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
        self.button_disconnect.setEnabled(False)
        self.button_connect.setEnabled(True)
        self.textbox_send_command.setEnabled(False)
        self.b_send.setEnabled(False)




        logging.debug("socket.disconnect finished")




    def save_ip(self):
        pass


    def send_sock(self):  # do I need another thread for this ???
        logging.debug("send_sock() method called")
        command = self.textbox_send_command.text()  # get what's on the textbox.
        self.textbox_send_command.setText("")
        # here the serial send command #
        self.sock_message_to_send = command.encode("utf-8")  # this should have effect on the serial_thread

        logging.debug("sock_message_to_send")
        logging.debug(self.sock_message_to_send)
        self.socket.send(self.sock_message_to_send)
        #self.new_message_to_send.emit()                         # emits signal, a new message is sent to slave.

        # TRIGGER THE SIGNAL A MESSAGE IS SENT --> SO WE CAN GET THE MESSAGE ON THE LOG WINDOW.


        # add here action trigger, so it can be catched by main window.

    def on_check_echo(self):
        val = self.check_echo.checkState()
        if(val == 0):
            self.echo_flag = False
        else:
            self.echo_flag = True
        logging.debug(self.echo_flag)


# MAIN WINDOW #################################################################################

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
    # window.palette = pyqt_custom_palettes.dark_palette()
    # window.setPalette(window.palette)
    window.show()
    app.exec_()

