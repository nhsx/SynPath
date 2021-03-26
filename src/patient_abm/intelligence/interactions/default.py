import datetime

from patient_abm.agent.environment import EnvironmentAgent
from patient_abm.agent.patient import PatientAgent
from patient_abm.utils import datetime_to_string


def death(
    patient: PatientAgent,
    environment: EnvironmentAgent,
    patient_time: datetime.datetime,
):
    """Interaction causing patient death. Sets patient attribute 'alive' to
    False and sets the 'end' field in the patient profile to patient_time
    timestamp

    Parameters
    ----------
    patient : PatientAgent
        Patient agent
    environment : EnvironmentAgent
        Environment agent (plays no part in death interaction but required
        for consistent interaction function signature)
    patient_time : datetime.datetime
        Current patient time

    Returns
    -------
    patient: PatientAgent
        Updated patient
    environment: EnvironmentAgent
        Environment (no update but required
        for consistent interaction function signature)
    update_data: dict
        Contains new patient record entries (redundant in this case)
    next_environment_id_to_prob: dict
        Dictionary mapping next environment IDs to probability (empty in this
        case)
    next_environment_id_to_time,
        Dictionary mapping next environment IDs to time delta (time to next
        environment) (empty in this case)
    """

    patient.record[0].entry["end"] = datetime_to_string(patient_time)
    patient.alive = False

    next_environment_id_to_prob = {}
    next_environment_id_to_time = {}

    update_data = {"new_patient_record_entries": []}
    return (
        patient,
        environment,
        update_data,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )
