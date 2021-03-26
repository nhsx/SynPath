import datetime
import importlib
import logging
import uuid
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

import dateutil.parser
from dateutil.tz import UTC


def string_to_datetime(
    dt: Optional[Union[str, datetime.datetime]],
    format_str: Optional[str] = None,
    tzinfo: datetime.timezone = datetime.timezone.utc,
) -> datetime.datetime:
    """Convert datetime-like string as datetime object. The default settings
    uses dateutil to automatically parse the string, and returns
    a datetime object with timezone datetime.timezone.utc

    Parameters
    ----------
    dt : Optional[Union[str, datetime.datetime]]
        Datetime string. If dt is already a datetime object or None, returns
        dt
    format_str : Optional[str], optional
        Input format string, by default None
    tzinfo : datetime.timezone, optional
        Timezone, by default datetime.timezone.utc

    Returns
    -------
    datetime.datetime
        Returns dt as a datetime object
    """
    if dt is None or isinstance(dt, datetime.datetime):
        return dt
    if format_str is None:
        return dateutil.parser.parse(dt).astimezone(UTC)
    else:
        return datetime.datetime.strptime(dt, format_str, tzinfo=tzinfo)


def datetime_to_string(
    dt: Optional[Union[str, datetime.datetime]],
    format_str: Optional[str] = None,
) -> str:
    """Return datetime formatted as string. The default settings return df in
    isoformat

    Parameters
    ----------
    dt : Optional[Union[str, datetime.datetime]]
        Datetime object
    format_str : Optional[str], optional
        Output format str, by default None

    Returns
    -------
    str
        Datetime as string
    """
    if dt is None or isinstance(dt, str):
        return dt
    if format_str is None:
        return dt.isoformat()
    else:
        return dt.strftime(format_str)


def load_module_from_path(name: str, path: Union[str, Path]) -> ModuleType:
    """Load module from a path

    Parameters
    ----------
    name : str
        Name of module
    path : Union[str, Path]
        Full path to module

    Returns
    -------
    ModuleType
        Loaded module
    """
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_uuid(type_: str = "urn") -> str:
    """Make unique ID using python uuid.uuid4()

    Parameters
    ----------
    type_ : str, optional
        ID return format, "hex" or "urn", by default "urn"

    Returns
    -------
    str
        Generated unique IDs
    """
    if type_ == "urn":
        return uuid.uuid4().urn
    elif type_ == "hex":
        return uuid.uuid4().hex


def print_log(
    msg: str, print_: bool = False, logger: logging.Logger = None
) -> None:
    """Print and / or log a message

    Parameters
    ----------
    msg : str
        Message string
    print_ : bool, optional
        Whether to pring message, by default False
    logger : logging.Logger, optional
        Logger that, if supplied, message will be written to, by default None
    """
    if logger is None or print_:
        print(msg)
    if logger is not None:
        logger.info(msg)
