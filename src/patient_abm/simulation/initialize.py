import copy
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy
import pandas

from patient_abm import PATIENT_ABM_DIR
from patient_abm.agent.environment import (
    AandEEnvironmentAgent,
    EnvironmentAgent,
    GPEnvironmentAgent,
    COEnvironmentAgent, 
    OPEnvironmentAgent, 
    IPEnvironmentAgent,
)
from patient_abm.agent.patient import PatientAgent
from patient_abm.data_handler.base import DataHandler
from patient_abm.data_handler.fhir import HAPI_FHIR_SERVER_4
from patient_abm.intelligence.interactions.default import death
from patient_abm.simulation.template import (
    parse_config,
    validate_unique_environment_ids,
)
from patient_abm.utils import load_module_from_path


def _initialize_patients_from_attributes(
    attributes: List[dict],
) -> List[PatientAgent]:
    return [PatientAgent(**attribute) for attribute in attributes]


def _initialize_environments_from_attributes(
    attributes: List[dict],
) -> Dict[
    Union[str, int],
    Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent, COEnvironmentAgent, OPEnvironmentAgent, IPEnvironmentAgent],
]:

    environments = []
    environment_ids = []

    for attribute in copy.deepcopy(attributes):

        if "type" in attribute:
            type_ = attribute["type"]
            del attribute["type"]
        else:
            type_ = ""

        attribute["environment_type"] = type_

        if type_ == "a_and_e":
            environment = AandEEnvironmentAgent(**attribute)
        elif type_ == "gp":
            environment = GPEnvironmentAgent(**attribute)
        elif type_ == "community":
            environment = COEnvironmentAgent(**attribute)
        elif type_ == "outpatient":
            environment = OPEnvironmentAgent(**attribute)
        elif type_ == "inpatient":
            environment = IPEnvironmentAgent(**attribute)
        else:
            environment = EnvironmentAgent(**attribute)

        environments.append(environment)
        environment_ids.append(environment.environment_id)

    validate_unique_environment_ids(environments, "environment_id")

    return dict(zip(environment_ids, environments))


def _get_agent_attributes_from_file(file_path: Union[Path, str]) -> List[dict]:

    if str(file_path).endswith(".csv"):
        return pandas.read_csv(file_path).to_dict("records")
    elif str(file_path).endswith(".json"):
        return DataHandler().load_json(file_path)
    else:
        raise ValueError(
            "Loading agents from a file path requires JSON or CSV format. "
            f"{file_path} is unsuitable."
        )


def _initialize_agents(
    config: dict, agents: str
) -> Union[
    List[PatientAgent],
    Dict[
        Union[str, int],
        Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent, COEnvironmentAgent, OPEnvironmentAgent, IPEnvironmentAgent],
    ],
]:
    agent_to_init = {
        "patients": _initialize_patients_from_attributes,
        "environments": _initialize_environments_from_attributes,
    }
    if not isinstance(config[agents], list):
        attributes = _get_agent_attributes_from_file(config[agents])
        # NOTE: modify config here because later _initialize_interaction_mapper
        # accesses config["environments"]
        config[agents] = attributes
    else:
        attributes = config[agents]

    return agent_to_init[agents](attributes)


def _initialize_patients(config: dict):
    return _initialize_agents(config, "patients")


def _initialize_environments(config: dict):
    return _initialize_agents(config, "environments")


def _initialize_default_interaction_mapper() -> Dict[str, Callable]:
    # TODO: improve this that default interactions are added more
    # robustly. In fact, it might be possible to remove this and just
    # add default interactions direclty in the Environment, see for
    # instance the way self.interactions is set in the EnviromentAgent
    # class constructor (which itself is not an optimal implementation
    # but provides examples of different ways to perform this)
    return {
        "death": death,
    }


