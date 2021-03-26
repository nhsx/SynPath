import copy
import datetime
from dataclasses import asdict

from patient_abm import PATIENT_ABM_DIR
from patient_abm.agent.patient import (
    PatientAgent,
    PatientRecordEntry,
    wrap_fhir_resource,
)
from patient_abm.data_handler.fhir import FHIRHandler, create_fhir_bundle
from patient_abm.utils import string_to_datetime

TEST_DATA_DIR = PATIENT_ABM_DIR / "tests" / "data"


def test_initialize_patient_agent_minimal():

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

    patient_profile = {
        "resource_type": "Patient",
        "id": str(patient_id),
        "gender": gender,
        "birth_date": birth_date,
    }
    wrapped_entry = wrap_fhir_resource(
        patient_profile,
        patient_time=string_to_datetime(start_time),
        environment_id=-1,
        tag="patient_profile",
    )

    wrapped_entry["real_time"] = string_to_datetime(created_at)
    wrapped_entry["record_index"] = 0
    wrapped_entry["entry_id"] = patient.record[0].entry_id

    initial_patient_resource = PatientRecordEntry(**wrapped_entry)

    assert patient.id == agent_id
    assert patient.created_at == string_to_datetime(created_at)
    assert patient.__repr__() == (
        f"PatientAgent(id={agent_id}, "
        f"created_at={string_to_datetime(created_at)})"
    )
    assert patient.record == [initial_patient_resource]


def test_initialize_patient_agent_with_comorbities():

    patient_id = 2468
    gender = "female"
    birth_date = "1985-05-24"
    start_time = "2020-12-01"
    agent_id = 12345
    created_at = "2021-03-09"

    comorbidity = {
        "resource_type": "Condition",
        "name": "Diabetes",
        "start": "2018-10-21",
    }
    wrapped_comorbidity = wrap_fhir_resource(
        comorbidity,
        patient_time=string_to_datetime(comorbidity["start"]),
        environment_id=-1,
        tag="comorbidity_diabetes",
    )
    wrapped_comorbidity["real_time"] = string_to_datetime(created_at)

    telecom = {"system": "phone", "value": "555-113-5410", "use": "home"}
    age = 35

    kwargs = {
        "patient__telecom": telecom,
        "age": age,
    }

    initial_record = [wrapped_comorbidity]

    patient = PatientAgent(
        patient_id=patient_id,
        gender=gender,
        birth_date=birth_date,
        start_time=start_time,
        id_=agent_id,
        created_at=created_at,
        record=initial_record,
        **kwargs,
    )

    patient_profile = {
        "resource_type": "Patient",
        "id": str(patient_id),
        "gender": gender,
        "birth_date": birth_date,
        "telecom": telecom,
    }
    wrapped_patient_profile = wrap_fhir_resource(
        patient_profile,
        patient_time=string_to_datetime(start_time),
        environment_id=-1,
        tag="patient_profile",
    )

    wrapped_patient_profile["real_time"] = string_to_datetime(created_at)
    wrapped_patient_profile["record_index"] = 0
    wrapped_patient_profile["entry_id"] = patient.record[0].entry_id

    initial_patient_entry = PatientRecordEntry(**wrapped_patient_profile)

    wrapped_comorbidity["real_time"] = string_to_datetime(created_at)
    wrapped_comorbidity["record_index"] = 1
    wrapped_comorbidity["entry_id"] = patient.record[1].entry_id

    comorbidity_entry = PatientRecordEntry(**wrapped_comorbidity)

    assert patient.id == agent_id
    assert patient.created_at == string_to_datetime(created_at)
    assert (
        patient.__repr__() == f"PatientAgent(id={agent_id}, "
        f"created_at={string_to_datetime(created_at)})"
    )
    assert patient.age == age
    assert patient.patient__telecom == telecom
    assert len(patient.record) == 2
    assert patient.record[0] == initial_patient_entry
    assert patient.record[1] == comorbidity_entry
    assert len(patient.conditions) == 1
    assert len(patient.medications) == 0
    assert len(patient.actions) == 0


def test_update_patient_agent():

    patient_id = 2468
    gender = "female"
    birth_date = "1985-05-24"
    patient_start_time = "2020-12-01"
    agent_id = 12345
    created_at = "2021-03-09"

    patient = PatientAgent(
        patient_id=patient_id,
        gender=gender,
        birth_date=birth_date,
        patient_start_time=patient_start_time,
        id_=agent_id,
        created_at=created_at,
    )

    assert len(patient.record) == 1
    assert len(patient.conditions) == 0

    comorbidity = {
        "resource_type": "Condition",
        "name": "Diabetes",
        "start": "2018-10-21",
    }
    wrapped_comorbidity = wrap_fhir_resource(
        comorbidity,
        patient_time=string_to_datetime(comorbidity["start"]),
        environment_id=-1,
        tag="comorbidity_diabetes",
    )
    wrapped_comorbidity["real_time"] = string_to_datetime(created_at)

    patient.update([wrapped_comorbidity])

    wrapped_comorbidity["record_index"] = 1
    wrapped_comorbidity["entry_id"] = patient.record[1].entry_id

    assert len(patient.record) == 2
    assert len(patient.conditions) == 1
    assert asdict(patient.record[-1]) == wrapped_comorbidity

    patient.update([wrapped_comorbidity], skip_existing=False)

    assert len(patient.record) == 3
    assert len(patient.conditions) == 1
    assert asdict(patient.record[-1]) == wrapped_comorbidity

    patient.update([wrapped_comorbidity], skip_existing=True)

    assert len(patient.record) == 3
    assert len(patient.conditions) == 1
    assert asdict(patient.record[-1]) == wrapped_comorbidity

    assert patient.conditions["active"][0]
    assert patient.conditions["end"][0] is None

    wrapped_comorbidity = copy.deepcopy(wrapped_comorbidity)
    wrapped_comorbidity["entry"]["end"] = "2020-10-21"

    patient.update([wrapped_comorbidity], skip_existing=True)

    assert len(patient.record) == 4
    assert len(patient.conditions) == 1
    assert asdict(patient.record[-1]) == wrapped_comorbidity

    assert not patient.conditions["active"][0]
    assert patient.conditions["end"][0] == string_to_datetime(
        wrapped_comorbidity["entry"]["end"]
    )

    patient_agent_path = TEST_DATA_DIR / "patient_agent.tar"

    patient.save(patient_agent_path)

    _patient = PatientAgent.load(patient_agent_path)

    dfs = ["conditions", "medications", "actions"]

    for attr_name in PatientAgent.serialisable_attributes:
        if attr_name in dfs:
            # NOTE: there is some discreapncy between the two data frames:
            # in one, the timestamps can appear with timezone tz="tzutc()"
            # whereas in the other they are tz="UTC", and this causes the
            # equality check to fail - this is why .astype(str) has been
            # applied to both dataframes. We leave it to future work to
            # iron out this detail
            assert (
                getattr(patient, attr_name)
                .astype(str)
                .equals(getattr(_patient, attr_name).astype(str))
            )
        else:
            assert getattr(patient, attr_name) == getattr(_patient, attr_name)

    patient_agent_path.unlink()


def test_patient_conditions_update():
    patient_id = 2468
    gender = "female"
    birth_date = "1985-05-24"

    patient = PatientAgent(
        patient_id=patient_id,
        gender=gender,
        birth_date=birth_date,
    )

    condition_entry = {
        "resource_type": "Condition",
        "name": "Fever",
        "start": "2021-03-21",
    }

    patient_time = datetime.datetime.now(patient.tz)
    patient.update([wrap_fhir_resource(condition_entry, patient_time)])
