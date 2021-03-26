import copy
import datetime
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from patient_abm.agent.environment import (
    AandEEnvironmentAgent,
    EnvironmentAgent,
    GPEnvironmentAgent,
)
from patient_abm.agent.patient import PatientAgent, wrap_fhir_resource
from patient_abm.data_handler.fhir import (
    FHIRValidationError,
    generate_patient_fhir_bundle,
)
from patient_abm.log import configure_logger
from patient_abm.simulation.initialize import initialize
from patient_abm.simulation.stopping_condition import stopping_condition
from patient_abm.utils import make_uuid


def _create_simulation_log_msg(
    status: str,
    simulation_id: Union[int, str],
    real_start_time: datetime.datetime,
    real_time: datetime.datetime,
    step: int,
    patient: PatientAgent,
    patient_time: datetime.datetime,
    environment: EnvironmentAgent,
    next_environment_id: Union[str, int],
    interaction_names: List[str],
    next_environment_id_to_prob: Dict[Union[str, int], float],
    next_environment_id_to_time: Dict[Union[str, int], datetime.timedelta],
    **kwargs,
) -> None:

    return {
        "simulation_id": simulation_id,
        "simulation_status": status,
        "simulation_created_at": real_start_time,
        "simulation_time": real_time,
        "simulation_time_elapsed": real_time - real_start_time,
        "simulation_step": step,
        "interaction_names": interaction_names,
        "patient_id": patient.patient_id,
        "patient_time": patient_time,
        "patient_time_elapsed": patient_time - patient.start_time,
        "environment_id": environment.environment_id,
        "next_environment_id": next_environment_id,
        "number_of_patient_record_entries": len(patient.record),
        **kwargs,
    }


def _update_patient_and_environment(
    patient: PatientAgent,
    environment: Union[
        AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent
    ],
    interactions: List[str],
    simulation_step: int,
    patient_time: datetime.datetime,
    update_data: dict,
    patient_record_duplicate_action: str,
    main_logger: logging.Logger,
    patient_logger: logging.Logger,
) -> None:

    patient.update(
        [
            wrap_fhir_resource(
                entry,
                patient_time,
                environment.environment_id,
                interactions,
                simulation_step,
            )
            for entry in update_data["new_patient_record_entries"]
        ],
        logger=patient_logger,
        skip_existing=patient_record_duplicate_action == "skip",
    )
    environment.update(patient, update_data.get("patient_data"))


