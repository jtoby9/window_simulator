import time
import board
import adafruit_ahtx0
from threading import Thread, Event, Lock
import logging
import csv
import queue
import datetime


class TH_Sensor(Thread):
    # Constructor
    def __init__(self, stop_event, to_tcp_server, to_th_sensor):
        # Set up logger object
        self.logger = logging.getLogger(__name__)
                
        # Create sensor object, communicating over the board's default I2C bus
        self.sensor = adafruit_ahtx0.AHTx0(board.I2C()) # uses board.SCL and board.SDA
        self.wait_time = 300 # seconds
        self.event = Event() # Dummy event object to use for waits. Do not ever set the internal flag
        
        # If the data file doesn't exist, create it and write the first row
        self.filename = "/home/josh/window_simulator/temp_and_humidity.csv"        
        self.header = ['Date', 'Time', 'Temperature (F)', '%RH']
        try:
            with open(self.filename, 'x') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(self.header)
        except FileExistsError:
            pass
            
        # Initialize queues
        self.to_tcp_server = to_tcp_server
        self.to_th_sensor = to_th_sensor
            
        # Initialize thread
        Thread.__init__(self, name="TH Sensor")
        self.stop_event = stop_event
        Thread.start(self)
        
    # Indefinitely collect and record data
    def run(self):
        while not self.stop_event.is_set():
            try:
                # Check for a message from the server
                try:
                    message = self.to_th_sensor.get(True, self.wait_time)[1]
                except queue.Empty:
                    message = None
            
                # Measure temperature and humidity
                now = datetime.datetime.now()
                temp = round(32 + 1.8 * self.sensor.temperature, 1)
                rh = round(self.sensor.relative_humidity, 1)
                
                # Write the data to the file
                with open(self.filename, 'a') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([now.strftime('%Y %b %d'), now.strftime('%H:%M'), temp, rh])
                    
                # If the server asked for the measurements, send them
                if message:
                    self.to_tcp_server.put_nowait(["TH_Sensor", "{}F, {}%".format(temp, rh)])                    
        
            # Catch stray errors
            except Exception:
                self.logger.exception("Encountered uncaught exception")
                self.stop_event.set()
