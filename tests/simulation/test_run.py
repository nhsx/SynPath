import copy
from pathlib import Path

from patient_abm import PATIENT_ABM_DIR
from patient_abm.simulation.initialize import initialize
from patient_abm.simulation.run import run_patient_simulation
from patient_abm.simulation.template import parse_config

TEST_DATA_DIR = PATIENT_ABM_DIR / "tests" / "data"


def test_simulate():
    # TODO: load config from template / example instead and
    # delete the intelligence folder in this directory

    save_dir = TEST_DATA_DIR / "test_run_outputs"

    config = {
        "patients": str(TEST_DATA_DIR / "patients_config.json"),
        "environments": str(TEST_DATA_DIR / "environments_config.json"),
        "intelligence_dir": str(
            PATIENT_ABM_DIR / "tests" / "simulation" / "intelligence"
        ),
        "initial_environment_ids": {"from_id": 0},
        "stopping_condition": {"max_patient_time": {"days": 90}},
        "log_every": 1,
        "hard_stop": 100,
        "log_patient_record": True,
        "save_dir": str(save_dir),
        "log_intermediate": False,
        "fhir_server_validate": False,
        "patient_record_duplicate_action": "skip",
    }

    config = parse_config(config)

    simulation_id_prefix = "simulation_for_patient"

    # Delete any existing log files so they don't grow
    for patient in config["patients"]:
        for log_name in ["main", "patient"]:
            log_file = Path(
                save_dir
                / f"{simulation_id_prefix}_{patient['patient_id']}"
                / f"{log_name}.log"
            )

            # TODO: python 3.7 test fails for some reason if use
            # next line
            # log_file.unlink(missing_ok=True)

            if log_file.exists():
                log_file.unlink()

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

    patient_id_to_agents = {}

    for patient, environments, initial_environment_id in zip(
        patients, environments_copies, initial_environment_ids
    ):

        simulation_id = f"{simulation_id_prefix}_{patient.patient_id}"

        patient, environments, _simulation_id = run_patient_simulation(
            simulation_id,
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

        assert simulation_id == _simulation_id

        patient_id_to_agents[patient.patient_id] = {
            "patient": patient,
            "envinroments": environments,
            "simulation_id": simulation_id,
        }
