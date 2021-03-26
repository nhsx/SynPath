import datetime


def outpatient_encounter(patient, environment, patient_time):

    # NOTE: entries produced by the interaction functions must have 'name',
    # 'start' and 'resource_type' fields, and only the following
    # resource_types are supported for conversion to FHIR
    #   - Patient
    #   - Encounter
    #   - Condition
    #   - Observation
    #   - Procedure
    #   - MedicationRequest
    #   - ServiceRequest
    #   - Appointment
    # See the patient_abm.data_handler.fhir module for the code that implements
    # the conversion (e.g. the convert_patient_record_entry_to_fhir function)

    entry = {
        "resource_type": "Encounter",
        "name": "outpatient encounter",
        "start": patient_time,
    }

    new_patient_record_entries = [entry]

    next_environment_id_to_prob = {0: 0.9, 1: 0.1}

    next_environment_id_to_time = {
        0: datetime.timedelta(days=14),
        1: datetime.timedelta(days=2),
    }

    update_data = {"new_patient_record_entries": new_patient_record_entries}
    return (
        patient,
        environment,
        update_data,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )


def inpatient_encounter(patient, environment, patient_time):
    entry = {
        "resource_type": "Encounter",
        "name": "inpatient encounter",
        "start": patient_time,
    }

    new_patient_record_entries = [entry]

    next_environment_id_to_prob = {0: 0.9, 1: 0.1}

    next_environment_id_to_time = {
        0: datetime.timedelta(days=14),
        1: datetime.timedelta(days=2),
    }

    update_data = {"new_patient_record_entries": new_patient_record_entries}
    return (
        patient,
        environment,
        update_data,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )
