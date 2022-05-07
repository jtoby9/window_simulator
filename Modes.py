import time
import random
import collections
from threading import Event

# Implement a default version of every optional function
class Mode():
    # Takes arguments specifying what about the state to modify, calls a modifying function, returns what was modified
    def modify(self, args):
        # Parse first argument
        if args[0] == "increase":
            increase = True
        elif args[0] == "decrease":
            increase = False
        else:
            return "Did nothing, invalid first argument"
            
        # Parse second argument
        if args[1] == "brightness":
            return self.modify_brightness(increase)
        elif args[1] in "rgbw":
            return self.modify_color(increase, args[1])
        else:
            return "Did nothing, invalid second argument"
            

    def modify_brightness(self, increase):
        return "Nothing defined to modify brightness for this mode"
    
    def modify_color(self, increase, color):
        return "Nothing defined to modify color for this mode"
        

class Alarm(Mode):
    name = "alarm"
    arg_dict = {}
    max_brightness = 5
    total_cycles = 1000
    # Constructor - validate arguments, convert them to attributes, and exit
    def __init__(self, args): 
        duration = int(args[0])
        if duration < 1:
            raise ValueError("Alarm duration needs to be greater than 0")
        self.cycles = 0
        self.duration = duration
        # Calculate time to wait per cycle
        self.wait_time = float(self.duration / 2) / (float(self.total_cycles))
        
    def cycle(self, leds):
        # First half of the alarm
        if self.cycles < self.total_cycles:
            # Ramp up the brightness and run for the wait time
            self.cycles += 1
            brightness = (self.max_brightness * leds.n) * (self.cycles / self.total_cycles)
            flatten(leds, int(brightness), self.wait_time)
        # Second half of the alarm
        else:
            # Stay on at the maximum brightness 
            color(leds, 0, 0, self.max_brightness, self.max_brightness, self.wait_time)
        
class Color(Mode):
    name = "color"
    arg_dict = {"four 8 bit numbers" : "Set the LED strip to the specified color"}
    wait_time = .1
    multiply_increment = .5
    add_increment = 25
    # Constructor - validate arguments, convert them to attributes, and exit
    def __init__(self, args): 
        # Check if any of the values are invalid
        for color in args:
            if not 0 <= int(color) <= 255:
                raise ValueError("Color values must be between 0 and 255 inclusive")
                
        # Assign them to attributes
        self.r = int(args[0])
        self.g = int(args[1])
        self.b = int(args[2])
        self.w = int(args[3])
        
    def cycle(self, leds):
        color(leds, self.r, self.g, self.b, self.w, self.wait_time)

    def modify_brightness(self, increase):
        self.r = color_multiply(self.r, increase, self.multiply_increment)
        self.g = color_multiply(self.g, increase, self.multiply_increment)
        self.b = color_multiply(self.b, increase, self.multiply_increment)
        self.w = color_multiply(self.w, increase, self.multiply_increment)
        return "{}creased brightness. New color is {}, {}, {}, {}".format("In" if increase else "De", self.r, self.g, self.b, self.w)
    
    def modify_color(self, increase, color):
        increment = self.add_increment if increase else self.add_increment * -1
        if color == 'r':
            self.r = color_add(self.r, increment)
            return "{}creased red. New color is {}, {}, {}, {}".format("In" if increase else "De", self.r, self.g, self.b, self.w)
        elif color == 'g':
            self.g = color_add(self.g, increment)
            return "{}creased green. New color is {}, {}, {}, {}".format("In" if increase else "De", self.r, self.g, self.b, self.w)
        elif color == 'b':
            self.b = color_add(self.b, increment)
            return "{}creased blue. New color is {}, {}, {}, {}".format("In" if increase else "De", self.r, self.g, self.b, self.w)
        elif color == 'w':
            self.w = color_add(self.w, increment)
            return "{}creased white. New color is {}, {}, {}, {}".format("In" if increase else "De", self.r, self.g, self.b, self.w)
        else:
            return "Did nothing, invalid color"
        