# TODO: talk about default updating
def run_patient_simulation(
    simulation_id: Union[str, int],
    patient: PatientAgent,
    environments: Dict[
        Union[str, int],
        Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent],
    ],
    interaction_mapper: Dict[str, Callable],
    intelligence: Callable,
    initial_environment_id: Union[str, int],
    stopping_condition_kwargs: dict,
    log_every: int = 1,
    log_intermediate: bool = False,
    hard_stop: int = 1e8,
    log_patient_record: bool = False,
    patient_record_duplicate_action: str = "add",
    save_dir: Optional[Union[str, Path]] = None,
    fhir_server_url: Optional[str] = None,
) -> Tuple[
    PatientAgent,
    List[Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent]],
]:
    """Run a simulation for a single patient. Runs in a while loop. Applies
    intelligence layer at every step of the loop, updates patients and
    environments, and if save_dir is not None saves:

    - save_dir / simulation_id / agents / patient_{patient_id}.tar
    - save_dir / simulation_id / agents / environment_{environment_id_0}.tar
    - save_dir / simulation_id / agents / environment_{environment_id_1}.tar
    ...
    - save_dir / simulation_id / fhir /  bundle.json
    - save_dir / simulation_id / main.log
    - save_dir / simulation_id / patient.log

    Parameters
    ----------
    simulation_id : Union[str, int]
        Simulation ID, is None then will automatically be set
    patient : PatientAgent
        Patient to simulation
    environments : Dict[
        Union[str, int],
        Union[AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent],
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
        If not None, will validate FHIR output using online server,
        by default None

    Returns
    -------
    Tuple[
        PatientAgent,
        List[Union[
            AandEEnvironmentAgent, EnvironmentAgent, GPEnvironmentAgent
            ]
        ], ]
        Returns updated patients and environments
    """

    if simulation_id is None:
        simulation_id = make_uuid()

    if log_every < 5:
        print(
            f"WARNING: Simulation with simulation_id={simulation_id} "
            f"will log every {log_every} steps. Such frequent logging "
            "may slow down the simulation."
        )

    if save_dir is not None:
        if isinstance(save_dir, str):
            save_dir = Path(save_dir)

        simulation_dir = save_dir / simulation_id
        simulation_dir.mkdir(exist_ok=True, parents=True)

        print(
            f"Patient {patient.patient_id} simulation outputs saved to "
            f"{simulation_dir}\n"
        )

        configure_logger("simulate_main_logger", simulation_dir / "main.log")
        configure_logger(
            "simulate_patient_logger", simulation_dir / "patient.log"
        )

    else:

        configure_logger("simulate_main_logger")
        configure_logger("simulate_patient_logger")

    main_logger = logging.getLogger("simulate_main_logger")
    patient_logger = logging.getLogger("simulate_patient_logger")

    patient_time = patient.start_time
    environment = environments[initial_environment_id]

    step = 0
    real_start_time = datetime.datetime.now()
    real_time = real_start_time

    last_n_patient_record_entries = 0

    is_stop = stopping_condition(
        step=step,
        patient_start_time=patient.start_time,
        patient_time=patient_time,
        real_start_time=real_start_time,
        real_time=real_time,
        **stopping_condition_kwargs,
    )

    next_environment_id = None
    interaction_names = None

    stopping_reason = "hard_stop"

    simulation_log_msgs = []

    while not is_stop:
        if step >= hard_stop:
            break

        (
            patient,
            environment,
            patient_time,
            update_data,
            next_environment_id,
            interaction_names,
            next_environment_id_to_prob,  # TODO; currenly not saved
            next_environment_id_to_time,  # TODO; currenly not saved
        ) = intelligence(
            patient, environment, patient_time, interaction_mapper
        )

        _update_patient_and_environment(
            patient,
            environment,
            interaction_names,
            step,
            patient_time,
            update_data,
            patient_record_duplicate_action,
            main_logger,
            patient_logger,
        )

        real_time = datetime.datetime.now()
        step += 1

        if log_intermediate:
            simulation_log_msgs.append(
                _create_simulation_log_msg(
                    "running",
                    simulation_id,
                    real_start_time,
                    real_time,
                    step - 1,
                    patient,
                    patient_time,
                    environment,
                    next_environment_id,
                    interaction_names,
                    next_environment_id_to_prob,
                    next_environment_id_to_time,
                )
            )

        if step % log_every == 0:
            if log_patient_record:
                last_n_patient_record_entries = len(
                    update_data["new_patient_record_entries"]
                )
            patient.log_state(
                patient_logger,
                log_last_n_record_entries=last_n_patient_record_entries,
            )
            # TODO: environment.log_state()?
            simulation_log_msgs.append(
                _create_simulation_log_msg(
                    "running",
                    simulation_id,
                    real_start_time,
                    real_time,
                    step - 1,
                    patient,
                    patient_time,
                    environment,
                    next_environment_id,
                    interaction_names,
                    next_environment_id_to_prob,
                    next_environment_id_to_time,
                )
            )
            for msg in simulation_log_msgs:
                main_logger.info(msg)

            simulation_log_msgs = []

        environments[environment.environment_id] = environment

        if not patient.alive:
            # TODO: maybe not stop here, may want to do clean up actions
            # e.g. extract & donate organs
            is_stop = True
            stopping_reason = "death"
            break

        is_stop = stopping_condition(
            step=step,
            patient_start_time=patient.start_time,
            patient_time=patient_time,
            real_start_time=real_start_time,
            real_time=real_time,
            **stopping_condition_kwargs,
        )
        if not is_stop:
            environment = environments[next_environment_id]
        else:
            stopping_reason = stopping_condition_kwargs[
                "stopping_condition_name"
            ]

    msg = _create_simulation_log_msg(
        "finished",
        simulation_id,
        real_start_time,
        real_time,
        step,
        patient,
        patient_time,
        environment,
        next_environment_id,
        interaction_names,
        next_environment_id_to_prob,
        next_environment_id_to_time,
        **{"stopping_reason": stopping_reason},
    )
    main_logger.info(msg)

    if save_dir is not None:

        agents_dir = simulation_dir / "agents"
        agents_dir.mkdir(exist_ok=True, parents=True)

        patient.save(agents_dir / f"patient_{patient.patient_id}.tar")
        for environment_id, environment in environments.items():
            environment.save(agents_dir / f"environment_{environment_id}.tar")

        fhir_dir = simulation_dir / "fhir"
        fhir_dir.mkdir(exist_ok=True, parents=True)

        try:
            generate_patient_fhir_bundle(
                patient,
                environments,
                bundle_type="transaction",
                validate=True,
                server_url=fhir_server_url,
                save_path=fhir_dir / "bundle.json",
            )
        except FHIRValidationError as e:
            main_logger.error(
                "FHIRValidationError: Could not generate FHIR bundle for "
                f"patient_id {patient.patient_id}: {e}"
            )

    return patient, environments, simulation_id


def simulate(config: dict) -> dict:
    """Run simulation by running the simulaion for one patient at a time,
    looping over patients.

    - Loads and validates the config json file
    - Initializes the patients, environments, intelligence layer and
    other variables as per the specification in the config file
    - Runs the simulation by looping over patients, with logging
    - Saves the outputs in the config file save_dir

    Parameters
    ----------
    config : dict
        Config for the simulation

    Returns
    -------
    dict
        Return final patients and environments for each patient simulation
    """
    # TODO: parallelise

    (
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
    ) = initialize(config)

    environments_copies = [
        copy.deepcopy(environments) for _ in range(len(patients))
    ]

    # TODO: decide whether save_dir naming convention / folder
    # depth structure should change for multiple patients

    patient_id_to_agents = {}

    for patient, environments, initial_environment_id in zip(
        patients, environments_copies, initial_environment_ids
    ):

        patient, environments, simulation_id = run_patient_simulation(
            None,
            patient,
            environments,
            interaction_mapper,
            intelligence,
            initial_environment_id,
            stopping_condition_kwargs,
            log_every,
            log_intermediate,
            hard_stop,
            log_patient_record,
            patient_record_duplicate_action,
            save_dir,
            fhir_server_url,
        )
        patient_id_to_agents[patient.patient_id] = {
            "patient": patient,
            "envinroments": environments,
            "simulation_id": simulation_id,
        }

    return patient_id_to_agents