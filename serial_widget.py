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

# GLOBAL VARIABLES #

SERIAL_BUFFER_SIZE = 1000												# buffer size to store the incoming data from serial, to afterwards process it.
SERIAL_TIMER_PERIOD_MS = 100                                             # every 'period' ms, we read the whole data at the serial buffer
SEPARATOR = "----------------------------------------------------------"
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

class serial_widget(QWidget):
    # class variables #
    serial_ports = list # list of serial ports detected
    serial_port = None  # serial port used for the communication
    serial_port_name = None  # used to pass it to the worker dealing with the serial port.
    serial_baudrate = 115200  # default baudrate
    endline = '\r\n'  # default value for endline is CR+NL
    error_type = None  # flag to transmit data to the error handling
    serial_message_to_send = None  # if not none, is a message to be sent via serial port
    timeouts = 0
    read_buffer = ''  # all chars read from serial come here, should it go somewhere else?
    recording = False  # flag to start/stop recording.
    log_folder = "logs"  # in the beginning, log folder, path and filename are fixed
    log_file_name = "serial_log_file"  # all communication in and out (could be) collected here.
    log_file_type = ".txt"  # file extension
    log_full_path = None  # this variable will be the one used to record

    def __init__(self):
        super().__init__()

        # serial timer #
        self.serial_timer = QTimer()  # we'll use timer instead of thread
        self.serial_timer.timeout.connect(self.on_serial_timer)
        self.serial_timer.start(SERIAL_TIMER_PERIOD_MS)  # period needs to be relatively short
        self.serial_timer.stop()  # by default the timer will be off, enabled by connect.

        self.layout_serial = QHBoxLayout()
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
        self.combo_serial_speed.setCurrentIndex(11)						# this index corresponds to 250000 as default baudrate.
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
        logging.debug("On_serial_timer")
        print("Byte Buffer:")
        byte_buffer = ''
        print(byte_buffer)
        print("(type(byte_buffer))")
        print(type(byte_buffer))
        print(type(self.read_buffer))
        try:
            byte_buffer = self.serial_port.read(SERIAL_BUFFER_SIZE)  # up to 1000 or as much as in buffer.
        except Exception as e:
            self.on_port_error(e)
            self.on_button_disconnect_click()  # we've crashed the serial, so disconnect and REFRESH PORTS!!!

        print(byte_buffer)
        #self.read_buffer = self.read_buffer + byte_buffer

        # if (self.parsing_style == "arduino"):
        #     self.add_arduino_data()
        # elif (self.parsing_style == "emg"):
        #     self.add_emg_sensor_data()

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

        except:
            logging.debug("UNKNOWN ERROR OPENING SERIAL PORT")

        else:  # IN CASE THERE'S NO EXCEPTION (I HOPE)
            logging.debug("SERIAL CONNECTION SUCCESFUL !")
            #self.status_bar.showMessage("Connected")
        # here we should also add going  to the "DISCONNECT" state.

        logging.debug("serial_port.is_open:")
        logging.debug(self.serial_port.is_open)
        logging.debug("done: ")

    # logging.debug(self.done)

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
        #self.status_bar.showMessage("Disconnected")  # showing sth is happening.
        self.serial_port.close()
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
        logging.debug("Send Serial")
        command = self.textbox_send_command.text()  # get what's on the textbox.
        self.textbox_send_command.setText("")
        # here the serial send command #
        self.serial_message_to_send = command.encode('utf-8')  # this should have effect on the serial_thread

        logging.debug("serial_message_to_send")
        logging.debug(self.serial_message_to_send)
        self.serial_port.write(self.serial_message_to_send)


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
        # 4. Initialization stuff required by the remote serial device:
        #self.init_emg_sensor()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QMainWindow()
    seria = serial_widget()
    window.setCentralWidget(seria)
    window.show()
    app.exec_()