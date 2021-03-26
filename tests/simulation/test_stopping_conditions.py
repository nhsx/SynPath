import pytest

from patient_abm.simulation.stopping_condition import (
    _max_num_steps_stopping_condition,
    _max_time_stopping_condition,
    stopping_condition,
)
from patient_abm.utils import string_to_datetime

test_data = [
    (10, 20, False),
    (20, 20, True),
    (30, 20, True),
]


@pytest.mark.parametrize("step, max_num_steps, expected", test_data)
def test_max_num_steps_stopping_condition(step, max_num_steps, expected):
    is_stop = _max_num_steps_stopping_condition(step, max_num_steps)
    assert is_stop is expected

    is_stop = stopping_condition(
        stopping_condition_name="max_num_steps",
        stopping_condition_max_value=max_num_steps,
        step=step,
    )
    assert is_stop is expected


test_data = [
    ({"days": 20}, False),
    ({"days": 6}, True),
    ({"days": 2}, True),
]


@pytest.mark.parametrize("max_time, expected", test_data)
def test_max_time_stopping_condition(max_time, expected):
    start_time = string_to_datetime("2021-02-01")
    time = string_to_datetime("2021-02-07")

    is_stop = _max_time_stopping_condition(time, start_time, max_time)
    assert is_stop is expected

    is_stop = stopping_condition(
        stopping_condition_name="max_patient_time",
        stopping_condition_max_value=max_time,
        patient_time=time,
        patient_start_time=start_time,
    )
    assert is_stop is expected

    is_stop = stopping_condition(
        stopping_condition_name="max_real_time",
        stopping_condition_max_value=max_time,
        real_time=time,
        real_start_time=start_time,
    )
    assert is_stop is expected


def test_stopping_condition():
    with pytest.raises(NameError):
        stopping_condition(
            stopping_condition_name="max_time",
            stopping_condition_max_value=None,
            real_time=None,
            real_start_time=None,
        )
