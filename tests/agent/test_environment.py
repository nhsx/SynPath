from typing import DefaultDict

from patient_abm import PATIENT_ABM_DIR
from patient_abm.agent.environment import EnvironmentAgent
from patient_abm.agent.patient import PatientAgent
from patient_abm.utils import string_to_datetime

TEST_DATA_DIR = PATIENT_ABM_DIR / "tests" / "data"


def test_initialise_environment_agent():

    environment_id = 3578
    environment_type = "test_env"
    name = "test_env_1"
    patient_present = True
    agent_id = 67890
    created_at = "2021-03-17"

    environment = EnvironmentAgent(
        environment_id=environment_id,
        environment_type=environment_type,
        name=name,
        patient_present=patient_present,
        id_=agent_id,
        created_at=created_at,
    )

    assert environment.id == agent_id
    assert environment.created_at == string_to_datetime(created_at)
    assert environment.__repr__() == (
        f"EnvironmentAgent(id={agent_id}, "
        f"created_at={string_to_datetime(created_at)})"
    )
    assert environment.interactions == ["death"]
    assert isinstance(environment.patient_data, DefaultDict)
    assert isinstance(environment.patient_interaction_history, DefaultDict)
    assert environment.capacity == []
    assert environment.wait_time == []


def test_update_environment():

    environment_id = 3578
    environment_type = "test_env"
    name = "test_env_1"
    patient_present = True
    agent_id = 67890
    created_at = "2021-03-17"

    environment = EnvironmentAgent(
        environment_id=environment_id,
        environment_type=environment_type,
        name=name,
        patient_present=patient_present,
        id_=agent_id,
        created_at=created_at,
    )

    patient_id = 2468
    gender = "female"
    birth_date = "1985-05-24"
    start_time = "2020-12-01"
    agent_id = 12345
    created_at = "2021-03-09"

    patient = PatientAgent(
        patient_id=patient_id,
        gender=gender,
        birth_date=birth_date,
        start_time=start_time,
        id_=agent_id,
        created_at=created_at,
    )

    environment.update(patient)

    assert len(environment.patient_interaction_history) == 1
    assert environment.patient_interaction_history[patient_id] == [
        {
            "time": patient.start_time,
            "last_record_index": 0,
            "interactions": None,
        }
    ]


def test_initialise_from_fhir_environment_agent():

    fhir_paths = [
        TEST_DATA_DIR / "fhir_example_organization.json",
        TEST_DATA_DIR / "fhir_example_location.json",
        TEST_DATA_DIR / "fhir_example_practitioner_0.json",
        TEST_DATA_DIR / "fhir_example_practitioner_1.json",
    ]

    environment = EnvironmentAgent.from_fhir(
        fhir_paths,
        resource_types=[
            "Organization",
            "Location",
            "Practitioner",
            "Practitioner",
        ],
        environment_id="fhir_env",
        server_url=None,
    )


def test_save_and_load_environment_agent():

    fhir_paths = [
        TEST_DATA_DIR / "fhir_example_organization.json",
        TEST_DATA_DIR / "fhir_example_location.json",
        TEST_DATA_DIR / "fhir_example_practitioner_0.json",
        TEST_DATA_DIR / "fhir_example_practitioner_1.json",
    ]

    environment = EnvironmentAgent.from_fhir(
        fhir_paths,
        resource_types=[
            "Organization",
            "Location",
            "Practitioner",
            "Practitioner",
        ],
        environment_id="fhir_env",
        server_url=None,
    )

    environment_agent_path = TEST_DATA_DIR / "environment_agent.tar"

    environment.save(environment_agent_path)

    _environment = EnvironmentAgent.load(environment_agent_path)

    for attr_name in EnvironmentAgent.serialisable_attributes:
        assert getattr(environment, attr_name) == getattr(
            _environment, attr_name
        )

    environment_agent_path.unlink()
