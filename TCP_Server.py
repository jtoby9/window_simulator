from LED_Strip import LED_Strip
import Modes
import time
import os
import sys
import socket
import logging
from threading import Thread, Event, Lock
import subprocess
import calendar
import re
import queue

# Class that encapsulates a TCP server and remote interface
class TCP_Server(Thread):
    # ATTRIBUTES
    # commands (list of string triples): A list containing every accepted command,
    # hostname (string): The IPv4 address that is exposed to the client
    # tcp_port (int): The port to try binding the TCP socket to
    # buf_size (int): The maximum number of bytes to receive from the client
    # socket_timeout (int): Number of seconds before timing out on blocking socket operations
    # logger (Logger): Object that writes to the log file
    
    # Constructor. Sets up server to be run
    def __init__(self, stop_event, to_tcp_server, to_led_strip, to_alarm_clock, to_th_sensor):
        # Set up logger object
        self.logger = logging.getLogger(__name__)
        
        # Initialize attributes
        self.server_commands = {
            "help"      : self.command_help,
            "alarm"     : self.command_alarm,
            "th"        : self.command_th,
            "snooze"    : self.command_snooze,
            "restart"   : self.command_restart,
            "reboot"    : self.command_reboot,
        }
        self.macros = {
            "r?g?b?w?" : self.macro_rgbw,
            "off|o" : self.macro_off,
            "max|m" : self.macro_max,
            "c" : self.macro_color,
        }
            
        
        self.hostname = ""
        self.tcp_port = 12345
        self.buf_size = 65536
        self.socket_timeout = 1.0
        self.conn_timeout = 120.0

        # Initialize queues
        self.to_tcp_server = to_tcp_server
        self.to_led_strip = to_led_strip
        self.to_alarm_clock = to_alarm_clock
        self.to_th_sensor = to_th_sensor

        # Initialize thread
        Thread.__init__(self, name="TCP Server")
        self.stop_event = stop_event
        Thread.start(self)
        
        
    # Runs the server indefinitely
    def run(self):
        try:
            # Open socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                self.logger.info("Opened socket at " + self.hostname + ", " + str(self.tcp_port))
                tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                tcp_socket.bind((self.hostname, self.tcp_port))
                tcp_socket.settimeout(self.socket_timeout)
                # Accept connection from clients indefinitely
                while not self.stop_event.is_set():
                    self.connect_to_client(tcp_socket)
        # Catch stray errors
        except Exception:
            self.logger.exception("Encountered uncaught exception")
            self.stop_event.set()

    # Listen for a connection from a client, then accept commands from them until they disconnect
    def connect_to_client(self, tcp_socket):
        # Wait for a client to connect and time out if one doesn't connect in time
        try:
            tcp_socket.listen()
            conn, addr = tcp_socket.accept()
        except socket.timeout:
            return None
        # At this point, connection received
        with conn:
            self.logger.info("Connected to client at " + str(addr))
            conn.settimeout(self.conn_timeout)
            client_connected = True

            # Accept commands from the client until they end the connection
            while client_connected:
                try:
                    command = conn.recv(self.buf_size).decode('utf-8').rstrip("\r").lower()
                    # Blank line means that the client ended the connection
                    if command == '':
                        self.logger.info("Client ended connection")
                        break
                                
                    reply = self.parse_command(command)
                    conn.sendall((reply + "\n").encode("utf-8"))
                    self.logger.debug("Sent reply " + reply)
                    
                except socket.timeout:
                    client_connected = False
                    self.logger.warning("Timed out waiting for command. Disconnecting")
                except ConnectionResetError:
                    client_connected = False
                    self.logger.warning("Client forcibly closed connection. Disconnecting")

    # Take command, return reply
    def parse_command(self, command):
        # Parse command
        self.logger.debug("Received command " + command)
        fields = list(filter(None, re.split(" |,", command))) # split by comma or space, remove empty string
        name = fields[0] # The first field is always the name
        args = fields[1:]
        reply = "Oops I missed an edge case"
        
        # If the command is a server command, process it and return the reply
        if name in self.server_commands:
            return self.server_commands[name](command)
            
        # If the command is a macro, expand it and pass it on to the LED strip
        for pattern, expand_function in self.macros.items():
            if re.fullmatch(pattern, name):
                command = expand_function(name, args)
                break # Don't bother trying the rest of the patterns once a match is found
        
        # Send the command to the LED Strip
        self.to_led_strip.put_nowait(["TCP_Server", command])
        # Wait for a response
        try:
            reply = self.to_tcp_server.get(True, self.conn_timeout / 2)[1]
        except queue.Empty:
            reply = "Timed out waiting for the LED strip to respond"
        
        return reply

    # Returns reply for the help command
    def command_help(self, command):
        # If the argument is none then return the arg dict
        if command is None:
            return {"none" : "Displays a list of commands and what they do"}
            
        # Build the help string. Start with the header, then macros, then commands, then modes
        format_string = "{:<16}{:<32}{}\n"
        reply = format_string.format("Name", "Argument(s)", "Description")
        reply += "================================ MACROS =================================\n"
        for pattern, macro_function in self.macros.items():
            for arg, description in macro_function(None, None).items():
                reply += format_string.format(pattern, arg, description)
        reply += "=============================== COMMANDS ================================\n"                
        for command, command_function in self.server_commands.items():
            for arg, description in command_function(None).items():
                reply += format_string.format(command, arg, description)
                
        reply += "================================ MODES ==================================\n"                
        reply += Modes.mode_string(format_string)
        return reply
        

    # Returns reply for the alarm command
    def command_alarm(self, command):
        # If the argument is none then return the arg dict
        if command is None:
            return {
                "none" : "list alarms",
                '3-letter day/"weekend"/"weekday", time' : "set alarm",
            }
            
        # Pass the command to the alarm clock
        self.to_alarm_clock.put_nowait(["TCP_Server", command])
        # Return the reply
        try:
            reply = self.to_tcp_server.get(True, self.conn_timeout / 2)[1]
        except queue.Empty:
            reply = "Timed out waiting for the alarm clock to respond"
        
        return reply

    # Returns reply for the th command
    def command_th(self, command):
        # If the argument is none then return the arg dict
        if command is None:
            return {
                "none" : "display temperature (F) and % relative humidity measurement",
            }
            
        # Pass the command to the TH Sensor
        self.to_th_sensor.put_nowait(["TCP_Server", command])
        # Return the reply
        try:
            reply = self.to_tcp_server.get(True, self.conn_timeout / 2)[1]
        except queue.Empty:
            reply = "Timed out waiting for the alarm clock to respond"
        
        return reply

    # Returns reply for the snooze command
    def command_snooze(self, command):
        # If the argument is none then return the arg dict
        if command is None:
            return {
                "on" : "snooze next alarm",
                "off" : "don't snooze next alarm",
            }
            
        # Pass the command to the alarm clock
        self.to_alarm_clock.put_nowait(["TCP_Server", command])
        # Return the reply
        try:
            reply = self.to_tcp_server.get(True, self.conn_timeout / 2)[1]
        except queue.Empty:
            reply = "Timed out waiting for the alarm clock to respond"
        
        return reply

    # Returns reply for the restart command
    def command_restart(self, command):
        # If the argument is none then return the arg dict
        if command is None:
            return {"none" : "restart service"}
            
        self.logger.info("Restarting service")
        return_code = subprocess.run(["sudo", "systemctl", "restart", "window_simulator.service"]).returncode
        time.sleep(3)
        self.logger.critical("Should have restarted service. Systemctl return code: " + str(return_code) + 
                             ". If you're running from the command line don't worry about this. Exiting")
        sys.exit()            

    # Returns reply for the reboot command
    def command_reboot(self, command):
        # If the argument is none then return the arg dict
        if command is None:
            return {"none" : "reboot Pi"}
            
        self.logger.info("Rebooting")
        return_code = subprocess.run(["sudo", "reboot"]).returncode
        time.sleep(3)
        self.logger.critical("Should have rebooted. Did /sbin/reboot get added to sudoers?" + 
                             " Reboot return code: " + str(return_code))
        sys.exit()            

    # Macro function for rgbw
    def macro_rgbw(self, name, args):
        # If both arguments are none then return the arg dict
        if name is None and args is None:
            return {"0-255" : "Applies the specified intensity across the specified colors"}
            
        command = "color"
        intensity = args[0] # still a string
        for letter in "rgbw":
            command += " "
            if letter in name:
                command += intensity
            else:
                command += "0"
        return command

    # Macro function for off
    def macro_off(self, name, args):
        # If both arguments are none then return the arg dict
        if name is None and args is None:
            return {"none" : "Turn the lights off"}
            
        return "color 0 0 0 0"
    
    # Macro function for max
    def macro_max(self, name, args):
        # If both arguments are none then return the arg dict
        if name is None and args is None:
            return {"none" : "Turn the lights to the highest intensity"}
            
        return "color 255 255 255 255"
    
    # Macro function for color
    def macro_color(self, name, args):
        # If both arguments are none then return the arg dict
        if name is None and args is None:
            return {"same as color" : "Expands to color"}
            
        command = "color"
        for intensity in args:
            command += " " + intensity
        return command
                