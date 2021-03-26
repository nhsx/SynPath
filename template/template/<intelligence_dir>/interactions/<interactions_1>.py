import datetime

from patient_abm.agent.environment import EnvironmentAgent
from patient_abm.agent.patient import PatientAgent


def an_interaction_1(
    patient: PatientAgent,
    environment: EnvironmentAgent,
    patient_time: datetime.datetime,
):
    """Interaction between patient and environment:

    - generates new Patient record entries;

    - decides which Environment the patient should visit next and at what time;

    - optionally applies custom updates the Patient and Environment agents.

    Parameters
    ----------
    patient : PatientAgent
        The patient agent
    environment : EnvironmentAgent
        The environment agent
    patient_time : datetime.datetime
        The time from the patient's persective

    Returns
    -------
    patient : PatientAgent
        Patient agent, possible updated
    environment : EnvironmentAgent
        The environment agent, possible updated
    patient_time : datetime.datetime
        The time from the patient's persective for the next interaction
    update_data : Dict[str, List[dict]]
        Dictionary containing new patient record entries as
        {"new_patient_record_entries": [entry_0, entry_1,...]},
        where each entry is itself a dictionary.
        These will get automatically added to the patient record.
        In future, update_data could contain other data too, which is why it is
        strucured in this way.
    next_environment_id_to_prob : Dict[Union[str, int], float]
        Dictionary contaning next environment_ids as keys and the proabiilties
        to transition to them
    next_environment_id_to_time : Dict[Union[str, int], datetime.timedelta]
        Dictionary contaning next environment_ids as keys and time period
        from initial patient_time to transition to them
    """

    # ADD CODE
    # Makes new patient record entries, decides next environment transition
    # probability and time. Can update patient and environment
    # Note that the intelligence layer, which receives the outputs of the
    # interaction functions, must be able to handle cases where
    # next_environment_id_to_prob and next_environment_id_to_time are empty
    # (these are the outputs of the default death interaction)

    return (
        patient,
        environment,
        update_data,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )
