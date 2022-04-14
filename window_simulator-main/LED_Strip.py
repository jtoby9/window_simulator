import Modes
import neopixel
import board
import time
from threading import Thread, Event, Lock
import logging
import random
import re
import queue

# Constants
H = 0 # hour index in alarms
M = 1 # minute index in alarms

class LED_Strip(Thread):
    # Constructor
    def __init__(self, stop_event, to_tcp_server, to_led_strip):      
        # Set up logger object
        self.logger = logging.getLogger(__name__)

        # Initialize Neopixel strip
        self.leds = neopixel.NeoPixel(
            pin = board.D18,
            n = 30,
            bpp = 4,
            brightness = 1,
            auto_write = False,
            pixel_order = neopixel.GRBW
        )
                                      
        # Initialize state
        self.mode = Modes.Color([0, 0, 0, 0])
                          
        # Initialize queues
        self.to_tcp_server = to_tcp_server
        self.to_led_strip = to_led_strip
                          
        # Initialize thread
        Thread.__init__(self, name="LED Strip")
        self.stop_event = stop_event
        Thread.start(self)
                
    # Run method
    def run(self):
        while not self.stop_event.is_set():
            try:
                # Receive messages from other threads
                try:
                    received_message = self.to_led_strip.get_nowait()
                    sender = received_message[0]
                    message = received_message[1]
                    reply = self.receive_message(message)
                    # Send the reply back to the sender thread if it needs a reply
                    if sender == "TCP_Server":
                        self.to_tcp_server.put_nowait(("LED_Strip", reply))
                    else:
                        self.logger.debug("Didn't send reply " + reply)
                        
                except queue.Empty:
                    pass
                
                # Cycle
                self.mode.cycle(self.leds)
                
            # Catch stray errors
            except Exception:
                self.logger.exception("Encountered uncaught exception")
                self.stop_event.set()

    # Receive a message and set mode accordingly. Return a reply saying whether or not the mode was set
    def receive_message(self, message):
        # Parse message
        self.logger.debug("Received message " + message)
        fields = list(filter(None, re.split(" |,", message))) # split by comma or space, remove empty string
        name = fields[0] # The first field is always the name
        args = fields[1:]
        reply = "Oops I missed an edge case"
        
        # Set the mode based on the message
        try: 
            # If the message starts with "modify", then modify the state
            if name == "modify":
                return self.mode.modify(args)
        
            # Otherwise, check if the message is a new mode
            mode_class = Modes.get_class(name)
            if mode_class is None:
                raise ValueError("Invalid mode name")
            self.mode = mode_class(args)
            reply = "Set mode to " + name
            self.logger.debug("Mode is " + self.mode.name)
            
        except (ValueError, IndexError) as e:
            reply = "Couldn't set mode, encountered error: " + str(e)
            
        return reply
    

