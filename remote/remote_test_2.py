#---------------------------------------------------------------------#
#Name - IR&NECDataCollect.py
#Description - Reads data from the IR sensor but uses the official NEC Protocol (command line version)
#Author - Lime Parallelogram
#Licence - Attribution Lime
#Date - 06/07/19 - 18/08/19
#---------------------------------------------------------------------#
#Imports modules
import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime
    
#==================#
#Promps for values
#Input pin
# while True:
    # PinIn = raw_input("Please enter your sensor pin: ")
    # try:
        # PinIn = int(PinIn)
        # break
    # except:
        # pass
PinIn = 12
#Remote name
# remote = raw_input("Please enter a name for you remote: ")
remote = "roku"

#==================#
#Creates output file
output = open(remote+".txt", 'a')
output.writelines("Button codes regarding " + remote + " IR controller:")
output.close()

#==================#
#Sets up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PinIn,GPIO.IN)

#==================#
#Defines Subs    
def ConvertHex(BinVal): #Converts binary data to hexidecimal
    tmpB2 = int(str(BinVal), 2)
    return hex(tmpB2)
        
def getData(): #Pulls data from sensor
    num1s = 0 #Number of consecutive 1s
    command = [] #Pulses and their timings
    binary = 0b1 #Decoded binary command
    previousValue = 0 #The previous pin state
    value = GPIO.input(PinIn) #Current pin state
    
    while value: #Waits until pin is pulled low
        value = GPIO.input(PinIn)
    
    startTime = datetime.now() #Sets start time
    
    while True:
        #Interrupts code if an extended high period is detected (End Of Command)    
        if value:
            num1s += 1
        else:
            num1s = 0
        
        if num1s > 10000:
            break

        # Check if a change in state has occured
        if value != previousValue:
            now = datetime.now() #Records the current time
            pulseLength = now - startTime #Calculate time in between pulses
            startTime = now #Resets the start time
            command.append((previousValue, pulseLength.microseconds)) #Adds pulse time to array (previous val acts as an alternating 1 / 0 to show whether time is the on time or off time)
        
        
        #Reads values again
        previousValue = value
        value = GPIO.input(PinIn)
        
    # Convert data to binary
    for (value, time) in command:
        # If the value is 1, then it corresponds to either a logical 1 or 0 depending on the pulse length
        if value == 1 and time > 500:
            binary = binary << 1
            if time > 1000: # According to NEC protocol a gap of 1687.5 microseconds repesents a logical 1 so over 1000 should make a big enough distinction
                binary += 0b1

    # Truncate the number to 34 bits
    if binary.bit_length() > 34:
        print("Truncating")
        binary = binary >> (binary.bit_length() - 34)
    # If there are less than 34 bits, ignore
    if binary.bit_length() < 34:
        return None

    # if len(str(binary)) > 34: #Sometimes the binary has two rouge charactes on the end
        # binary = int(str(binary)[:34])
        
    return binary
    
def runTest(): #Actually runs the test
    #Takes samples
    # command = ConvertHex(getData())
    # print("Hex value: " + str(command)) #Shows results on the screen
    data = getData()
    while data is None:
        data = getData()
    command = hex(data)
    print("Hex value: " + command)
    return command
    ###

#==================#
#Main program loop
try:
    while True:
        # if raw_input("Press enter to start. Type q to quit. ") == 'q':
          # break
        finalData = runTest()
        # if raw_input("Save? y/n.") == 'y':
          # name = raw_input("Enter a name for your button: ")
          # output = open(remote+".txt", 'a')
          # output.writelines("""
      # Button Code - """ + name + ": " + str(finalData))
          # output.close()
except Exception as e:
    print(e)
    GPIO.cleanup()
