import pigpio
import time
from threading import Thread, Event, Lock
import logging

class Button(Thread):
    # Constructor
    def __init__(self, pi, stop_event, to_led_strip):
        # Set up logger object
        self.logger = logging.getLogger(__name__)
               
        # Set up GPIO
        self.pin = 4
        self.pi = pi
        self.pi.set_mode(self.pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.pin, pigpio.PUD_DOWN)
        self.callback = self.pi.callback(self.pin, pigpio.EITHER_EDGE, self.button_callback)
        
        # Initialize debounce parameters
        self.debounce_time = 25000 # microseconds
        self.button_pressed = Event()
        self.wait_time = 1 # seconds
        
        # Initialize queue
        self.to_led_strip = to_led_strip
        
        # Initialize thread
        Thread.__init__(self, name="Button")
        self.stop_event = stop_event
        Thread.start(self)
        
    # Executes every time the button pin sees an edge. Sets the button pressed event if it is held high for long enough
    def button_callback(self, pin, level, tick):
        # If the edge is rising, record the time
        if level:
            self.last_rising_edge = tick
        # If the edge is falling, calculate the time the button has been high for
        else:
            high_time = tick - self.last_rising_edge
            # If the button has been high for longer than the debounce time, set the button pressed event
            if high_time > self.debounce_time:
                self.button_pressed.set()
            else:
                self.logger.debug("Off button received erroneous pulse of {} microseconds ".format(high_time))
                
                
    # Run function
    def run(self):
        while not self.stop_event.is_set():
            try:
                # If the button pressed event has been set, send a message to the LED strip to turn off
                if self.button_pressed.wait(self.wait_time):
                    self.logger.debug("Off button was pressed")
                    self.to_led_strip.put_nowait(["Button", "color 0 0 0 0"])
                    self.button_pressed.clear()
            except Exception:
                self.logger.exception("Encountered uncaught exception")
                self.stop_event.set()
            
