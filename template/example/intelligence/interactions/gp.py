import datetime
import os
import sys


def measure_bmi(patient, environment, patient_time):

    # Could import outpatient_encounter function from general.py instead here
    encounter = {
        "resource_type": "Encounter",
        "name": "outpatient encounter",
        "start": patient_time,
    }

    bmi = {
        "resource_type": "Observation",
        "name": "Body mass index (BMI)",
        "start": encounter["start"] + datetime.timedelta(minutes=15),
        "value": {
            "value": 16.2,
            "unit": "kg/m2",
            "system": "http://unitsofmeasure.org",
            "code": "kg/m2",
        },
    }

    new_patient_record_entries = [encounter, bmi]

    next_environment_id_to_prob = {0: 0.5, 1: 0.5}

    next_environment_id_to_time = {
        0: datetime.timedelta(
            days=10
        ),  # TODO: from initial paient_time (not last)
        1: datetime.timedelta(days=20),
    }

    update_data = {"new_patient_record_entries": new_patient_record_entries}
    return (
        patient,
        environment,
        update_data,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )


def diagnose_fever(patient, environment, patient_time):
    entry = {
        "resource_type": "Condition",
        "name": "Fever",
        "code": "386661006",
        "start": patient_time,
    }

    new_patient_record_entries = [entry]
    next_environment_id_to_prob = {0: 0.2, 1: 0.8}

    next_environment_id_to_time = {
        0: datetime.timedelta(days=10),
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
