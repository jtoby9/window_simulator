import RPi.GPIO as GPIO
import time

pin = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# GPIO.setup(pin, GPIO.IN)


def button_pressed_callback(channel):
    print("GPIO{} pressed".format(channel))

prev_state = False
state = False

try:
    while True:
        prev_state = state
        state = GPIO.input(pin)
        if state != prev_state:
            print(prev_state, "->", state)
        
        # time.sleep(.01)
        

    # GPIO.add_event_detect(pin, GPIO.RISING, callback=button_pressed_callback, bouncetime=200)
    # while True:
        # pass
    

    
    
except KeyboardInterrupt as e:
    print("Exiting")
    GPIO.cleanup()