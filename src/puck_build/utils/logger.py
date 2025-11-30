from enum import Enum


class LogLevel(Enum):
    """Defines the logging severity levels."""

    ERROR = 0
    WARNING = 1
    INFO = 2
    VERBOSE = 3
    DEBUG = 4


class Logger:
    """A simple logger abstraction for controlled output."""

    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        self.min_level = min_level

    def _log(self, level: LogLevel, message: str):
        if level.value <= self.min_level.value:
            prefix = level.name
            print(f"[{prefix:<7}] {message}")

    def print(self, message: str):
        print(message)

    def error(self, message: str):
        self._log(LogLevel.ERROR, message)

    def warning(self, message: str):
        self._log(LogLevel.WARNING, message)

    def info(self, message: str):
        self._log(LogLevel.INFO, message)

    def verbose(self, message: str):
        self._log(LogLevel.VERBOSE, message)

    def debug(self, message: str):
        self._log(LogLevel.DEBUG, message)


logger = Logger(LogLevel.INFO)


def calculate_log_level(verbosity_count: int) -> LogLevel:
    """
    Calculates the desired LogLevel based on the number of -v flags.

    Default Level: WARNING
    -v (count=1): INFO
    -vv (count=2): VERBOSE
    -vvv (count=3): DEBUG
    """

    initial_level_value = LogLevel.WARNING.value

    target_value = initial_level_value + verbosity_count

    max_value = LogLevel.DEBUG.value
    final_value = min(target_value, max_value)

    for level in LogLevel:
        if level.value == final_value:
            return level

    return LogLevel.WARNING
