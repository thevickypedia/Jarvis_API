import pathlib
import time
from multiprocessing import Manager, Process
from multiprocessing.managers import DictProxy  # noqa
from typing import NoReturn

from jarvis_ui.modules.logger import logger


def initiator(status_manager: DictProxy) -> NoReturn:
    """Starts main process to activate Jarvis and process requests via API calls."""
    from jarvis_ui.executables.starter import Activator, env, heart_beat
    from jarvis_ui.modules.timer import RepeatedTimer
    if env.heart_beat:
        logger.info("Initiating heart beat")
        timer = RepeatedTimer(function=heart_beat, interval=env.heart_beat, args=(status_manager,))
        timer.start()
    else:
        timer = None
    try:
        status_manager["LOCKED"] = False
        Activator().start(status_manager=status_manager)
    except KeyboardInterrupt:
        if timer:
            timer.stop()
        return


def terminator(process: Process) -> NoReturn:
    """Terminates the process.

    Args:
        process: Takes the process object as an argument.
    """
    logger.info(f"Terminating {process.name} [{process.pid}]")
    process.terminate()
    if process.is_alive():
        logger.warning(f"Process {process.name} [{process.pid}] is still alive. Killing it.")
        process.kill()
        process.join(timeout=1e-01)
        try:
            logger.info(f"Closing process: {process.name} [{process.pid}]")
            process.close()  # Close immediately instead of waiting to be garbage collected
        except ValueError as error:
            # Expected when join timeout is insufficient. The resources will be released eventually but not immediately.
            logger.error(error)


def start() -> NoReturn:
    """Initiates Jarvis as a child process."""
    # Import within a function to be called repeatedly
    from jarvis_ui.modules.models import env  # noqa: F401
    status_manager = Manager().dict()
    status_manager["LOCKED"] = False  # Instantiate DictProxy
    # todo: Process won't work for Linux as it doesn't stream on audio I/O devices in multiple processes
    process = Process(target=initiator, args=(status_manager,))
    process.name = pathlib.Path(__file__).stem
    process.start()
    logger.info(f"Initiating as {process.name} [{process.pid}]")
    while True:
        if not process.is_alive():  # Terminated
            logger.info(f"Process {process.name}[{process.pid}] died. Ending loop.")
            return
        if status_manager["LOCKED"] is None:  # Neither locked nor unlocked, so restart
            logger.info("Lock status was set to None")
            terminator(process=process)
            break
        time.sleep(1)
    start()
