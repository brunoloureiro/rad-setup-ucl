#!/usr/bin/python3
import argparse
import errno
import logging
import os
import signal
import sys
import threading
import traceback
import typing
from pathlib import Path
from rasp import FileReceiver
from psu_control import PowerController

import yaml

from server.logger_formatter import logging_setup
from server.machine import Machine
from server.print_manager import ConsoleCursesManager

# Logger name in the main server thread
PARENT_LOGGER_NAME: str = os.path.basename(str(__file__).lower().replace(".py", ""))

# Those global variables are necessary to stop all the threads when an exception is raised
# Machine List
MACHINE_LIST: list = list()
CONSOLE_CURSES_MANAGER: typing.Optional[ConsoleCursesManager] = None
PWR_CTRL: PowerController = None
THREAD_JOIN_TIMEOUT: float = 1.0


def __end_daemon_machines():
    # FIXME: This does not work when the end is before the threads are not started yet
    """ General end for all machines """
    logger = logging.getLogger(name=PARENT_LOGGER_NAME)
    if PWR_CTRL is not None:
        PWR_CTRL.stop_monitor()
        PWR_CTRL.shutdown()
    logger.info("Stopping all threads")
    for machine in MACHINE_LIST:
        machine.stop()
    logger.info("Waiting for all threads to join")
    for machine in MACHINE_LIST:
        try:
            machine.join(timeout=THREAD_JOIN_TIMEOUT)
        except RuntimeError as e:
            logging.error(f"Error while joining thread: {e}")

    if CONSOLE_CURSES_MANAGER is not None:
        CONSOLE_CURSES_MANAGER.stop()
        try:
            CONSOLE_CURSES_MANAGER.join()
        except RuntimeError as e:
            logging.error(f"Error while joining thread: {e}")



def __machine_thread_exception_handler(args: threading.ExceptHookArgs):
    """ It handles the exception on the Machine threads
    The args argument has the following attributes:
    exc_type: Exception type --> DEPRECATED after Python 3.10, the value is ignored
    exc_value: Exception value can be None.
    exc_traceback: Exception trace-back can be None.
    thread: Thread, which raised the exception, can be None. """
    # FIXME: some exceptions are problematic as not all attributes are available
    logger = logging.getLogger(name=PARENT_LOGGER_NAME)
    exception_str = "".join(
        traceback.format_exception(args.exc_type, value=args.exc_value, tb=args.exc_traceback)
    )
    logger.error(f"Error {exception_str} at Machine thread:{args.thread}")
    # Log the thread that raises the exception
    __end_daemon_machines()
    sys.exit(errno.ECHILD)


def __ctrlc_handler(signum, frame):
    """ Signal handler to be attached
    """
    logger = logging.getLogger(name=PARENT_LOGGER_NAME)
    logger.error(
        f"KeyboardInterrupt detected, exiting gracefully!( at least trying :) ). signum:{signum} frame:{frame}")
    logger.info("Stopping all threads")
    __end_daemon_machines()
    sys.exit(130)


def main():
    """ Main function """
    # The First thing is to guarantee that python >=3.10 is running
    if sys.version_info.major < 3 or sys.version_info.minor < 10:
        raise ValueError("Python 3.10 or greater required")

    # Attach CTRL-C pressing to the function
    signal.signal(signal.SIGINT, __ctrlc_handler)

    # Argument reading
    parser = argparse.ArgumentParser(description='Server to monitor radiation experiments')
    parser.add_argument('-c', '--config', metavar='PATH_YAML_FILE', type=str, default="server_parameters.yaml",
                        help='Path to an YAML FILE that contains the server parameters. '
                             'Default is ./server_parameters.yaml')
    parser.add_argument('--enable_curses', default=False, action="store_true", help='Enable curses display')
    args = parser.parse_args()
    # load yaml file
    with open(args.config, 'r') as fp:
        server_parameters = yaml.load(fp, Loader=yaml.SafeLoader)

    server_log_file = server_parameters['server_log_file']
    server_log_store_dir = server_parameters['server_log_store_dir']
    server_ip = server_parameters['server_ip']

    # log in the stdout
    global CONSOLE_CURSES_MANAGER
    if args.enable_curses is True:
        CONSOLE_CURSES_MANAGER = ConsoleCursesManager(daemon=True)
        CONSOLE_CURSES_MANAGER.start()

    logger = logging_setup(logger_name=PARENT_LOGGER_NAME, log_file=server_log_file, enable_curses=args.enable_curses)
    logger.info(f"Python version: {sys.version_info.major}.{sys.version_info.minor} machine:{server_ip}")

    # If a path does not exist, create it
    if os.path.isdir(server_log_store_dir) is False:
        os.mkdir(server_log_store_dir)

    # noinspection SpellCheckingInspection
    # set the exception hook
    threading.excepthook = __machine_thread_exception_handler

    # TO-DO
    # make these params into args or config files
    transfer_ip = "192.168.1.6"
    transfer_port = 1238
    transfer_timeout = 2
    corrupted_output_save_path = './experiment_files'
    Path(corrupted_output_save_path).mkdir(exist_ok=True, parents=True)
    file_transfer_max_connections = 5
    power_controller: PowerController = None

    try:
        transfer_monitor = FileReceiver(
            transfer_ip,
            transfer_port,
            transfer_timeout,
            logger,
            download_path=corrupted_output_save_path,
            max_connections=file_transfer_max_connections,
        )
        transfer_monitor.start()
        logger.debug(f"Starting power controller")
        monitor_polling_ms = 5
        power_controller = PowerController(
            logger=logger,
            update_initial_state = True,
            initial_state = False,
            initial_voltage = 12.0,
            initial_current = 1.3,
            max_voltage = 14.0,
            max_current = 1.5,
            monitor_polling_time = monitor_polling_ms * (1/1000),
            monitor_log_every = int(1000 / monitor_polling_ms),
            verbose=True,
            monitor_log_file='/home/carol/radiation-setup/measurements.log',
        )
        logger.debug(f"Started power controller successfully")
        global PWR_CTRL
        PWR_CTRL = power_controller
        logger.debug(f"Starting power monitor thread")
        power_controller.start_monitor()
        logger.debug(f"Started power monitor thread successfully")
        # Start the server threads
        for m in server_parameters["machines"]:
            if m['enabled']:
                machine = Machine(configuration_file=m["cfg_file"], server_ip=server_ip, logger_name=PARENT_LOGGER_NAME,
                                  server_log_path=server_log_store_dir, power_controller=power_controller)

                logger.info(f"Starting a new thread to listen at {machine}")
                machine.start()
                MACHINE_LIST.append(machine)
    except Exception as err:
        logger.exception(f"General exception:{err}")
        __end_daemon_machines()
        if power_controller is not None:
            power_controller.shutdown()
        # Unknown exit
        sys.exit(-1)

    print(f"Done. Exiting.")


if __name__ == '__main__':
    main()
