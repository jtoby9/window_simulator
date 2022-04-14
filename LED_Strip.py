import RPi.GPIO as GPIO
import neopixel
import board
import time
import datetime
import calendar
from threading import Thread, Event, Lock
import logging
import random
import pickle

# Constants
H = 0 # hour index in alarms
M = 1 # minute index in alarms

class LED_Strip(Thread):
    # Constructor
    def __init__(self, initial_mode="off"):      
        # Set up logger object
        self.logger = logging.getLogger(__name__)

        # Initialize Neopixel strip
        self.num_leds = 30
        self.leds = neopixel.NeoPixel(pin = board.D18,
                                      n = self.num_leds,
                                      bpp = 4,
                                      brightness = 1,
                                      auto_write = False,
                                      pixel_order = neopixel.GRBW)
                                      
        # Initialize state
        self.mode = initial_mode
        self.params = []
        self.mode_lock = Lock()
        self.alarm_last_set_on = -1
        self.alarm_last_rang_on = -1
        self.snooze_next_alarm = False
        self.snoozed_last_alarm = False
        self.next_alarm_time = datetime.datetime(1, 1, 1, 1, 1, 1)

        # Set alarm parameters
        self.alarm_length = 1200 # seconds
        self.alarm_max_brightness = 5
        self.alarm_num_steps = 1000
        
        # Load alarm from file
        self.alarm_filename = "/home/josh/window_simulator/alarms"
        with open(self.alarm_filename, 'rb') as alarm_file:
            self.alarms = pickle.load(alarm_file)
                          
        # Set other constants
        self.strobe_time = .2
        self.scroll_delta = .3
        self.cascade_increment = 8
        self.reading_color = (75, 0, 0, 75)
                          
        # Calculate dependent variables
        self.wait_time = float(self.alarm_length) / (float(self.alarm_num_steps) * 2)
                          
        # Initialize thread
        Thread.__init__(self, name="LED Strip")
        self.stop_event = Event()
        Thread.start(self)
        
        # Initialize off button
        self.off_button_pin = 4
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.off_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(self.off_button_pin, GPIO.RISING, callback=self.off_button_callback, bouncetime=50)
        self.turning_off = False 
        
    # Run method
    def run(self):
        try:
            while not self.stop_event.is_set():
                # If the current mode is not alarm, check if it should be
                if self.mode != "alarm":
                    # Get the current time
                    now = datetime.datetime.now()
                    today = now.weekday()
                    
                    # Check if the alarm was set today
                    if today != self.alarm_last_set_on:
                        # If the last alarm was snoozed, re-arm the alarm
                        if self.snoozed_last_alarm:
                            self.snooze_next_alarm = False
                        # Set the alarm time to the next alarm time
                        self.next_alarm = datetime.datetime(now.year, now.month, now.day, self.alarms[today][H], self.alarms[today][M], 0, 0)
                        self.alarm_last_set_on = today
                        self.logger.debug("Next alarm is " + self.next_alarm.strftime("%Y-%m-%d at %H:%M:%S"))
                        
                    # Check if it's time to ring the alarm
                    diff = self.next_alarm - now
                    if today != self.alarm_last_rang_on and 0 < diff.seconds < self.alarm_length / 2:
                        if self.snooze_next_alarm:
                            self.snoozed_last_alarm = True
                        else:
                            self.logger.debug("Activating alarm")
                            self.mode = "alarm"
                            self.params = [0, 0]
                            self.snoozed_last_alarm = False
                            self.alarm_last_rang_on = today
                            
                # If the off button is pressed, set mode to off (if not already off)
                if self.mode != "off" and self.turning_off:
                    self.turning_off = False
                    self.logger.debug("Turning off from button")
                    self.mode = "off"
                            
                # Regardless of the mode, lock mode and params and run cycle
                with self.mode_lock:
                    self.cycle()
        
        # Catch stray errors
        except Exception:
            self.logger.exception("Encountered uncaught exception")
            
    # Cycle. Do something according to mode/params. Should take no more than a few seconds
    def cycle(self):
        # Off - turn LEDS off and sleep for 100ms
        if self.mode == "off":
            self.color(0, 0, 0, 0, .1)
            
        # Alarm - gradually ramp up brightness until the alarm time, then stay on
        elif self.mode == "alarm":
            params = self.params
            # First half of the alarm
            if params[0] < self.alarm_num_steps:
                # Ramp up the brightness and run for the wait time
                params[0] += 1
                brightness = (self.alarm_max_brightness * self.num_leds) * (params[0] / self.alarm_num_steps)
                self.flatten(int(brightness), self.wait_time)
            # Second half of the alarm
            elif params[1] < self.alarm_num_steps:
                # Stay on at the maximum brightness for the wait time
                self.color(0, 0, self.alarm_max_brightness, self.alarm_max_brightness, self.wait_time)
                params[1] += 1
            # End of the alarm
            else:
                # When the number of steps has been reached, turn off
                params = []
                self.mode = "off"
                self.logger.debug("Alarm done")
            self.params = params

        # Rainbow - do the adafruit rainbow thing
        elif self.mode == "rainbow":
            # No idea how this works but it looks cool
            for i in range(255):
                for j in range(self.num_leds):
                    pixel_index = (j * 256 // self.num_leds) + i
                    pos = pixel_index & 255
                    if pos < 0 or pos > 255:
                        r = g = b = 0
                    elif pos < 85:
                        r = int(pos * 3)
                        g = int(255 - pos*3)
                        b = 0
                    elif pos < 170:
                        pos -= 85
                        r = int(255 - pos*3)
                        g = 0
                        b = int(pos*3)
                    else:
                        pos -= 170
                        r = 0
                        g = int(pos*3)
                        b = int(255 - pos*3)
                    self.leds[j] = (r, g, b, 0)
                self.leds.show()
                time.sleep(.001)

        # Color - turn the LEDs the specified color and sleep for 100ms
        elif self.mode == "color":
            self.color(self.params[0], self.params[1], self.params[2], self.params[3], .1)

        # Fade - fade in and out of a random color
        elif self.mode == "fade":
            white = self.params[0]
            # Choose random color
            r = random.random()
            g = random.random()
            b = random.random()
            # Fade in and out
            for i in list(range(256)) + list(range(256, -1, -1)):
                self.color(int(r * i), int(g * i), int(b * i), white, .005)

        # Strobe - flash lights
        elif self.mode == "strobe":
            # Flash all lights on and off
            for i in range(4):
                self.color(255, 255, 255, 255, self.strobe_time)
                self.color(0, 0, 0, 0, self.strobe_time)
            # Flash lights alternating
            for i in range(8):
                for j in range(self.num_leds):
                    brightness = 255 * ((i + j) % 2)
                    self.leds[j] = (brightness, brightness, brightness, brightness)
                self.leds.show()
                time.sleep(self.strobe_time / 2)
                self.color(0, 0, 0, 0, self.strobe_time / 2)

        # Random - Pick a random color and "walk" towards it
        elif self.mode == "random":
            # Choose random color
            new_r = random.randint(0, 255)
            new_g = random.randint(0, 255)
            new_b = random.randint(0, 255)
            
            # Walk towards it
            diff_r = new_r - self.params[0]
            diff_g = new_g - self.params[1]
            diff_b = new_b - self.params[2]
            steps = max(abs(diff_r), abs(diff_g), abs(diff_b))
            for i in range(steps):
                red_val = int(self.params[0] + diff_r * (i / steps))
                green_val = int(self.params[1] + diff_g * (i / steps))
                blue_val = int(self.params[2] + diff_b * (i / steps))
                self.color(red_val, green_val, blue_val, 0, .01)
            time.sleep(1)
            
            # Save the new values
            self.params = [new_r, new_g, new_b, 0]
            
        # Cylon
        elif self.mode == "cylon":
            for i in list(range(self.num_leds - 1)) + list(range(self.num_leds - 1, 0, -1)):
                self.color_one_led(i, (0, 0, 0, 10))
                self.leds.show()
                time.sleep(self.strobe_time / 50)
                
        # Scroll
        elif self.mode == "scroll":
            # Pick either R, G, or B
            value_to_change = random.randint(0, 2)
            # Either subtract the delta from it or add the delta to it
            if random.random() >= .5:
                self.params[value_to_change] += int(self.scroll_delta * (256 - self.params[value_to_change]))
            else:
                self.params[value_to_change] = int(self.params[value_to_change] * (1 - self.scroll_delta))
            self.queue_push(tuple(self.params + [0]), .05, False)

        # Cascade
        elif self.mode == "cascade":
            color = [0, 0, 0]
            # Pick two of R, G, or B to raise (in random order) and raise them 
            values = [0, 1, 2]
            values.remove(random.randint(0, 2))
            if random.random() >= .5:
                values.reverse()
            for value in values:
                for i in range(255 // self.cascade_increment):
                    color[value] += self.cascade_increment
                    self.queue_push(tuple(color + [0]), .05)
                
            # Pick two of R, G, or B to lower (in random order) and lower them 
            if random.random() >= .5:
                values.reverse()
            for value in values:
                for i in range(255 // self.cascade_increment):
                    color[value] -= self.cascade_increment
                    self.queue_push(tuple(color + [0]), .05)               
            
        # Read
        elif self.mode == "read":
            # Reading light
            for i in range(self.num_leds):
                if i in (19, 20, 21):
                    self.leds[i] = self.reading_color
                else:
                    self.leds[i] = (0, 0, 0, 0)
            self.leds.show()
                
        # Read2
        elif self.mode == "read2":
            # Reading light for both sides
            for i in range(self.num_leds):
                if i in (0, 1, 2, 19, 20, 21):
                    self.leds[i] = self.reading_color
                else:
                    self.leds[i] = (0, 0, 0, 0)
            self.leds.show()

                
        # Test - test something
        elif self.mode == "test":
            # Put test code here
            self.mode = "off"
                
        # Invalid mode - set mode to off
        else:
            self.logger.error("Invalid mode: " + self.mode)
            self.mode = "off"
            
    # Off button callback
    def off_button_callback(self, channel):
        if self.mode != "off":
            # Make sure the button stays on for 50ms
            button_pressed = True
            for i in range(10):
                time.sleep(.005)
                button_pressed &= GPIO.input(self.off_button_pin)
        
            if button_pressed:
                self.turning_off = True
                self.logger.debug("Off button was pressed")
            else:
                self.logger.debug("Off button received interference")
        
    # Takes a number from 0 to 7650 inclusive and distributes the brightness as
    # blue/white along the LEDs, calls show(), and waits
    def flatten(self, brightness, sleep_time):
        quotient = int(brightness // self.num_leds)
        remainder = int(brightness % self.num_leds)
        for i in range(self.num_leds):
            if i < remainder:
                self.leds[i] = (0, 0, quotient + 1, quotient + 1)
            else:
                self.leds[i] = (0, 0, quotient, quotient)
        self.leds.show()
        time.sleep(sleep_time)
        
    # Set one LED to one color, set everything else to another color. Does not call show()
    def color_one_led(self, index, color, other_color=(0, 0, 0, 0)):
        for i in range(self.num_leds):
            if i == index:
                self.leds[i] = color
            else:
                self.leds[i] = other_color
                
    # Shift the LED colors either left or right, set the remaining LED to the specified
    # color, call show() and wait
    def queue_push(self, color, sleep_time, dir_is_right=True):
        if dir_is_right:
            # Shift LEDs right, set leftmost LED to color
            self.leds[1:self.num_leds] = self.leds[0:self.num_leds - 1]
            self.leds[0] = color
        else:
            # Shift LEDs left, set rightmost LED to color
            self.leds[0:self.num_leds - 1] = self.leds[1:self.num_leds]
            self.leds[self.num_leds - 1] = color
        self.leds.show()
        time.sleep(sleep_time)
            
    # Basically a macro for filling colors, calling show(), and waiting
    def color(self, r, g, b, w, sleep_time):
        self.leds.fill((r, g, b, w))
        self.leds.show()
        time.sleep(sleep_time)
                        

    # Returns a string that contains the alarms nicely formatted
    def alarm_string(self):
        if self.snooze_next_alarm and not self.snoozed_last_alarm:
            alarm_string = "Alarm set to snooze\n"
        else:
            alarm_string = "Alarm armed\n"
        return alarm_string + "\n".join(["{}: {:02.0f}:{:02.0f}".format(calendar.day_name[day], self.alarms[day][0], self.alarms[day][1]) for day in range(7)])


    # Setter for alarm. Returns a string with info on the alarm that was set
    def set_alarm(self, day, hour, minute):
        # Set alarms, then write the variable to file
        self.alarms[day][H] = hour
        self.alarms[day][M] = minute
        with open(self.alarm_filename, 'wb') as alarm_file:
            pickle.dump(self.alarms, alarm_file)
        reply = "Set alarm on {} to {:02.0f}:{:02.0f}".format(calendar.day_name[day], hour, minute)
        self.logger.debug(reply)
        
        # Update next_alarm if it was just changed
        if self.next_alarm.weekday() == day:
            now = datetime.datetime.now()
            self.next_alarm = datetime.datetime(now.year, now.month, now.day, hour, minute, 0, 0)
            self.logger.debug("Next alarm is " + self.next_alarm.strftime("%Y-%m-%d at %H:%M:%S"))
        
        return reply

    # Setter for snooze. Returns a string with info on the snooze that was set
    def set_snooze(self, on=True):
        if on:
            self.snooze_next_alarm = True
            reply = "Set to snooze next alarm"
        else:
            self.snooze_next_alarm = False
            reply = "Not going to snooze next alarm"
        return reply
        

    # Setter for mode/params
    def set_mode(self, mode, params=[]):
        with self.mode_lock:
            self.mode = mode
            self.params = params
            self.logger.debug("Just set mode to " + mode + " and params to " + str(self.params))
