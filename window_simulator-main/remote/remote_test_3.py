import RPi.GPIO as GPIO
import time
import traceback
import csv

pin = 21
timeout_time_ms = 100

GPIO.setmode(GPIO.BCM) 
GPIO.setup(pin, GPIO.IN)

try:
    while True:
        # Reset times and clear pulses
        pulses = []
        rising_time = 0
        falling_time = 0
        # Wait for a falling edge
        channel = GPIO.wait_for_edge(pin, GPIO.FALLING, timeout=timeout_time_ms * 10)
        # A falling edge has been detected - now capture the pulses
        while channel:
            # Record the time and record the length of the high pulse
            falling_time = time.time()
            pulses.append([True, falling_time - rising_time])
            # Wait for a rising edge. Don't wait longer than the timeout time
            GPIO.wait_for_edge(pin, GPIO.RISING, timeout=timeout_time_ms)
            # Record the time and record the length of the low pulse
            rising_time = time.time()
            pulses.append([False, rising_time - falling_time])
            # Wait for another falling edge. Don't wait longer than the timeout time
            channel = GPIO.wait_for_edge(pin, GPIO.FALLING, timeout=timeout_time_ms)
            
        # Get rid of the erroneous first pulse
        pulses = pulses[1:]
        
        # Ignore the pulses if there are less than 34
        if len(pulses) >= 34:
            # Combine the pulse data into a string and display it
            # string_pulses = ["{}_{}".format("1" if is_high else "0", round(length * 1000, 2)) for is_high, length in pulses]
            string_pulses = [str(round(length * 1000, 2)) for is_high, length in pulses]
            for a in string_pulses:
                print(a)
                        
                        
            # Convert the pulses into a binary number
            
                
            # # Write the pulses into a csv
            # with open("roku_back.csv", 'a', newline='') as csvfile:
                # writer = csv.writer(csvfile)
                # writer.writerow(string_pulses)
                # csvfile.close()
                

except Exception as e:
    print(traceback.format_exc())
    GPIO.cleanup()