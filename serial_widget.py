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
    QColor
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

#import pyqt_common_resources.pyqt_custom_palettes as pyqt_custom_palettes


# GLOBAL VARIABLES #

SERIAL_BUFFER_SIZE = 2000											    # buffer size to store the incoming data from serial, to afterwards process it.
SERIAL_TIMER_PERIOD_MS = 1000                                           # every 'period' ms, we read the whole data at the serial buffer
SEPARATOR = "----------------------------------------------------------"
RECEIVE_TEXT_COLOR = "red"
SEND_TEXT_COLOR = "green"
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

class MainWindow(QMainWindow):

    serial_bytes = b''                          # here we store what we get from serial port (get_byte_buffer)
    serial_data = ""                            # here the processed message(s) after parsing are stored
    serial_lines = []                           # the serial data could contain several lines, this variable holds them.
    logging.debug(type(serial_data))

    def __init__(self):

        self.print_timer = QTimer()  # we'll use timer instead of thread
        self.print_timer.timeout.connect(self.add_log_serial_lines)
        self.print_timer.start(500)  # period needs to be relatively short

        super().__init__()

        self.widget = QWidget()
        self.setCentralWidget(self.widget)
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
        self.serial = serial_widget()
        self.layout.addWidget(self.serial)
        self.serial_log_text = QTextEdit()
        self.serial_log_text.setMinimumHeight(60)
        self.serial_log_text.setReadOnly(True)
        self.layout.addWidget(self.serial_log_text)
        self.serial.new_data.connect(self.get_serial_bytes)
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)
        self.button_save_log = QPushButton("Save Log")
        self.button_save_log.clicked.connect(self.save_log)
        self.buttons_layout.addWidget(self.button_save_log)
        # add a separator here
        self.button_clear_log = QPushButton("Clear Log")
        self.button_clear_log.clicked.connect(self.clear_log)
        self.buttons_layout.addWidget(self.button_clear_log)


    def get_serial_bytes(self):
        self.serial_bytes = self.serial.get_byte_buffer()
        self.serial.clear_byte_buffer()                                         # as I need to return byte_buffer, I can't clean inside get_byte_buffer
    # triggered when there is new data available on serial_buffer




    def add_log_serial_lines(self):
        # NOTE: Be careful using print, better logging debug, as print doesn't follow the program flow when multiple threads.
        #logging.debug("print_serial_data() method called")
        #self.serial_data = self.parse_serial_bytes(self.serial_bytes)          # doing so, will smash the previously stored data, so don't!!!
        self.parse_serial_bytes(self.serial_bytes)                              # parse_serial_bytes already handles the modifications over serial_data
        #logging.debug(self.serial_data variable:)
        self.serial_data = ""                                                   # clearing variable, data is already used
        for line in self.serial_lines:
            if(line != ''):                                                     # do nothing in case of empty string
                color = QColor(RECEIVE_TEXT_COLOR)
                self.serial_log_text.setTextColor(color)
                l = ">> " + str(line)                                            # marking for incoming lines
                self.serial_log_text.append(l)
        self.serial_lines = []                                                  # data is already on text_edit, not needed anymore









    def parse_serial_bytes(self,bytes):                                         # maybe include this method onto the serial widget, and add different parsing methods.
        logging.debug("parse_serial_bytes() method called")
        try:
            char_buffer = self.serial_bytes.decode('utf-8')                     # convert bytes to characters, so now variables make reference to chars
            self.serial_bytes = b''                                             # clean serial_bytes, or it will keep adding data
        except Exception as e:
            print(SEPARATOR)
            # print(e)
            self.serial.on_port_error(e)
        else:
            # logging.debug(SEPARATOR)
            # logging.debug("char_buffer variable :")
            # logging.debug(char_buffer)
            # logging.debug(type(char_buffer))                                    # is string, so ok
            # logging.debug(SEPARATOR)
            self.serial_data = self.serial_data + char_buffer
            logging.debug(SEPARATOR)
            logging.debug("self.serial_data variable:")
            logging.debug(self.serial_data)
            logging.debug(SEPARATOR)
            data_lines = self.serial_data.split(self.serial.endline)
            self.serial_data = data_lines[-1]  # clean the buffer, saving the non completed data_points

            complete_lines = data_lines[:-1]

            logging.debug(SEPARATOR)
            logging.debug("complete_lines variable:")
            for data_line in complete_lines:
                logging.debug(data_line)

            for data_line in complete_lines:  # so all data points except last.
                self.serial_lines.append(data_line)

    def save_log(self):
        # popup window to save in user defined location #
        name = QFileDialog.getSaveFileName(self,"Save File")
        print("Variable file:")
        #print(name)
        try:
            file = open(name[0],'w')                        # first parameter contains the name of the selected file.
            file.write(self.serial_log_text.toPlainText())
        except:
            logging.debug("Error saving to file")
    def clear_log(self):
        self.serial_log_text.clear()

