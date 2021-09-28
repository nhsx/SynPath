import pytest

import numpy

from patient_abm.agent.environment import (
    AandEEnvironmentAgent,
    EnvironmentAgent,
    GPEnvironmentAgent,
    COEnvironmentAgent, 
    OPEnvironmentAgent, 
    IPEnvironmentAgent,
)
from patient_abm.simulation.initialize import (
    _initialize_environments,
    _initialize_initial_environment_ids,
    _initialize_patients,
    _initialize_stopping_condition,
)
from patient_abm.utils import string_to_datetime


def test_initialize_patients_from_attributes():
    config = {
        "patients": [
            {
                "patient_id": 0,
                "gender": "male",
                "birth_date": "1978-07-04",
            },
            {
                "patient_id": 1,
                "gender": "female",
                "birth_date": "1956-05-24",
            },
        ]
    }

    patients = _initialize_patients(config)

    for i, patient in enumerate(patients):
        patient_config = config["patients"][i]
        assert patient.patient_id == patient_config["patient_id"]
        assert patient.gender == patient_config["gender"]
        assert patient.birth_date == string_to_datetime(
            patient_config["birth_date"]
        )


def test_initialize_environments_from_attributes():
    # TODO: test environment_id clash
    config = {
        "environments": [
            {
                "environment_id": "minimal",
            },
            {
                "environment_id": "00",
                "type": "clinic",
                "name": "my_local_clinic",
            },
            {
                "environment_id": "01",
                "type": "gp",
                "name": "my_gp",
            },
            {
                "environment_id": "02",
                "type": "a_and_e",
                "name": "a_and_e_charing_cross",
            },
        ]
    }

    environments = _initialize_environments(config)

    assert isinstance(environments["00"], EnvironmentAgent)
    assert isinstance(environments["01"], GPEnvironmentAgent)
    assert isinstance(environments["02"], AandEEnvironmentAgent)
    assert isinstance(environments["03"], COEnvironmentAgent)
    assert isinstance(environments["04"], OPEnvironmentAgent)
    assert isinstance(environments["05"], IPEnvironmentAgent)

    for i, (environment_id, environment) in enumerate(environments.items()):
        environment_config = config["environments"][i]
        print(environment_config)
        assert (
            environment.environment_id == environment_config["environment_id"]
        )
        assert environment.environment_type == environment_config.get(
            "type", ""
        )
        assert environment.name == environment_config.get("name", "")


def test_initialize_initial_environment_ids():
    # TODO: test from json!
    config = {
        "patients": [
            {
                "patient_id": 0,
                "gender": "male",
                "birth_date": "1978-07-04",
            },
            {
                "patient_id": 1,
                "gender": "female",
                "birth_date": "1956-05-24",
            },
        ],
        "environments": [
            {
                "environment_id": 0,
                "type": "clinic",
                "name": "my_local_clinic",
            },
            {
                "environment_id": 1,
                "type": "gp",
                "name": "my_gp",
            },
            {
                "environment_id": 2,
                "type": "a_and_e",
                "name": "a_and_e_charing_cross",
            },
        ],
    }

    patients = _initialize_patients(config)
    environments = _initialize_environments(config)

    config["initial_environment_ids"] = {"from_id": 0}
    initial_environment_ids = _initialize_initial_environment_ids(
        config, environments, patients
    )
    assert initial_environment_ids == [0, 0]

    config["initial_environment_ids"] = {"from_id": [0]}
    initial_environment_ids = _initialize_initial_environment_ids(
        config, environments, patients
    )
    assert initial_environment_ids == [0, 0]

    config["initial_environment_ids"] = {"from_id": [0, 1]}
    initial_environment_ids = _initialize_initial_environment_ids(
        config, environments, patients
    )
    assert initial_environment_ids == [0, 1]

    config["initial_environment_ids"] = {"from_id": [0, 1, 2]}
    with pytest.raises(ValueError):
        initial_environment_ids = _initialize_initial_environment_ids(
            config, environments, patients
        )

    config["initial_environment_ids"] = {"from_id": [0, 3]}
    with pytest.raises(ValueError):
        initial_environment_ids = _initialize_initial_environment_ids(
            config, environments, patients
        )

    numpy.random.seed(0)
    config["initial_environment_ids"] = {"from_probability": [0.1, 0.6, 0.3]}
    initial_environment_ids = _initialize_initial_environment_ids(
        config, environments, patients
    )
    assert initial_environment_ids == [1, 2]

    config["initial_environment_ids"] = {"from_prob": [0.1, 0.6, 0.3]}
    with pytest.raises(NameError):
        initial_environment_ids = _initialize_initial_environment_ids(
            config, environments, patients
        )

    config["initial_environment_ids"] = {
        "from_id": [0, 0],
        "from_probability": [0.1, 0.6, 0.3],
    }
    with pytest.raises(ValueError):
        initial_environment_ids = _initialize_initial_environment_ids(
            config, environments, patients
        )


def test_initialize_stopping_condition():
    config = {}
    config["stopping_condition"] = {"max_num_steps": 100}
    stopping_condition_kwargs = _initialize_stopping_condition(config)
    assert stopping_condition_kwargs == {
        "stopping_condition_name": "max_num_steps",
        "stopping_condition_max_value": 100,
    }

    config["stopping_condition"] = {"max_patient_time": {"days": 5}}
    stopping_condition_kwargs = _initialize_stopping_condition(config)
    assert stopping_condition_kwargs == {
        "stopping_condition_name": "max_patient_time",
        "stopping_condition_max_value": {"days": 5},
    }

    config["stopping_condition"] = {"max_real_time": {"hours": 2}}
    stopping_condition_kwargs = _initialize_stopping_condition(config)
    assert stopping_condition_kwargs == {
        "stopping_condition_name": "max_real_time",
        "stopping_condition_max_value": {"hours": 2},
    }

    config["stopping_condition"] = {"max_time": {"hours": 2}}
    with pytest.raises(NameError):
        stopping_condition_kwargs = _initialize_stopping_condition(config)


# TODO: test remaining features (log_every etc)