def _initialize_interaction_mapper(config: dict) -> Dict[str, Callable]:
    """
    Will return a dictionary with keys = string name of function and
    values = function handle

    NOTE: currently assuming 'interactions' are supplied as a list
    for each environment
    """

    interaction_mapper = {}
    for environment_config in config["environments"]:
        interactions = environment_config["interactions"]
        for interaction in interactions:
            module_name, function_name = interaction.split(".")
            module = load_module_from_path(
                module_name,
                Path(config["intelligence_dir"])
                / "interactions"
                / f"{module_name}.py",
            )
            function = getattr(module, function_name)
            interaction_mapper[interaction] = function

    default_interaction_mapper = _initialize_default_interaction_mapper()
    for k, v in default_interaction_mapper.items():
        if k in interaction_mapper:
            raise NameError(
                "Custom interactions cannot have the following names: "
                f"{list(default_interaction_mapper)}"
            )
        interaction_mapper[k] = v
    return interaction_mapper


def _initialize_intelligence(config: dict) -> Callable:

    intelligence_module = load_module_from_path(
        "intelligence", Path(config["intelligence_dir"]) / "intelligence.py"
    )

    return getattr(intelligence_module, "intelligence")


def _initialize_initial_environment_ids(
    config: dict,
    environments: Dict[
        Union[str, int],
        Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent, COEnvironmentAgent, OPEnvironmentAgent, IPEnvironmentAgent],
    ],
    patients: List[PatientAgent],
) -> List[Union[int, str]]:

    environment_ids = list(environments)
    initial_environment_ids = []

    try:
        [initial_environment_id_method] = list(
            config["initial_environment_ids"]
        )
    except ValueError:
        raise ValueError(
            "The simulation config 'initial_environment_ids' field should be "
            "a dictionary with a single key which is either 'from_id', "
            "'from_probability', or 'from_json'."
        )

    if initial_environment_id_method == "from_id":
        id_ = config["initial_environment_ids"]["from_id"]
        if isinstance(id_, int) or isinstance(id_, str):
            initial_environment_ids = [id_] * len(patients)
        elif isinstance(id_, list):
            if len(id_) == 1:
                initial_environment_ids = id_ * len(patients)
            elif len(id_) == len(patients):
                initial_environment_ids = id_

    elif initial_environment_id_method == "from_probability":

        p = config["initial_environment_ids"]["from_probability"]
        initial_environment_ids = numpy.random.choice(
            environment_ids,
            size=len(patients),
            p=p,
        ).tolist()
    elif initial_environment_id_method == "from_json":
        file_path = config["initial_environment_ids"]["from_json"]
        initial_environment_ids = DataHandler().load_json(file_path)
    else:
        raise NameError(
            "Invalid 'initial_environment_ids' method "
            f"{initial_environment_id_method}. Must be one of: 'from_id', "
            "'from_probability', or 'from_json'"
        )
    if len(initial_environment_ids) != len(patients):
        raise ValueError(
            "In template config script, when "
            "'initial_environment_ids' 'from_id' is a list of IDs, "
            "then the number of IDs in the list must be one or the "
            "same as tne number of patients. Currently there are "
            f"{len(patients)} patients and {len(initial_environment_ids)} "
            "initial environment IDs."
        )
    if len(set(initial_environment_ids) - set(environment_ids)) > 0:
        raise ValueError(
            "There are initial environment IDs that are not present "
            "in the list of environments"
        )
    return initial_environment_ids


def _initialize_stopping_condition(config: dict) -> dict:
    try:
        [stopping_condition_name] = list(config["stopping_condition"])
    except ValueError:
        raise ValueError(
            "The simulation config 'stopping_condition' field should be "
            "a dictionary with a single key which is either: "
            "'max_num_steps', 'max_patient_time', or 'max_real_time'. "
            "Detected value is "
            f"'{stopping_condition_name}'"
        )
    if stopping_condition_name not in [
        "max_num_steps",
        "max_patient_time",
        "max_real_time",
    ]:
        raise NameError(
            f"Invalid stopping_condition_name '{stopping_condition_name}'. "
            "Must be one of: 'max_num_steps', 'max_patient_time', or "
            "'max_real_time'"
        )
    stopping_condition_kwargs = {
        "stopping_condition_name": stopping_condition_name,
        "stopping_condition_max_value": list(
            config["stopping_condition"].values()
        )[0],
    }
    return stopping_condition_kwargs


