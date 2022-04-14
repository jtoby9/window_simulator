import pigpio
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
pi = pigpio.pi()
pi.set_mode(PinIn, pigpio.INPUT)



        
# def poll_sensor(): #Pulls data from sensor
    # num1s = 0 #Number of consecutive 1s
    # command = [] #Pulses and their timings
    # binary = 0b1 #Decoded binary command
    # previousValue = 0 #The previous pin state
    # value = GPIO.input(PinIn) #Current pin state
    
    # # Wait until pin is pulled low
    # value = 0
    # channel = GPIO.wait_for_edge(PinIn, GPIO.FALLING, timeout=100)
    
    # startTime = time.time() #Sets start time
    
    # while channel is not None:
        # channel = GPIO.wait_for_edge(PinIn, GPIO.BOTH, timeout=100)
        
        # if value != previousValue: #Waits until change in state occurs
            # now = time.time() #Records the current time
            # pulseLength = (now - startTime) * 1000000 #Calculate time in between pulses in microseconds
            # startTime = now #Resets the start time
            # command.append((previousValue, pulseLength)) #Adds pulse time to array (previous val acts as an alternating 1 / 0 to show whether time is the on time or off time)
                
        # #Reads values again
        # previousValue = value
        # value = GPIO.input(PinIn)
        
    # #Covers data to binary
    # print(len(command))
    # for (typ, tme) in command:
        # if typ == 1:
            # binary = binary << 1
            # # print(round(tme, 1))
            # if tme > 1000: #According to NEC protocol a gap of 1687.5 microseconds repesents a logical 1 so over 1000 should make a big enough distinction
                # binary += 1
                
    # if binary.bit_length() > 34: #Sometimes the binary has two rouge charactes on the end
        # binary = binary >> (binary.bit_length() - 34)
        
    # return binary
    
                        
    # # Helper function to poll the IR receiver pin and return the code received as an int
    # def get_remote_code(self):
        # # Record pulses until the wait time elapses
        # code = 0
        # pulses = []
        # try:
            # while True:
                # pulses.append(self.gpio_events.get(True, self.wait_time))
                # # print(pulses)
            
        # except queue.Empty:
            # # If there were no pulses, just return and don't try and convert anything
            # if len(pulses) == 0:
                # return 0
        
            # print(len(pulses))        
            # # Convert the pulses to binary
            # for i in range(len(pulses) - 1):
                # # The low pulses are the only ones that matter in terms of decoding
                # if pulses[i][0] == 0:
                    # code = code << 1
                    # # Logical 1 -> 1687.5us, logical 0 -> 562.5us. So split the difference
                    # if pulses[i][1] > 1125:
                        # code += 1
    
            # if code.bit_length() > 34: # Sometimes the binary has two rouge charactes on the end
                # code = code >> (code.bit_length() - 34)
        # return code
    
    
last_tick = 0
    
def cbf(gpio, level, tick):
   global last_tick
   print(gpio, level, tick - last_tick)
   last_tick = tick
    
#Main program loop
try:
    cb1 = pi.callback(17, pigpio.EITHER_EDGE, cbf)
    while True:
        # command = poll_sensor()
        # if command in button_dict:
            # print(button_dict[command])
        # elif command > 100:
            # print("Unknown:", hex(command))
            
        # channel = pi.wait_for_edge(PinIn, pigpio.EITHER_EDGE, wait_timeout=1)
        # after = time.time()
        # print((after - before) * 1000000)
        # before = after
        pass
except:
    print(traceback.format_exc())
finally:
    pi.stop()
    
