#!/usr/bin/python3

from TCP_Server import TCP_Server
from LED_Strip import LED_Strip
from Remote_Receiver import Remote_Receiver
from Button import Button
from Alarm_Clock import Alarm_Clock
import os
import sys
import pigpio
import queue
from threading import Event
import logging
from logging import handlers
from logging.handlers import RotatingFileHandler

def main():
    # Set up logger
    logger = set_up_logger(1048576, 3)
    logger.info("Started window")
        
    try:
        # Initialize objects to pass to threads
        pi = pigpio.pi()
        stop_event = Event()
        to_tcp_server = queue.Queue()
        to_led_strip = queue.Queue()
        to_alarm_clock = queue.Queue()
        
        # If there is an initial mode, pass it to the LED strip
        if len(sys.argv) > 1:
            command = " ".join(sys.argv[1:])
            to_led_strip.put_nowait(["Main", command])
        
        # Initialize threads and add each one to the list as it gets initialized
        threads = []
        tcp_server = TCP_Server(stop_event, to_tcp_server, to_led_strip, to_alarm_clock)
        threads.append(tcp_server)
        
        led_strip = LED_Strip(stop_event, to_tcp_server, to_led_strip)
        threads.append(led_strip)
        
        remote_receiver = Remote_Receiver(pi, stop_event, to_led_strip)
        threads.append(remote_receiver)
        
        button = Button(pi, stop_event, to_led_strip)
        threads.append(button)
        
        alarm_clock = Alarm_Clock(stop_event, to_tcp_server, to_led_strip, to_alarm_clock)
        threads.append(alarm_clock)
        
        # Wait
        stop_event.wait()
                
    
    # Catch stray errors
    except KeyboardInterrupt:
        logger.warning("Received KeyboardInterrupt. Exiting")
    except Exception:
        logger.exception("Encountered uncaught exception. Exiting")
    finally:
        # Try to stop the threads
        try:
            if not stop_event.is_set():
                logger.debug("Stop event was not set. Setting it now")
                stop_event.set()
            for thread in threads:
                if thread.is_alive():
                    logger.debug("Stopping " + thread.name)
                    thread.join()
        except:
            logger.exception("Encountered another uncaught exception while trying to stop threads")
        finally:
            pi.stop()
            sys.exit() # Exit cleanly
    
# Takes max log size in bytes and number of backups to keep, and returns a fully
# initialized logger object
def set_up_logger(max_log_size, log_backups):
    # Initialize handler for the log file
    debug_log = logging.handlers.RotatingFileHandler(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "log"),
                maxBytes=max_log_size,
                backupCount=log_backups)
    debug_log.setLevel(logging.DEBUG)
    
    # Initialize logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s.%(msecs)03d] [%(name)s:%(lineno)d] [%(threadName)s] [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[debug_log, logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)


if __name__ == "__main__":
    main()

