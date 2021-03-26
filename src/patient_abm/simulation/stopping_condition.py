import datetime
from typing import Optional, Union


def _max_num_steps_stopping_condition(step: int, max_num_steps: int) -> bool:
    return step >= max_num_steps


def _max_time_stopping_condition(
    time: datetime.datetime,
    start_time: datetime.datetime,
    max_time: datetime.datetime,
) -> bool:
    return time - start_time >= datetime.timedelta(**max_time)


def stopping_condition(
    stopping_condition_name: str,
    stopping_condition_max_value: Optional[
        Union[int, datetime.datetime]
    ] = None,
    step: Optional[int] = None,
    patient_start_time: Optional[datetime.datetime] = None,
    patient_time: Optional[datetime.datetime] = None,
    real_start_time: Optional[datetime.datetime] = None,
    real_time: Optional[datetime.datetime] = None,
) -> bool:
    """Check for simulation stopping condition and if condition
    satisfied returns True i.e. stop

    Parameters
    ----------
    stopping_condition_name : str
        Name of stopping condition, either 'max_num_steps', 'max_patient_time'
        or 'max_real_time'
    stopping_condition_max_value : Optional[
        Union[int, datetime.datetime]
    ], optional
        The upper value for the stopping condition, by default None
    step : Optional[int], optional
        The current simulation step, used by max_num_steps stopping condition,
        by default None
    patient_start_time : Optional[datetime.datetime], optional
        The simulation patient_start_time, used by max_patient_time
        stopping condition, by default None
    patient_time : Optional[datetime.datetime], optional
        The current simulation patient_time, used by max_patient_time
        stopping condition, by default None
    real_start_time : Optional[datetime.datetime], optional
        The simulation real_start_time, used by max_real_time
        stopping condition, by default None
    real_time : Optional[datetime.datetime], optional
        The current simulation real_time, used by max_real_time
        stopping condition, by default None

    Returns
    -------
    bool
        Whether the simulatoin should stop

    Raises
    ------
    NameError
        If stopping_condition_name is none of 'max_num_steps',
        'max_patient_time' or 'max_real_time'
    """

    if stopping_condition_name == "max_num_steps":
        return _max_num_steps_stopping_condition(
            step, stopping_condition_max_value
        )
    elif stopping_condition_name == "max_patient_time":
        return _max_time_stopping_condition(
            patient_time, patient_start_time, stopping_condition_max_value
        )
    elif stopping_condition_name == "max_real_time":
        return _max_time_stopping_condition(
            real_time, real_start_time, stopping_condition_max_value
        )
    else:
        raise NameError(
            f"Invalid stopping_condition_name '{stopping_condition_name}'. "
            "Must be one of: 'max_num_steps', 'max_patient_time', or "
            "'max_real_time'"
        )