class serial_widget(QWidget):
    # class variables #
    serial_ports = list # list of serial ports detected
    serial_port = None  # serial port used for the communication
    serial_connected = False
    c = False # variable to poll if port connected or not (useful for parent)
    serial_port_name = None  # used to pass it to the worker dealing with the serial port.
    serial_baudrate = 115200  # default baudrate
    endline = '\r\n'  # default value for endline is CR+NL
    error_type = None  # flag to transmit data to the error handling
    serial_message_to_send = None  # if not none, is a message to be sent via serial port
    timeouts = 0
    byte_buffer = b''  # all chars read from serial come here, should it go somewhere else?
    recording = False  # flag to start/stop recording.
    log_folder = "logs"  # in the beginning, log folder, path and filename are fixed
    log_file_name = "serial_log_file"  # all communication in and out (could be) collected here.
    log_file_type = ".txt"  # file extension
    log_full_path = None  # this variable will be the one used to record

    new_data = pyqtSignal()

    def __init__(self):
        super().__init__()

        # size policies #
        self.setMaximumHeight(100)
        self.setContentsMargins(0,0,0,0)

        #self.set
        # serial timer #
        self.serial_timer = QTimer()  # we'll use timer instead of thread
        self.serial_timer.timeout.connect(self.on_serial_timer)
        self.serial_timer.start(SERIAL_TIMER_PERIOD_MS)  # period needs to be relatively short
        self.serial_timer.stop()  # by default the timer will be off, enabled by connect.

        self.layout_serial = QHBoxLayout()
        self.layout_serial.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout_serial)
        # connect button #
        self.button_serial_connect = QPushButton("Connect")
        self.button_serial_connect.clicked.connect(self.on_button_connect_click)
        self.layout_serial.addWidget(self.button_serial_connect)
        # disconnect button #
        self.button_serial_disconnect = QPushButton("Disconnect")
        self.button_serial_disconnect.clicked.connect(self.on_button_disconnect_click)
        self.button_serial_disconnect.setEnabled(False)
        self.layout_serial.addWidget(self.button_serial_disconnect)
        # update button #
        self.button_serial_update = QPushButton("Update")
        self.button_serial_update.clicked.connect(self.on_button_update_click)
        self.layout_serial.addWidget(self.button_serial_update)
        # combo serial port #
        self.combo_serial_port = QComboBox()
        self.layout_serial.addWidget(self.combo_serial_port)
        self.update_serial_ports()
        self.combo_serial_port.currentTextChanged.connect(				# changing something at this label, triggers on_port select, which should trigger a serial port characteristics update.
            self.on_port_select)
        self.on_port_select(self.combo_serial_port.currentText())       # runs the method to ensure the port displayed at the textbox matches the port we're using
        self.label_port = QLabel("Port")
        self.layout_serial.addWidget(self.label_port)
        # combo serial speed #
        self.combo_serial_speed = QComboBox()
        self.combo_serial_speed.setEditable(False)						# by default it isn't editable, but just in case.
        self.combo_serial_speed.addItems(SERIAL_SPEEDS)
        self.combo_serial_speed.setCurrentIndex(9)						# this index corresponds to 115200 as default baudrate.
        self.combo_serial_speed.currentTextChanged.connect(				# on change on the serial speed textbox, we call the connected mthod
            self.change_serial_speed) 									# we'll figure out which is the serial speed at the method (would be possible to use a lambda?)
        self.layout_serial.addWidget(self.combo_serial_speed)				#
        self.label_baud = QLabel("baud")
        self.layout_serial.addWidget(self.label_baud)
        # text box command #
        self.textbox_send_command = QLineEdit()
        self.textbox_send_command.returnPressed.connect(self.send_serial)	# sends command via serial port
        self.textbox_send_command.setEnabled(False)						# not enabled until serial port is connected.
        self.layout_serial.addWidget(self.textbox_send_command)
        # send button #
        self.b_send = QPushButton("Send")
        self.b_send.clicked.connect(self.send_serial)					# same action as enter in textbox
        self.layout_serial.addWidget(self.b_send)
        # combo endline #
        self.combo_endline_params = QComboBox()
        self.combo_endline_params.addItems(ENDLINE_OPTIONS)
        self.combo_endline_params.setCurrentIndex(3)					# defaults to endline with CR & NL
        self.combo_endline_params.currentTextChanged.connect(self.change_endline_style)
        self.layout_serial.addWidget(self.combo_endline_params)

    # methods #

    def on_serial_timer(self):
        #logging.debug("On_serial_timer")
        readed_bytes = b''
        # print("Byte Buffer:")
        # print(byte_buffer)
        # print("(type(byte_buffer))")
        # print(type(byte_buffer))
        # print(type(self.read_buffer))
        try:
            readed_bytes = self.serial_port.read(SERIAL_BUFFER_SIZE)  # up to 1000 or as much as in buffer.
        except Exception as e:
            self.on_port_error(e)
            self.on_button_disconnect_click()  # we've crashed the serial, so disconnect and REFRESH PORTS!!!

        #print(byte_buffer)
        # after collecting some data on the byte buffer, store it in a static variable, and
        # emit a signal, so another window can subscribe to it, and handle the data when needed.
        self.new_data.emit()
        self.byte_buffer = self.byte_buffer + readed_bytes            # only reading the bytes, but NO PARSING

    def serial_connect(self, port_name):
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
            #self.status_bar.showMessage("Connected")
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
            print("PORT ALREADY OPEN BY THIS APPLICATION")
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

    def on_button_connect_click(self):  # this button changes text to disconnect when a connection is succesful.
        logging.debug("Connect Button Clicked")  # how to determine a connection was succesful ???
        self.button_serial_connect.setEnabled(False)
        self.button_serial_disconnect.setEnabled(True)
        self.combo_serial_port.setEnabled(False)
        self.button_serial_update.setEnabled(False)
        self.combo_serial_speed.setEnabled(False)
        self.combo_endline_params.setEnabled(False)
        self.textbox_send_command.setEnabled(True)
        #self.status_bar.showMessage("Connecting...")  # showing sth is happening.
        self.start_serial()

        self.first_toggles = 0

    def on_button_disconnect_click(self):
        print("Disconnect Button Clicked")
        self.button_serial_disconnect.setEnabled(False)  # toggle the enable of the connect/disconnect buttons
        self.button_serial_connect.setEnabled(True)
        self.button_serial_update.setEnabled(True)
        self.combo_serial_port.setEnabled(True)
        self.combo_serial_speed.setEnabled(True)
        self.combo_endline_params.setEnabled(True)
        self.textbox_send_command.setEnabled(False)
        self.byte_buffer = b''                          # clear byte buffer
        self.serial_connected = False
        #self.status_bar.showMessage("Disconnected")    # showing sth is happening.
        try:
            self.serial_port.close()
        except:
            print("Tried  to close serial port, but was already closed")
        self.serial_timer.stop()
        print(SEPARATOR)

    def on_button_update_click(self):  # this button changes text to disconnect when a connection is succesful.
        logging.debug("Update Button Clicked")  # how to determine a connection was succesful ???
        self.combo_serial_port.clear()
        self.get_serial_ports()  # meeded to list the serial ports at the menu

        if self.serial_ports != []:
            for port in self.serial_ports:  # adding all ports to combo box.
                port_name = port[0]
                item = self.combo_serial_port.addItem(port_name)  # add new items
        else:
            self.noserials = self.serial_port_menu.addAction("No serial Ports detected")
            self.noserials.setDisabled(True)

    def send_serial(self):  # do I need another thread for this ???
        print("Send Serial")
        logging.debug("Send Serial")
        command = self.textbox_send_command.text()  # get what's on the textbox.
        self.textbox_send_command.setText("")
        # here the serial send command #
        self.serial_message_to_send = command.encode('utf-8')  # this should have effect on the serial_thread

        logging.debug("serial_message_to_send")
        logging.debug(self.serial_message_to_send)
        self.serial_port.write(self.serial_message_to_send)

        # add here action trigger, so it can be catched by main window.


    # other methods #

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
                logging.debug(splitted_enum)  # uncomment this to see why this parameter was used to differentiate bt ports.
                last_param = splitted_enum[
                    -1]  # this contains the last parameter of the bt info, which is different between incoming and outgoing bt serial ports.
                last_field = last_param.split('_')  # here there is the real difference between the two created com ports
                last_field = last_field[-1]  # we get only the part after the '_'
                logging.debug(last_field)

                if (last_field == "C00000000"):  # this special string is what defines what are the valid COM ports.
                    discarded = 0  # the non-valid COM ports have a field liked this: "00000001", and subsequent.
                else:
                    discarded = 1
                    logging.debug("This port should be discarded!")
                    self.serial_ports.remove(port)  # removes by matching description

    def update_serial_ports(self):  # we update the list every time we go over the list of serial ports.
        # here we need to add an entry for each serial port avaiable at the computer
        # 1. How to get the list of available serial ports ?

       # self.serial_port_menu.clear()  # not existing in a monolythic widget.
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
                item = self.combo_serial_port.addItem(port_name)    # add new items
                self.serial_port_name = port_name                   # not the best, but works: update the name for the serial port to be used



        else:
            #self.noserials = self.serial_port_menu.addAction("No serial Ports detected")
            self.noserials.setDisabled(True)

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
        if (endline_style == ENDLINE_OPTIONS[0]):  # "No Line Adjust"
            self.endline = b""
        elif (endline_style == ENDLINE_OPTIONS[1]):  # "New Line"
            self.endline = b"\n"
        elif (endline_style == ENDLINE_OPTIONS[2]):  # "Carriage Return"
            self.endline = b"\r"
        elif (endline_style == ENDLINE_OPTIONS[3]):  # "Both NL & CR"
            self.endline = b"\r\n"

        logging.debug(self.endline)

    def start_serial(self):
        # first ensure connection os properly made
        self.serial_connect(self.serial_port_name)
        # 2. move status to connected
        # 3. start the timer to collect the data
        self.serial_timer.start()
        self.serial_connected = True
        # 4. Initialization stuff required by the remote serial device:
        #self.init_emg_sensor()

    def get_byte_buffer(self):
        return(self.byte_buffer)

    def clear_byte_buffer(self):
        self.byte_buffer = b''                              # read buffer contains bytes, so initialize to empty bytes



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # required to use it here
    window = MainWindow()
    # window.palette = pyqt_custom_palettes.dark_palette()
    # window.setPalette(window.palette)
    window.show()
    app.exec_()