import logging
import os
import sys
from datetime import datetime


class Logger:
    """
    A reusable logger class that provides logging with console and
    optional file output.
    Removes singleton enforcement to allow more flexibility.
    """

    def __init__(self, name: str = "AppLogger", level: str = "DEBUG"):
        self._logger = logging.getLogger(name)

        if not self._logger.handlers:
            self._logger.setLevel(getattr(
                logging, level.upper(), logging.DEBUG
                )
            )

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            # Console Handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

            # Optional File Handler
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(
                log_dir,
                f"{datetime.now().strftime('%Y-%m-%d')}.log"
            )
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)

    def set_level(self, level: str):
        """Set the logging level dynamically."""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        if level.upper() in level_map:
            self._logger.setLevel(level_map[level.upper()])
        else:
            raise ValueError(f"Invalid log level: {level}")

    def get_logger(self) -> logging.Logger:
        """Return the internal logger instance."""
        return self._logger
