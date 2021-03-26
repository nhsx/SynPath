import logging
import sys
from pathlib import Path
from typing import Optional, Union

from pythonjsonlogger import jsonlogger


def configure_logger(
    log_name: Optional[str] = None,
    log_path: Optional[Union[str, Path]] = None,
    log_level: int = logging.INFO,
    formatter_str: Optional[str] = None,
) -> None:
    """Configure logger and enable logging.

    Parameters
    ----------

    log_name : str
        Name of the log file
    log_path : str
        Path to log file.
    log_level : int
        Level to trigger logging
    formatter_str : str
        Custom formatting. If not supplied defaults to
        "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s - %(lineno)d
         - %(funcName)s - %(message)s\n"
    """
    if formatter_str is None:
        formatter_str = (
            "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s "
            "- %(lineno)d - %(funcName)s - %(message)s\n"
        )
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)
    if log_path is not None:
        Path(log_path).parent.mkdir(exist_ok=True, parents=True)
        handler = logging.FileHandler(log_path)
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = jsonlogger.JsonFormatter(formatter_str)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.handler_set = True
