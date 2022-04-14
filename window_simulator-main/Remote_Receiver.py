import pigpio
import time
from threading import Thread, Event, Lock
import logging
import queue

class Remote_Receiver(Thread):
    # Constructor
    def __init__(self, pi, stop_event, to_led_strip):
        # Set up logger object
        self.logger = logging.getLogger(__name__)
        
        # Initialize remote receiver properties
        self.button_dict = {
            0x157e304fb: "mute",
            0x157e308f7: "volume_down",
            0x157e310ef: "vudu",
            0x157e31ee1: "arrow",
            0x157e32cd3: "rewind",
            0x157e330cf: "disney+",
            0x157e332cd: "play/pause",
            0x157e346b9: "moon",
            0x157e34ab5: "netflix",
            0x157e354ab: "ok",
            0x157e36699: "back",
            0x157e37887: "left",
            0x157e38679: "star",
            0x157e39867: "up",
            0x157e3aa55: "fast_forward",
            0x157e3b24d: "hulu",
            0x157e3b44b: "right",
            0x157e3c03f: "home",
            0x157e3cc33: "down",
            0x157e3e817: "power",
            0x157e3f00f: "volume_up",
        }
        self.wait_time = .1 # seconds
        
        # Set up GPIO
        self.pin = 17
        self.pi = pi
        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.callback = self.pi.callback(self.pin, pigpio.EITHER_EDGE, self.decode_pulse)

        # Initialize remote decoding parameters
        self.last_tick = 0
        self.current_code = 1
        self.codes_received = queue.Queue()
        self.pulse_done = 10000 # milliseconds
        self.wait_time = 1 # seconds

        # Initialize queue
        self.to_led_strip = to_led_strip
        
        # Initialize thread
        Thread.__init__(self, name="Remote Receiver")
        self.stop_event = stop_event
        Thread.start(self)
                
    # Executes every time the remote receiver pin changes value. Converts the pulse length to a remote code
    def decode_pulse(self, pin, level, tick):
        # Get pulse length
        pulse_length = tick - self.last_tick
        self.last_tick = tick
        
        # If the pin has been high or low for a long time, then this code is done transmitting
        if pulse_length > self.pulse_done:
            # Strip off extra characters
            if self.current_code.bit_length() > 34:
                self.current_code = self.current_code >> (self.current_code.bit_length() - 34)
            self.codes_received.put_nowait(self.current_code)
            self.current_code = 0
        
        # Otherwise, decode the message based on low pulse length
        elif level == 0:
            self.current_code = self.current_code << 1
            # Logical 1 -> 1687.5us, logical 0 -> 562.5us. So split the difference
            if pulse_length > 1125:
                self.current_code += 1
                
        # If the current code is in the dictionary, then it is done transmitting
        if self.current_code in self.button_dict:
            self.codes_received.put_nowait(self.current_code)
            self.current_code = 0     
                                
    # Run function
    def run(self):
        while not self.stop_event.is_set():
            try:
                remote_code = self.codes_received.get(True, self.wait_time)
                if remote_code in self.button_dict:
                    # Generate command
                    button = self.button_dict[remote_code]
                    self.logger.debug("IR receiver detected " + button + " pressed")                    
                    # Modes
                    if button == "power":
                        command = "color 0 0 0 0"
                        
                    elif button == "netflix":
                        command = "color 255 0 0 255"
                        
                    elif button == "disney+":
                        command = "read"
                        
                    elif button == "hulu":
                        command = "read 2"
                        
                    elif button == "left":
                        command = "fade"
                    
                    elif button == "right":
                        command = "random"
                        
                    elif button == "ok":
                        command = "rainbow"
                        
                    elif button == "back":
                        command = "scroll"
                        
                    elif button == "home":
                        command = "cascade"
                    
                    elif button == "vudu":
                        command = "cylon"
                        
                    elif button == "mute":
                        command = "color 128 128 128 128"
                        
                    # Modify
                    elif button == "up":
                        command = "modify increase brightness"
                        
                    elif button == "down":
                        command = "modify decrease brightness"
                        
                    elif button == "arrow":
                        command = "modify increase r"
                        
                    elif button == "rewind":
                        command = "modify decrease r"
                        
                    elif button == "moon":
                        command = "modify increase g"
                        
                    elif button == "play/pause":
                        command = "modify decrease g"
                        
                    elif button == "star":
                        command = "modify increase b"
                        
                    elif button == "fast_forward":
                        command = "modify decrease b"
                        
                    elif button == "volume_up":
                        command = "modify increase w"
                        
                    elif button == "volume_down":
                        command = "modify decrease w"
                                                
                    else:
                        self.logger.warning("Unknown button")
                        continue
                    
                    # Send the command to the LED strip
                    self.logger.debug("Sending " + command + " to LED strip")
                    self.to_led_strip.put_nowait(["Remote_Receiver", command])
                else:
                    if remote_code > 0xFF: # Don't even bother logging garbage data if it's a byte or less
                        self.logger.debug("IR receiver received garbage data: " + hex(remote_code))
            except queue.Empty:
                pass
            except Exception:
                self.logger.exception("Encountered uncaught exception")
                self.stop_event.set()
            
