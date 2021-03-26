import json

import pytest

from patient_abm import PATIENT_ABM_DIR
from patient_abm.agent.patient import (
    PatientAgent,
    PatientRecordEntry,
    wrap_fhir_resource,
)
from patient_abm.data_handler.fhir import (
    HAPI_FHIR_SERVER_4,
    FHIRHandler,
    FHIRValidationError,
    convert_fhir_to_patient_record_entry,
    convert_patient_record_entry_to_fhir,
    generate_patient_fhir_bundle,
    generate_patient_fhir_resources,
    get_supported_fhir_resources,
)
from patient_abm.utils import datetime_to_string, string_to_datetime

TEST_DATA_DIR = PATIENT_ABM_DIR / "tests" / "data"


test_data = [
    (
        {"resource": "Patient"},
        "Patient",
    ),
    (
        {"resource_type": "patient"},
        "Patient",
    ),
]


@pytest.mark.parametrize("data, resource_type", test_data)
def test_validate_raise_fhir_validation_error(data, resource_type):

    with pytest.raises(FHIRValidationError):
        FHIRHandler().validate(data, resource_type)


test_data = [
    (
        "Bundle",
        "Bundle",
        None,
    ),
    (
        "Bundle",
        "Patient",
        None,
    ),
    (
        "Bundle",
        "Bundle",
        HAPI_FHIR_SERVER_4,
    ),
    (
        "Bundle",
        "Patient",
        HAPI_FHIR_SERVER_4,
    ),
]


@pytest.mark.parametrize(
    "input_resource_type, output_resource_type, server_url", test_data
)
def test_load_resources(input_resource_type, output_resource_type, server_url):

    fhirhandler_data = FHIRHandler().load(
        TEST_DATA_DIR / f"fhir_example_{input_resource_type.lower()}.json",
        input_resource_type=input_resource_type,
        output_resource_type=output_resource_type,
        server_url=server_url,
    )

    with (
        TEST_DATA_DIR / f"fhir_example_{output_resource_type.lower()}.json"
    ).open("r") as f:
        json_data = json.load(f)

    assert fhirhandler_data == json_data


def test_convert_patient_record_entry_to_fhir():

    # TODO: NO ASSERTS, JUST TESTING NO VALIDATION ERROR RAISED

    fhir_handler = FHIRHandler()

    patient = PatientAgent(
        patient_id="patient-0",
        gender="male",
        birth_date="1956-07-26",
    )

    entry_id = "test-entry-0"
    record_entry = PatientRecordEntry(
        real_time="",
        patient_time="",
        environment_id=None,
        interactions=None,
        simulation_step=None,
        fhir_resource_time="",
        fhir_resource_type="",
        fhir_resource={},
        record_index=0,
        entry_id=entry_id,
        entry={},
        tag="test-entry",
    )

    # NOTE: all these keys and more can be in entry but they won't
    # all get used in every resource
    # TODO: write func to return keys used by resource, also which ones are
    # required
    entry = {
        "name": "some name",
        "code": "xxx",
        "start": string_to_datetime("2021-01-10 09:00:00"),
        "end": string_to_datetime("2021-01-10 09:15:00"),
        "reason": "some reason",
        "description": "some description",
        "dosage": "some dosage",
        "duration_value": 10,
        "duration_unit": "some duration_unit",
        "value": {
            "value": 6.3,
            "unit": "mmol/l",
            "system": "http://unitsofmeasure.org",
            "code": "mmol/L",
        },
    }
    record_entry.entry = entry

    supported_fhir_resources = get_supported_fhir_resources()

    for fhir_resource_type in supported_fhir_resources:

        record_entry.fhir_resource_type = fhir_resource_type

        resource = convert_patient_record_entry_to_fhir(
            record_entry, patient, environments=None
        )

        assert fhir_handler.validate(resource, fhir_resource_type)

    entries = []
    for fhir_resource_type in supported_fhir_resources:
        entry["resource_type"] = fhir_resource_type
        entry["name"] = f"some name in resource {fhir_resource_type}"
        entries.append(wrap_fhir_resource(entry, entry["start"]))

    patient._update_record(entries)

    environments = None

    resources = generate_patient_fhir_resources(
        patient,
        environments,
        validate=True,
        server_url=None,
    )

    bundle_path = TEST_DATA_DIR / f"patient_{patient.patient_id}_bundle.json"

    generate_patient_fhir_bundle(
        patient,
        environments,
        bundle_type="transaction",
        validate=True,
        server_url=None,
        save_path=bundle_path,
    )

    # TODO: patient_abm.data_handler.fhir.FHIRValidationError: Failed
    # to validate FHIR data using server operation at
    # http://hapi.fhir.org/baseR4/Bundle/$validate.
    # Status code returned: 400
    bundle = fhir_handler.load(
        bundle_path, "Bundle", server_url=None, validate=True
    )


def test_convert_fhir_to_patient_record_entry():
    # TODO
    pass
