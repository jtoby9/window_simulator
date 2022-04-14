import datetime
import calendar
import pickle
from threading import Thread, Event, Lock
import logging
import queue
import re

# Constants
H = 0 # hour index in alarms
M = 1 # minute index in alarms

class Alarm_Clock(Thread):
    # Constructor
    def __init__(self, stop_event, to_tcp_server, to_led_strip, to_alarm_clock):
        # Set up logger object
        self.logger = logging.getLogger(__name__)
                
        # Initialize state
        self.alarm_last_set_on = -1
        self.alarm_last_rang_on = -1
        self.snooze_next_alarm = False
        self.snoozed_last_alarm = False
        self.next_alarm_start = datetime.datetime(1, 1, 1, 1, 1, 1)
        self.next_alarm_stop = datetime.datetime(1, 1, 1, 1, 1, 2)
        self.alarm_is_ringing = False
                
        # Set alarm parameters
        self.alarm_duration = 1200 # seconds

        # Load alarm from file
        self.alarm_filename = "/home/josh/window_simulator/alarms"
        try:
            with open(self.alarm_filename, 'rb') as alarm_file:
                self.alarms = pickle.load(alarm_file)
        # If the file does not exist or is empty, create it
        except (FileNotFoundError, EOFError):
            with open(self.alarm_filename, 'wb') as alarm_file:
                self.alarms = [
                    [10, 0], # Default mon
                    [10, 0], # Default tue
                    [10, 0], # Default wed
                    [10, 0], # Default thu
                    [10, 0], # Default fri
                    [10, 0], # Default sat
                    [10, 0], # Default sun
                ]
                pickle.dump(self.alarms, alarm_file)
            
                
        # Initialize queues
        self.to_tcp_server = to_tcp_server
        self.to_led_strip = to_led_strip
        self.to_alarm_clock = to_alarm_clock
        
        # Initialize thread
        Thread.__init__(self, name="Alarm Clock")
        self.stop_event = stop_event
        Thread.start(self)
        
        
    # Poll indefinitely
    def run(self):
        while not self.stop_event.is_set():
            try:
                # Get the current time
                now = datetime.datetime.now()
                today = now.weekday()
                
                # Check if the alarm was set today
                if today != self.alarm_last_set_on:
                    # If the last alarm was snoozed, re-arm the alarm
                    if self.snoozed_last_alarm:
                        self.snooze_next_alarm = False
                    # Set next alarm start and stop times
                    alarm_time = datetime.datetime(now.year, now.month, now.day, self.alarms[today][H], self.alarms[today][M], 0, 0)
                    self.next_alarm_start = alarm_time - datetime.timedelta(seconds=(self.alarm_duration / 2))
                    self.next_alarm_stop  = alarm_time + datetime.timedelta(seconds=(self.alarm_duration / 2))
                    self.alarm_last_set_on = today
                    self.logger.debug("Next alarm is " + alarm_time.strftime("%Y-%m-%d at %H:%M:%S"))
                    
                # Check if it's time to ring the alarm
                if today != self.alarm_last_rang_on and self.next_alarm_start < now < self.next_alarm_stop:
                    if self.snooze_next_alarm:
                        # Snooze this alarm
                        self.logger.debug("Snoozing this alarm")
                        self.snoozed_last_alarm = True
                        self.alarm_last_rang_on = today
                    else:
                        # Ring the alarm
                        self.logger.debug("Ringing alarm")
                        self.to_led_strip.put_nowait(["Alarm_Clock", "alarm " + str(self.alarm_duration)])
                        self.snoozed_last_alarm = False
                        self.alarm_last_rang_on = today
                        self.alarm_is_ringing = True
                
                # Check if it's time to stop the alarm
                if self.alarm_is_ringing and now > self.next_alarm_stop:
                    self.logger.debug("Stopping alarm")
                    self.to_led_strip.put_nowait(["Alarm_Clock", "color 0 0 0 0"])
                    self.alarm_is_ringing = False
                    
                # Receive messages from other threads
                try:
                    received_message = self.to_alarm_clock.get_nowait()
                    sender = received_message[0]
                    message = received_message[1]
                    reply = self.receive_message(message)
                    # Send the reply back to the sender thread
                    if sender == "TCP_Server":
                        self.to_tcp_server.put_nowait(("LED_Strip", reply))
                except queue.Empty:
                    pass
                
            except Exception:
                self.logger.exception("Encountered uncaught exception")
                self.stop_event.set()
                
    # Receive a message and set alarm or snooze accordingly. Return a reply saying what happened
    def receive_message(self, message):
        # Parse message
        self.logger.debug("Received message " + message)
        fields = list(filter(None, re.split(" |,", message))) # split by comma or space, remove empty string
        name = fields[0] # The first field is always the name
        args = fields[1:]
        reply = "Oops I missed an edge case"
        
        # Alarm
        if name == "alarm":
            # If there are no arguments display the alarms
            if len(args) == 0:
                reply = self.alarm_string()
            else:
                try:
                    day_arg = args[0]
                    if day_arg == "mon":
                        days = [0]
                    elif day_arg == "tue":
                        days = [1]
                    elif day_arg == "wed":
                        days = [2]
                    elif day_arg == "thu":
                        days = [3]
                    elif day_arg == "fri":
                        days = [4]
                    elif day_arg == "sat":
                        days = [5]
                    elif day_arg == "sun":
                        days = [6]
                    elif day_arg == "weekday":
                        days = [0, 1, 2, 3, 4]
                    elif day_arg == "weekend":
                        days = [5, 6]
                    else:
                        raise ValueError('First argument was not a 3-letter day, "weekday" or "weekend"')
                    reply = ""
                    for day in days:
                        time = args[1].split(":")
                        hour = int(time[0])
                        minute = int(time[1])
                        if hour not in range(24) or minute not in range(60):
                            raise ValueError("Invalid time")
                        reply += "\n" + self.set_alarm(day, hour, minute)
                except (ValueError, IndexError) as e:
                    reply = "Didn't set alarm, encountered error: " + str(e)

        # Snooze
        elif name == "snooze":
            # Call the snooze setter with on or off depending on the arguments
            if len(fields) == 2 and fields[1] == "off":
                reply = self.set_snooze(on=False)
            elif len(fields) == 1:
                reply = self.set_snooze(on=True)
            else:
                reply = "Didn't set snooze, encountered error"
                
        else:
            reply = "Not a recognized alarm clock command"
                
        return reply
        
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
        
        # Update next alarm if it was just changed
        now = datetime.datetime.now()
        if self.next_alarm_start.weekday() == day and self.next_alarm_start.hour <= hour and self.next_alarm_start.minute <= minute:
            alarm_time = datetime.datetime(now.year, now.month, now.day, hour, minute, 0, 0)
            self.next_alarm_start = alarm_time - datetime.timedelta(seconds=(self.alarm_duration / 2))
            self.next_alarm_stop  = alarm_time + datetime.timedelta(seconds=(self.alarm_duration / 2))
            self.alarm_last_set_on = now.weekday()
            self.alarm_last_rang_on = -1
            self.logger.debug("Next alarm is " + alarm_time.strftime("%Y-%m-%d at %H:%M:%S"))
        
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
