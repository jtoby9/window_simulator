#!/usr/bin/python3

from TCP_Server import TCP_Server
import os
import sys
import logging
from logging import handlers
from logging.handlers import RotatingFileHandler

def main():
    # Set up logger
    logger = set_up_logger(1048576, 3)
    logger.info("Started window")
    
    # Get initial mode argument
    if len(sys.argv) > 1:
        initial_mode = sys.argv[1]
    else:
        initial_mode = "off"
    
    try:
        # Initialize and run server (should run indefinitely unless there is an error)
        server = TCP_Server( 
            commands = [
                ["help", "none", "Print a list of commands and what they do"],
                ["alarm", "none", "list alarms"],
                ["alarm", '3-letter day/"weekend"/"weekday", time', "set alarm"],
                ["snooze", "on", "snooze next alarm"],
                ["snooze", "off", "don't snooze next alarm"],
                ["rainbow", "none", ""],
                ["white/w", "0-255", ""],
                ["color/c", "four 8 bit numbers", ""],
                ["max/m", "", "equivalent to c 255 255 255 255"],
                ["fade", "none", ""],
                ["fade", "white value", ""],
                ["strobe", "none", ""],
                ["random", "none", ""],
                ["cylon", "none", ""],
                ["scroll", "none", ""],
                ["cascade", "none", ""],
                ["read", "none", ""],
                ["read2", "none", ""],
                ["restart", "none", ""],
                ["reboot", "none", ""],
                ["off/o", "none", ""],
            ],
            hostname = "", 
            tcp_port = 12345,
            buf_size = 4096,
            socket_timeout = 120.0,
            initial_mode = initial_mode,            
        )
        server.run()
    
    # Catch stray errors
    except KeyboardInterrupt:
        logger.warning("Received KeyboardInterrupt from server side. Exiting")
    except Exception:
        logger.exception("Encountered uncaught exception. Exiting")
    finally:
        # Try to stop the LED strip
        try:
            server.led_strip.stop_event.set()
            logger.debug("Stopped LED strip")
        except AttributeError:
            logger.debug("Didn't stop LED strip because it wasn't initialized")
        except UnboundLocalError:
            logger.debug("Didn't stop LED strip because server wasn't initialized")
        except:
            logger.exception("Encountered another uncaught exception while trying to stop LED strip")
        finally:
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