class Rainbow(Mode):
    name = "rainbow"
    arg_dict = {"none" : "Rainbow pattern"}
    # Constructor
    def __init__(self, args): 
        self.cycles = 0
        
    def cycle(self, leds):
        # No idea how this works but it looks cool
        for j in range(leds.n):
            pixel_index = (j * 256 // leds.n) + self.cycles
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
            leds[j] = (r, g, b, 0)
        leds.show()
        event.wait(.001)
            
        # Increment cycles
        self.cycles += 1
        if self.cycles >= 255:
            self.cycles = 0
    

class Fade(Mode):
    # ATTRIBUTES NOT INHERITED
    # white (int) - the white value that stays constantly on during the fade pattern
    name = "fade"
    arg_dict = {
        "none" : "Fade in and out of random colors",
        "0-255" : "Fade in and out of random colors with the specified white value",
    }
    cycle_time = .005
    default_white = 20
    add_increment = 20
    # Constructor - validate arguments, convert them to attributes, and exit
    def __init__(self, args): 
        # If there is no white argument, use the default
        if len(args) == 0:
            white = self.default_white 
        else:
            white = int(args[0])
            if not 0 <= white < 256:
                raise ValueError
                
        # Initialize color
        self.white = white
        self.colors = collections.deque()

    def cycle(self, leds):
        # If the list of colors to cycle in and out of is empty, build it up
        if len(self.colors) == 0:
            # Choose random color
            r = random.random()
            g = random.random()
            b = random.random()
            
            # Fade in and out
            for i in list(range(256)) + list(range(256, -1, -1)):
                self.colors.append((int(r * i), int(g * i), int(b * i)))
                
        # Otherwise, set the LEDS to the most recent color from the list
        else:
            r, g, b = self.colors.popleft()
            color(leds, r, g, b, self.white, self.cycle_time)      
                    
    def modify_brightness(self, increase):
        increment = self.add_increment if increase else self.add_increment * -1
        self.white = color_add(self.white, increment)
        return "Increased white" if increase else "Decreased white"
    

class Strobe(Mode):
    name = "strobe"
    arg_dict = {"none" : "Strobe pattern"}
    strobe_time = .2
    # Constructor
    def __init__(self, args): 
        pass
        
    def cycle(self, leds):
        # Flash all lights on and off
        for i in range(4):
            color(leds, 255, 255, 255, 255, self.strobe_time)
            color(leds, 0, 0, 0, 0, self.strobe_time)
        # Flash lights alternating
        for i in range(8):
            for j in range(leds.n):
                brightness = 255 * ((i + j) % 2)
                leds[j] = (brightness, brightness, brightness, brightness)
            leds.show()
            event.wait(self.strobe_time / 2)
            color(leds, 0, 0, 0, 0, self.strobe_time / 2)

class Random(Mode):
    name = "random"
    arg_dict = {
        "none" : "Picks random colors and transitions towards them",
        "0-255" : "Picks random colors and transitions towards them with the specified white value",
    }
    initial_rgb = (128, 128, 128)
    default_white = 0
    add_increment = 5
    cycle_time = .01
    hold_time = 1
    # Constructor - validate arguments, convert them to attributes, and exit
    def __init__(self, args):
        # If there is no white argument, use the default
        if len(args) == 0:
            white = self.default_white 
        else:
            white = int(args[0])
            if not 0 <= white < 256:
                raise ValueError
                
        # Initialize color
        self.white = white
        self.r = random.randint(0, 255)
        self.g = random.randint(0, 255)
        self.b = random.randint(0, 255)
        
        # Initialize loop variables
        self.colors = collections.deque()
        self.time_to_wait = 0
        
    def cycle(self, leds):
        # Wait if holding the final color value
        if self.time_to_wait > 0:
            event.wait(self.cycle_time)
            self.time_to_wait -= self.cycle_time
        # If the list of colors to display is empty, build it up
        elif len(self.colors) == 0:            
            # Choose random color
            new_r = random.randint(0, 255)
            new_g = random.randint(0, 255)
            new_b = random.randint(0, 255)
            
            # Calculate number of steps to take
            diff_r = new_r - self.r
            diff_g = new_g - self.g
            diff_b = new_b - self.b
            steps = max(abs(diff_r), abs(diff_g), abs(diff_b))
            
            # Build up list of colors to display
            for i in range(steps):
                red_val = int(self.r + diff_r * (i / steps))
                green_val = int(self.g + diff_g * (i / steps))
                blue_val = int(self.b + diff_b * (i / steps))
                self.colors.append((red_val, green_val, blue_val))
                
                
        # Otherwise, display the next color in the list
        else:
            r, g, b = self.colors.popleft()
            color(leds, r, g, b, self.white, self.cycle_time)
            
            # Check if this is the last step
            if len(self.colors) == 0:
                # Save the final color and hold it
                self.r, self.g, self.b = [r, g, b]
                self.time_to_wait = self.hold_time
                
    def modify_brightness(self, increase):
        increment = self.add_increment if increase else self.add_increment * -1
        self.white = color_add(self.white, increment)
        return "{}creased white to {}".format("In" if increase else "De", self.white)
        
class Cylon(Mode):
    name = "cylon"
    arg_dict = {"none" : "Moving dot pattern from a show I haven't seen"}
    cylon_time = .004
    cylon_color = (0, 0, 0, 10)
    # Constructor
    def __init__(self, args): 
        pass
        
    def cycle(self, leds):
        for i in list(range(leds.n - 1)) + list(range(leds.n - 1, 0, -1)):
            color_one_led(leds, i, self.cylon_color)
            leds.show()
            event.wait(self.cylon_time)
        

class Scroll(Mode):
    name = "scroll"
    arg_dict = {"none" : "Scrolls through random colors"}
    scroll_delta = .3
    initial_color = [128, 128, 128, 0]
    cycle_time = .05
    # Constructor - initialize color
    def __init__(self, args): 
        self.color = self.initial_color
        
    def cycle(self, leds):
        # Pick either R, G, or B
        value_to_change = random.randint(0, 2)
        # Either subtract the delta from it or add the delta to it depending on a "coin flip"
        if random.random() >= .5:
            self.color[value_to_change] += int(self.scroll_delta * (256 - self.color[value_to_change]))
        else:
            self.color[value_to_change] = int(self.color[value_to_change] * (1 - self.scroll_delta))
        queue_push(leds, tuple(self.color), self.cycle_time, False)

class Cascade(Mode):
    name = "cascade"
    arg_dict = {"none" : "Scrolls through R, B and G randomly"}
    cascade_increment = 8
    default_white = 0
    add_increment = 5
    cycle_time = .05
    # Constructor - validate arguments, convert them to attributes, and exit
    def __init__(self, args):
        # If there is no white argument, use the default
        if len(args) == 0:
            white = self.default_white 
        else:
            white = int(args[0])
            if not 0 <= white < 256:
                raise ValueError
        # Initialize color
        self.white = white
        self.colors = collections.deque()
        
    def cycle(self, leds):
        # If the list of colors is empty, build it up
        if len(self.colors) == 0:
            # Pick two of R, G, or B to raise (in random order) and raise them 
            color = [0, 0, 0]
            rgb_indices = [0, 1, 2]
            rgb_indices.remove(random.randint(0, 2))
            if random.random() >= .5:
                rgb_indices.reverse()
            for index in rgb_indices:
                for i in range(255 // self.cascade_increment):
                    color[index] += self.cascade_increment
                    self.colors.append(tuple(color))
            
            # Lower the two values raised in a random order 
            if random.random() >= .5:
                rgb_indices.reverse()
            for index in rgb_indices:
                for i in range(255 // self.cascade_increment):
                    color[index] -= self.cascade_increment
                    self.colors.append(tuple(color))
                    
        # Otherwise, set the LEDS to the most recent color from the list
        else:
            color = self.colors.popleft()
            queue_push(leds, color + (self.white,), self.cycle_time)
                
    def modify_brightness(self, increase):
        increment = self.add_increment if increase else self.add_increment * -1
        self.white = color_add(self.white, increment)
        return "{}creased white to {}".format("In" if increase else "De", self.white)

                
class Read(Mode):
    name = "read"
    arg_dict = {
        "none" : "Reading light",
        "2" : "Reading light for two people",
    }
    reading_color = (75, 0, 0, 75)
    one_light = (19, 20, 21)
    two_lights = (0, 1, 2, 19, 20, 21)
    cycle_time = .1
    # Constructor - decide between one or two reading lights
    def __init__(self, args): 
        if len(args) > 0 and args[0] == "2":
            self.leds_to_turn_on = self.two_lights
        else:
            self.leds_to_turn_on = self.one_light
        
    def cycle(self, leds):
        # Set LEDs that should be turned on to the reading color, turn off all other LEDs
        for i in range(leds.n):
            if i in self.leds_to_turn_on:
                leds[i] = self.reading_color
            else:
                leds[i] = (0, 0, 0, 0)
        leds.show()
        event.wait(self.cycle_time)
        
# Data for every mode:
        
# Dictionary that matches each mode class name to the actual mode class
class_dict = {
    Alarm.name : Alarm,
    Color.name : Color,
    Rainbow.name : Rainbow,
    Fade.name : Fade,
    Strobe.name : Strobe,
    Random.name : Random,
    Cylon.name : Cylon,
    Scroll.name : Scroll,
    Cascade.name : Cascade,
    Read.name : Read,
}
# Dummy event object to use for waits. Do not ever set the internal flag
event = Event()


# Takes the name of a mode, returns the mode class
def get_class(name):
    if name in class_dict:
        return class_dict[name]
    else:
        return None
       
# Takes a string that can be formatted to contain each line and returns a string containing 
# all the mode names, arguments and descriptions
def mode_string(format_string):
    string = ""
    for name, mode_class in class_dict.items():
        for arg, description in mode_class.arg_dict.items():
            string += format_string.format(name, arg, description)
    return string
            

# Takes a number from 0 to 7650 inclusive and distributes the brightness as
# blue/white along the LEDs, calls show(), and waits
def flatten(leds, brightness, sleep_time):
    quotient = int(brightness // leds.n)
    remainder = int(brightness % leds.n)
    for i in range(leds.n):
        if i < remainder:
            leds[i] = (0, 0, quotient + 1, quotient + 1)
        else:
            leds[i] = (0, 0, quotient, quotient)
    leds.show()
    event.wait(sleep_time)
    
# Set one LED to one color, set everything else to another color. Does not call show()
def color_one_led(leds, index, color, other_color=(0, 0, 0, 0)):
    for i in range(leds.n):
        if i == index:
            leds[i] = color
        else:
            leds[i] = other_color
            
# Shift the LED colors either left or right, set the remaining LED to the specified
# color, call show() and wait
def queue_push(leds, color, sleep_time, dir_is_right=True):
    if dir_is_right:
        # Shift LEDs right, set leftmost LED to color
        leds[1:leds.n] = leds[0:leds.n - 1]
        leds[0] = color
    else:
        # Shift LEDs left, set rightmost LED to color
        leds[0:leds.n - 1] = leds[1:leds.n]
        leds[leds.n - 1] = color
    leds.show()
    event.wait(sleep_time)
        
# Sets every LED to the r, g, b, and w values given, calls show(), and sleeps for the time given
def color(leds, r, g, b, w, sleep_time):
    leds.fill((r, g, b, w))
    leds.show()
    event.wait(sleep_time)

# Closes the gap between a color value and its maximum or minimum value by the factor specified
def color_multiply(color_value, increase, factor):
    if increase:
        return int(color_value + (255 - color_value) * .5)
    else:
        return int(color_value * .5)
        
# Adds an amount to a color value but keeps it from over or underflowing
def color_add(color_value, amount):
    new_value = color_value + amount
    if new_value > 255:
        return 255
    elif new_value < 0:
        return 0
    else:
        return new_value