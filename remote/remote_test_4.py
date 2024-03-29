import RPi.GPIO as GPIO
import time
import traceback
    
PinIn = 17
button_dict = {
    0x357e304fb: "mute",
    0x357e308f7: "volume_down",
    0x357e310ef: "vudu",
    0x357e31ee1: "arrow",
    0x357e32cd3: "rewind",
    0x357e330cf: "disney+",
    0x357e332cd: "play/pause",
    0x357e346b9: "moon",
    0x357e34ab5: "netflix",
    0x357e354ab: "ok",
    0x357e36699: "back",
    0x357e37887: "left",
    0x357e38679: "star",
    0x357e39867: "up",
    0x357e3aa55: "fast_forward",
    0x357e3b24d: "hulu",
    0x357e3b44b: "right",
    0x357e3c03f: "home",
    0x357e3cc33: "down",
    0x357e3e817: "power",
    0x357e3f00f: "volume_up",
}

#Sets up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PinIn, GPIO.IN)
# GPIO.setup(PinIn, GPIO.IN, pull_up_down=GPIO.PUD_UP)


        
def poll_sensor(): #Pulls data from sensor
    num1s = 0 #Number of consecutive 1s
    command = [] #Pulses and their timings
    binary = 0b1 #Decoded binary command
    previousValue = 0 #The previous pin state
    value = GPIO.input(PinIn) #Current pin state
    
    # Wait until pin is pulled low
    value = 0
    channel = GPIO.wait_for_edge(PinIn, GPIO.FALLING, timeout=100)
    
    startTime = time.time() #Sets start time
    
    while channel is not None:
        channel = GPIO.wait_for_edge(PinIn, GPIO.BOTH, timeout=100)
        
        if value != previousValue: #Waits until change in state occurs
            now = time.time() #Records the current time
            pulseLength = (now - startTime) * 1000000 #Calculate time in between pulses in microseconds
            startTime = now #Resets the start time
            command.append((previousValue, pulseLength)) #Adds pulse time to array (previous val acts as an alternating 1 / 0 to show whether time is the on time or off time)
                
        #Reads values again
        previousValue = value
        value = GPIO.input(PinIn)
        
    #Covers data to binary
    print(len(command))
    for (typ, tme) in command:
        if typ == 1:
            binary = binary << 1
            # print(round(tme, 1))
            if tme > 1000: #According to NEC protocol a gap of 1687.5 microseconds repesents a logical 1 so over 1000 should make a big enough distinction
                binary += 1
                
    if binary.bit_length() > 34: #Sometimes the binary has two rouge charactes on the end
        binary = binary >> (binary.bit_length() - 34)
        
    return binary
    
#Main program loop
try:
    before = time.time()
    while True:
        # command = poll_sensor()
        # if command in button_dict:
            # print(button_dict[command])
        # elif command > 100:
            # print("Unknown:", hex(command))
            
        channel = GPIO.wait_for_edge(PinIn, GPIO.BOTH, timeout=1000)
        after = time.time()
        print((after - before) * 1000000)
        before = after
except:
    print(traceback.format_exc())
finally:
    GPIO.cleanup()
