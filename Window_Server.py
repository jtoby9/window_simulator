from LED_Strip import LED_Strip
import time
import os
import sys
import socket
import logging
import subprocess
import calendar
import re

# Class that encapsulates a TCP server and remote interface
class Window_Server:
    # ATTRIBUTES
    # commands (list of string triples): A list containing every accepted command,
    # identifier (string): The unique identifier that every sensor box has
    # hostname (string): The IPv4 address that is exposed to the client
    # filepath (string): The absolute path to the directory containing this file
    # tcp_port (int): The port to try binding the TCP socket to
    # buf_size (int): The maximum number of bytes to receive from the client
    # socket_timeout (int): Number of seconds before timing out on blocking socket operations
    # logger (Logger): Object that writes to the log file
    
    # Constructor. Sets up server to be run
    def __init__(self, commands, hostname, tcp_port, buf_size, socket_timeout, initial_mode):
        # Initialize attributes
        self.commands = commands
        self.hostname = hostname
        self.filepath = os.path.dirname(os.path.realpath(__file__))
        self.tcp_port = tcp_port
        self.buf_size = buf_size
        self.socket_timeout = socket_timeout

        # Set up logger object
        self.logger = logging.getLogger(__name__)
        
        # Construct LED strip
        self.led_strip = LED_Strip(initial_mode)
        
    # Runs the server indefinitely
    def run(self):
        # Open socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            self.logger.info("Opened socket at " + self.hostname + ", " + str(self.tcp_port))
            tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_socket.bind((self.hostname, self.tcp_port))
            # Accept connection from clients indefinitely
            while True:
                self.connect_to_client(tcp_socket)

    # Listen for a connection from a client, then accept commands from them
    # until they disconnect
    def connect_to_client(self, tcp_socket):
        self.logger.info("Listening for connection from client")
        tcp_socket.listen()
        conn, addr = tcp_socket.accept()
        # At this point, connection received
        with conn:
            self.logger.info("Connected to client at " + str(addr))
            conn.settimeout(self.socket_timeout)
            client_connected = True

            # Accept commands from the client until they end the connection
            while client_connected:
                try:
                    command = conn.recv(self.buf_size).decode('utf-8').rstrip("\r")
                    # Blank line means that the client ended the connection
                    if command == '':
                        self.logger.info("Client ended connection")
                        break

                    # Parse command and send reply
                    reply = self.parse_command(command, conn)
                    conn.sendall((reply + "\n").encode("utf-8"))
                    self.logger.debug("Sent reply " + reply)
                except socket.timeout:
                    client_connected = False
                    self.logger.warning("Timed out waiting for command. Disconnecting")
                except ConnectionResetError:
                    client_connected = False
                    self.logger.warning("Client forcibly closed connection. Disconnecting")
                except BadMessage as e:
                    client_connected = False
                    self.logger.error(str(e) + ". Disconneting")

    # Take command, return reply
    def parse_command(self, command, conn):
        # Parse command
        self.logger.debug("Received command " + command)
        fields = list(filter(None, re.split(" |,", command))) # split by comma or space, remove empty string
        cmd_name = fields[0] # The first field is always the name
        reply = "Default reply - if you see this, someone missed an edge case"
        

        # Help
        if cmd_name == "help":
            # Print table of commands/arguments/descriptions
            reply = "\n{:<16}{:<32}{}\n".format("Command", "Argument(s)", "Description")
            for i in self.commands:
                reply += "{:<16}{:<32}{}\n".format(i[0], i[1], i[2])

        
        # Alarm
        elif cmd_name == "alarm":
            # If there are no arguments display the alarms
            if len(fields) == 1:
                reply = self.led_strip.alarm_string()
            else:
                try:
                    day_arg = command.split()[1]
                    if day_arg == "mon":
                        days = [0]
                    elif day_arg == "tue":
                        days = [1]
                    elif day_arg == "wed":
                        days = [2]
                    elif day_arg == "thu":
                        days = [3]
                    elif day_arg == "fri":
                        days = [4]
                    elif day_arg == "sat":
                        days = [5]
                    elif day_arg == "sun":
                        days = [6]
                    elif day_arg == "weekday":
                        days = [0, 1, 2, 3, 4]
                    elif day_arg == "weekend":
                        days = [5, 6]
                    else:
                        raise ValueError('First argument was not a 3-letter day, "weekday" or "weekend"')
                    reply = ""
                    for day in days:
                        time = command.split()[2].split(":")
                        hour = int(time[0])
                        minute = int(time[1])
                        reply += "\n" + self.led_strip.set_alarm(day, hour, minute)
                except (ValueError, IndexError) as e:
                    reply = "Didn't set alarm, encountered error: " + str(e)

        # Snooze
        elif cmd_name == "snooze":
            # Call the snooze setter with on or off depending on the arguments
            if len(fields) == 2 and fields[1] == "off":
                reply = self.led_strip.set_snooze(on=False)
            elif len(fields) == 1:
                reply = self.led_strip.set_snooze(on=True)
            else:
                reply = "Didn't set snooze, encountered error"
                
        # Rainbow
        elif cmd_name == "rainbow":
            self.led_strip.set_mode("rainbow")
            # reply = "Come the dawn"
            reply = "Set mode to rainbow"
            
        # Solid color (color, max, r/g/b/w)
        elif cmd_name in ["color", "c", "max", "m", "r", "g", "b", "w", "rg", "rb", "rw", "gb", "gw", "bw", "rgb", "rgw", "rbw", "gbw", "rgbw"]:
            try:
                # Check if any of the values are invalid
                for color in fields[1:]:
                    if not 0 <= int(color) <= 255:
                        raise ValueError
                
                # Set default color values to 0
                r, g, b, w = 0, 0, 0, 0
                
                # Full color
                if "c" in cmd_name:
                    r = int(fields[1])
                    g = int(fields[2])
                    b = int(fields[3])
                    if len(fields) > 4:
                        w = int(fields[4])
                    
                # Single colors
                if "m" in cmd_name: 
                    r, g, b, w = 255, 255, 255, 255
                if "r" in cmd_name: # there is an r in color as well but that's ok
                    r = int(fields[1])
                if "g" in cmd_name:
                    g = int(fields[1])
                if "b" in cmd_name:
                    b = int(fields[1])
                if "w" in cmd_name:
                    w = int(fields[1])

                self.led_strip.set_mode("color", [r, g, b, w])
                reply = "LEDs set to ({}, {}, {}, {})".format(r, g, b, w)
            except (ValueError, IndexError) as e:
                reply = "Invalid color"

        # Fade
        elif cmd_name == "fade":
            # If there is no white argument, use the default
            try:
                if len(fields) == 1:
                    white = 20
                else:
                    white = int(fields[1])
                    if not 0 <= white < 256:
                        raise ValueError
                self.led_strip.set_mode("fade", [white])
                # reply = "I feel it fade"
                reply = "Set mode to fade"
            except ValueError as e:
                reply = "Invalid white value"
                

        # Strobe
        elif cmd_name == "strobe":
            self.led_strip.set_mode("strobe")
            # reply = "Alexa play Strobe - deadmau5"
            reply = "Set mode to strobe"

        # Random
        elif cmd_name == "random":
            self.led_strip.set_mode("random", params=[128, 128, 128])
            # reply = "Walter"
            reply = "Set mode to random"

        # Cylon
        elif cmd_name == "cylon":
            self.led_strip.set_mode("cylon")
            # reply = "Lol nerd"
            reply = "Set mode to cylon"

        # Scroll
        elif cmd_name == "scroll":
            self.led_strip.set_mode("scroll", params=[128, 128, 128])
            reply = "Set mode to scroll"

        # Cascade
        elif cmd_name == "cascade":
            self.led_strip.set_mode("cascade")
            reply = "Set mode to cascade"

        # Read
        elif cmd_name == "read":
            self.led_strip.set_mode("read")
            reply = "Set mode to read"

        # Read2
        elif cmd_name == "read2":
            self.led_strip.set_mode("read2")
            reply = "Set mode to read2"

        # Off
        elif cmd_name == "off" or cmd_name == "o":
            self.led_strip.set_mode("off")
            # reply = "I'm turned off"
            reply = "Set mode to off"
            
        # Restart
        elif cmd_name == 'restart':
            self.logger.info("Restarting service")
            return_code = subprocess.run(["sudo", "systemctl", "restart", "window_simulator.service"]).returncode
            self.logger.critical("Should have restarted service. Systemctl return code: " + str(return_code) + 
                                 ". If you're running from the command line don't worry about this. Exiting")
            sys.exit()            

        # Reboot
        elif cmd_name == "reboot":
            self.logger.info("Rebooting")
            return_code = subprocess.run(["sudo", "reboot"]).returncode
            self.logger.critical("Should have rebooted. Did /sbin/reboot get added to sudoers?" + 
                                 " Reboot return code: " + str(return_code))
            sys.exit()            

        # Unrecognized command
        else:
            reply = "ERROR: Received unrecognized command " + command
            self.logger.error("Couldn't recognize command")
            
        return reply
        
    # Takes a socket and the number of fields to receive. Calls recv on the socket and if the number of fields in
    # the received data matches the number of fields expected, returns the received data as a string. If not, raises
    # a BadMessage exception that specifies whether it was a blank string or just the wrong number of fields.
    # This function should be used in place of conn.recv() anywhere besides accepting a command from the client
    def recv_string(self, conn, expected_fields):
        received_string = conn.recv(self.buf_size).decode("utf-8")
        # Blank string
        if received_string == "":
            raise BadMessage("Client disconnected unexpectedly")
        # Wrong number of fields
        elif len(received_string.split(",")) != expected_fields:
            raise BadMessage("Expected a message with " + str(number_of_fields) + " fields, got: " + received_string)
        else:
            return received_string
        
# Custom exception for when the client sends a message that is the wrong number of fields. This includes when the
# client sends a blank line (i.e. disconnects) at a time when they weren't expected to do so
class BadMessage(Exception):
    pass