import RPi.GPIO as GPIO
from time import time

# Constants
pin = 17
button_codes = {
	0x357fe817d : "power",
	0x357e3669e : "back",
	0x357e100ff : "home",
	0x357e39867 : "up",
	0x37e37887d : "left",
	0x357e3b44b : "right",
	0x357e3c33d : "down",
	0x357e34abd : "ok",
	0x3bf18f70e : "arrow",
	0x357e346b9 : "moon",
	0x357e38679 : "star",
	0x357e3cd3d : "rewind",
	0x357e332cd : "play/pause",
	0x357e3aa55 : "ffwd",
	0x37f1a55ae : "netflix",
	0x3578cc33f : "disney+",
	0x357e3926e : "hulu",
	0x357e310ef : "vudu",
	0x357e3f00f : "volume+",
	0x357e38f7d : "volume-",
	0x357e304ef : "mute",
}

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def binary_aquire(pin, duration):
    # aquires data as quickly as possible
    t0 = time()
    results = []
    while (time() - t0) < duration:
        results.append(GPIO.input(pin))
    return results


def on_ir_receive(pinNo, bouncetime=150):
    # when edge detect is called (which requires less CPU than constant
    # data acquisition), we acquire data as quickly as possible
    data = binary_aquire(pinNo, bouncetime/1000.0)
    if len(data) < bouncetime:
        return
    rate = len(data) / (bouncetime / 1000.0)
    pulses = []
    i_break = 0
    # detect run lengths using the acquisition rate to turn the times in to microseconds
    for i in range(1, len(data)):
        if (data[i] != data[i-1]) or (i == len(data)-1):
            pulses.append((data[i-1], int((i-i_break)/rate*1e6)))
            i_break = i
    # decode ( < 1 ms "1" pulse is a 1, > 1 ms "1" pulse is a 1, longer than 2 ms pulse is something else)
    # does not decode channel, which may be a piece of the information after the long 1 pulse in the middle
    outbin = ""
    for val, us in pulses:
        if val != 1:
            continue
        if outbin and us > 2000:
            break
        elif us < 1000:
            outbin += "0"
        elif 1000 < us < 2000:
            outbin += "1"
    try:
        return int(outbin, 2)
    except ValueError:
        # probably an empty code
        return None


def destroy():
    GPIO.cleanup()


if __name__ == "__main__":
    setup()
    try:
        print("Starting IR Listener")
        while True:
            print("Waiting for signal")
            GPIO.wait_for_edge(pin, GPIO.FALLING)
            code = on_ir_receive(pin)
            if code:
                print(str(hex(code)))
            else:
                print("Invalid code")
    except KeyboardInterrupt as e:
        print(e)
    except RuntimeError as e:
        # this gets thrown when control C gets pressed
        # because wait_for_edge doesn't properly pass this on
        print(e)
    print("Quitting")
    destroy()
