import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas
from pydantic import BaseModel, parse_obj_as

from patient_abm.agent.environment import (
    AandEEnvironmentAgent,
    EnvironmentAgent,
    GPEnvironmentAgent,
)
from patient_abm.data_handler.base import DataHandler


class Gender(str, Enum):
    male = "male"
    female = "female"


class PatientConfig(BaseModel):
    # TODO: add more?
    patient_id: Union[int, str]
    gender: Gender
    birth_date: Union[str, datetime.datetime]
    start_time: Optional[Union[str, datetime.datetime]]
    name: Optional[str]
    kwargs: Optional[dict]


class EnvironmentConfig(BaseModel):
    # TODO: add more?
    environment_id: Union[int, str]
    environment_type: Optional[str]
    name: Optional[str]
    patient_present: Optional[bool]
    location: Optional[dict]
    organization: Optional[dict]
    practitioners: Optional[list]
    interactions: Optional[List[str]]
    kwargs: Optional[dict]


class InitialEnvironmentMethod(str, Enum):
    from_id = "from_id"
    from_probability = "from_probability"
    from_json = "from_json"


class StoppingConditionName(str, Enum):
    max_num_steps = "max_num_steps"
    max_real_time = "max_real_time"
    max_patient_time = "max_patient_time"


class TimeDeltaUnits(str, Enum):
    days = "days"
    seconds = "seconds"
    microseconds = "microseconds"
    milliseconds = "milliseconds"
    minutes = "minutes"
    hours = "hours"
    weeks = "weeks"


class PatientRecordDuplicateAction(str, Enum):
    add = "add"
    skip = "skip"


class Config(BaseModel):
    patients: List[PatientConfig]
    environments: List[EnvironmentConfig]
    intelligence_dir: str
    save_dir: str
    initial_environment_ids: Dict[
        InitialEnvironmentMethod, Union[int, List[int], str]
    ]
    stopping_condition: Dict[
        StoppingConditionName, Union[int, Dict[TimeDeltaUnits, int]]
    ]
    log_every: int
    log_intermediate: bool
    hard_stop: int
    log_patient_record: bool
    fhir_server_validate: bool
    patient_record_duplicate_action: PatientRecordDuplicateAction


def _parse_agents_config_from_file(
    agents_path: Union[str, Path],
    agents: str,
) -> List[dict]:

    # TODO: populate these lists automatically?
    csv_columns_to_eval = {
        "patients": ["kwargs"],
        "environments": ["interactions", "kwargs"],
    }
    if agents == "patients":
        agent_config = PatientConfig
    elif agents == "environments":
        agent_config = EnvironmentConfig
    else:
        raise ValueError(
            f"Invalid agents {agents}. Must be either 'patients' or "
            "'environments'"
        )

    agents_path = Path(agents_path)

    if agents_path.suffix == ".json":
        agents_config = DataHandler().load_json(agents_path)
    elif agents_path.suffix == ".csv":
        agents_config = pandas.read_csv(agents_path)
        for column in csv_columns_to_eval[agents]:
            if column not in agents_config:
                continue
            agents_config[column] = agents_config[column].apply(
                lambda x: eval(x)
            )
        agents_config = agents_config.to_dict("records")
    else:
        raise ValueError(
            f"When initialising {agents} from a file the "
            "format must be either json or csv."
        )

    parse_obj_as(List[agent_config], agents_config)

    return agents_config


def validate_unique_environment_ids(
    environments: Union[
        List[dict],
        List[
            Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent]
        ],
    ],
    id_key: str = "environment_id",
) -> None:
    """Checks that environments in a list all have unique environment_ids

    Parameters
    ----------
    environments : Union[
        List[dict],
        List[ Union[
            AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent
        ]
    ], ]
        List of environments or environment kwargs
    id_key : str
        Key to check uniqueness for, by default "environment_id"

    Raises
    ------
    ValueError
        Error raised isf duplicate found
    """

    # Validate unique environment_ids strictly, i.e. don't allow if same
    # stringified value
    environment_ids = set()
    for e in environments:
        if isinstance(e, dict):
            environment_id = str(e[id_key])
        else:
            # If EvironmentAgent class
            environment_id = str(getattr(e, id_key))
        if environment_id in environment_ids:
            raise ValueError(
                "There are multiple environments with the same ID. "
                f"Found at least two instances of {e.environment_id}. "
                "Environment IDs must be unique."
            )
        else:
            environment_ids.add(environment_id)


def parse_config(config: Union[dict, str, Path]) -> dict:
    """Parse and validate config file

    Parameters
    ----------
    config : Union[dict, str, Path]
        Config data, either loaded as dictionary or path to file

    Returns
    -------
    dict
        Return config if passes validation, else error is raised
    """

    if isinstance(config, str) or isinstance(config, Path):
        config = DataHandler().load_json(config)

    for agents in ["patients", "environments"]:
        if isinstance(config[agents], str):
            config[agents] = _parse_agents_config_from_file(
                config[agents], agents
            )

    validate_unique_environment_ids(config["environments"], "environment_id")

    Config(**config)

    return config
