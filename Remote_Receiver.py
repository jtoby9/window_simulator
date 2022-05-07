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
        self.wait_time = .1 # seconds
        # Button codes
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
        # Command for each button
        self.command_dict = {
            # Modes
            "power"         : "color 0 0 0 0",
            "netflix"       : "color 255 0 0 255",
            "mute"          : "color 255 255 255 255",
            "disney+"       : "read",
            "hulu"          : "read 2",
            "left"          : "fade",
            "right"         : "random",
            "ok"            : "rainbow",
            "back"          : "scroll",
            "home"          : "cascade",
            "vudu"          : "cylon",
            
            # Modifiers
            "up"            : "modify increase brightness",
            "down"          : "modify decrease brightness",
            "arrow"         : "modify increase r",
            "rewind"        : "modify decrease r",
            "moon"          : "modify increase g",
            "play/pause"    : "modify decrease g",
            "star"          : "modify increase b",
            "fast_forward"  : "modify decrease b",
            "volume_up"     : "modify increase w",
            "volume_down"   : "modify decrease w",       
        }
        
        # Set up GPIO
        self.pin = 17
        self.pi = pi
        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.callback = self.pi.callback(self.pin, pigpio.EITHER_EDGE, self.decode_pulse)

        # Initialize remote decoding parameters
        self.last_tick = 0
        self.current_code = 1
        self.codes_received = queue.Queue()
        self.pulse_done = 10000 # microseconds
        self.wait_time = 1 # seconds
        self.last_code_received = 0
        self.last_button_pressed = ""
        self.echo_gap = 500000 # microseconds

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
        code_done = False
        
        # If the pin has been high or low for a long time, then this code is done transmitting
        if pulse_length > self.pulse_done:
            code_done = True
            # Fix common errors
            if self.current_code.bit_length() > 34: # extra bits
                self.current_code = self.current_code >> (self.current_code.bit_length() - 34)
            if self.current_code > 0x200000000: # extra leading 1
                self.current_code -= 0x200000000
            if self.current_code & 0x100 and self.current_code % 2 == 0: # echo
                self.current_code -= 0xFF
        
        # Otherwise, decode the message based on low pulse length
        elif level == 0:
            self.current_code = self.current_code << 1
            # Logical 1 -> 1687.5us, logical 0 -> 562.5us. So split the difference
            if pulse_length > 1125:
                self.current_code += 1
                
        # If the current code is in the dictionary, then it is done transmitting
        code_done |= self.current_code in self.button_dict
            
        # If the current code is done trasmitting, put it in the queue and reset current code
        if code_done:
            self.codes_received.put_nowait((self.current_code, tick))
            self.current_code = 0     
                                
    # Run function
    def run(self):
        while not self.stop_event.is_set():
            try:
                remote_code, tick = self.codes_received.get(True, self.wait_time)
                if remote_code in self.button_dict:
                    button = self.button_dict[remote_code]
                    # If this code was just received, this is an echo
                    if button == self.last_button_pressed and tick - self.last_code_received < self.echo_gap:
                        self.logger.debug("Echo received on {} button, gap of {}us".format(button, tick - self.last_code_received))
                    # Otherwise, generate and send command
                    else:
                        self.logger.debug("IR receiver detected {} pressed, gap of {}us".format(button, tick - self.last_code_received))                    
                        if button in self.command_dict:
                            command = self.command_dict[button]
                        else:
                            self.logger.warning("Unknown button")
                            continue
                    
                        # Send the command to the LED strip
                        self.logger.debug("Sending " + command + " to LED strip")
                        self.to_led_strip.put_nowait(["Remote_Receiver", command])
                    self.last_code_received = tick
                    self.last_button_pressed = button
                else:
                    if remote_code > 0xFF: # Don't even bother logging garbage data if it's a byte or less
                        self.logger.debug("IR receiver received garbage data: " + hex(remote_code))
            except queue.Empty:
                pass
            except Exception:
                self.logger.exception("Encountered uncaught exception")
                self.stop_event.set()
            