def initialize(
    config: Union[dict, str, Path]
) -> Tuple[
    List[PatientAgent],
    Dict[
        Union[str, int],
        Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent, COEnvironmentAgent, OPEnvironmentAgent, IPEnvironmentAgent],
    ],
    Dict[str, Callable],
    Callable,
    List[Union[str, int]],
    dict,
    int,
    int,
    bool,
    Optional[Union[str, Path]],
]:
    """Initializes the patients, environments, intelligence layer and
    other variables as per the specification in the simulation config

    Parameters
    ----------
    config : Union[dict, str, Path]
        Config dictionary or path to config.json

    Returns
    -------
    patient : PatientAgent
        Patient to simulation
    environments : Dict[
        Union[str, int],
        Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent, COEnvironmentAgent, OPEnvironmentAgent, IPEnvironmentAgent],
    ]
        Environments in simulation
    interaction_mapper : Dict[str, Callable]
        Map from interaction function name to function handle
    intelligence : Callable
        Intelligence function handle
    initial_environment_id : Union[str, int]
        ID of first environment the patient should interact with
    stopping_condition_kwargs : dict
        Stopping condition for simulation
    log_every : int, optional
        Rate of logging, by default 1
    log_intermediate : bool, optional
        Whether to accumulate log messages between log_every and then log all,
        by default False
    hard_stop : int, optional
        Maximum number of steps for simulation - provides hard termination
        for while loop, by default 1e8
    log_patient_record : bool, optional
        Whether to print patient record entries to patient logger,
        by default False
    patient_record_duplicate_action : str, optional
        "skip" or "add" duplicate entries to existing patient record,
        by default "add"
    save_dir : Optional[Union[str, Path]], optional
        Directory to save outputs to, by default None, in which case no saving
        occurs
    fhir_server_url : Optional[str], optional
        Either None or the HAPI FHIR v4 server url
    """

    if isinstance(config, str) or isinstance(config, Path):
        config = parse_config(config)

    config = copy.deepcopy(config)

    # NOTE: order is important - load patients and environments first in case
    #  their information needs to be loaded from a file - config gets updated
    # with this info.
    patients = _initialize_patients(config)
    environments = _initialize_environments(config)

    interaction_mapper = _initialize_interaction_mapper(config)
    intelligence = _initialize_intelligence(config)

    initial_environment_ids = _initialize_initial_environment_ids(
        config, environments, patients
    )
    stopping_condition_kwargs = _initialize_stopping_condition(config)

    log_every = config.get("log_every", 1)
    log_intermediate = config.get("log_intermediate", False)
    hard_stop = config.get("hard_stop", 1e8)
    log_patient_record = config.get("log_patient_record", True)
    save_dir = config.get("save_dir", PATIENT_ABM_DIR / "outputs")
    patient_record_duplicate_action = config.get(
        "patient_record_duplicate_action", "add"
    )

    if config.get("fhir_server_validate", False):
        fhir_server_url = HAPI_FHIR_SERVER_4
    else:
        fhir_server_url = None

    if isinstance(save_dir, str):
        save_dir = Path(save_dir)

    save_dir.mkdir(exist_ok=True, parents=True)

    return (
        patients,
        environments,
        interaction_mapper,
        intelligence,
        initial_environment_ids,
        stopping_condition_kwargs,
        log_every,
        log_intermediate,
        hard_stop,
        log_patient_record,
        patient_record_duplicate_action,
        save_dir,
        fhir_server_url,
    )
