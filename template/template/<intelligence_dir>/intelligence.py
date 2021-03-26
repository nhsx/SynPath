import datetime
from typing import Callable, Dict

from patient_abm.agent.environment import EnvironmentAgent
from patient_abm.agent.patient import PatientAgent


def intelligence(
    patient: PatientAgent,
    environment: EnvironmentAgent,
    patient_time: datetime.datetime,
    interaction_mapper: Dict[str, Callable],
):
    """Intelligence layer - decides which interaction(s) to apply to patient
    and environment.

    Parameters
    ----------
    patient : PatientAgent
        The patient agent
    environment : EnvironmentAgent
        The environment agent
    patient_time : datetime.datetime
        The time from the patient's persective
    interaction_mapper : Dict[str, Callable]
        Dictionary mapping interaction names to corresponding function
        handles

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
    next_environment_id : Union[int, str]
        environment_id of the next environment the patient should visit,
        sampled from next_environment_id_to_prob
    interaction_name : List[str]
        Name of the interactions that were applied here.
    next_environment_id_to_prob : Dict[Union[str, int], float]
        Dictionary contaning next environment_ids as keys and the proabiilties
        to transition to them
    next_environment_id_to_time : Dict[Union[str, int], datetime.timedelta]
        Dictionary contaning next environment_ids as keys and time period
        from initial patient_time to transition to them
    """

    # ADD CODE
    # < some logic that decides which
    # interaction function to apply to the patient and environment,
    # and samples from next_environment_id_to_prob >

    return (
        patient,
        environment,
        patient_time,
        update_data,
        next_environment_id,
        interaction_names,
        next_environment_id_to_prob,
        next_environment_id_to_time,
    )
