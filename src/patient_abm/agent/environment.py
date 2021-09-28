import datetime
import inspect
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, List, Optional, Union

from patient_abm.agent.base import Agent
from patient_abm.agent.patient import PatientAgent
from patient_abm.data_handler.fhir import FHIRHandler


class EnvironmentAgent(Agent):
    """Class for environment agent"""

    # NOTE: in future, may want to add a log_state method to the
    # EnvironmentAgent, if, say, dynamics are implemented

    serialisable_attributes = [  #  TODO: change to serializable_attributes
        "environment_id",
        "environment_type",
        "name",
        "patient_present",
        "location",
        "organization",
        "practitioners",
        "interactions",
        "patient_data",
        "patient_interaction_history",
        "capacity",
        "wait_time",
        "id",
        "created_at",
        "kwargs",
    ]

    def __init__(
        self,
        environment_id: Union[str, int],
        environment_type: str = "",
        name: str = "",
        patient_present: bool = True,
        location: Optional[dict] = None,
        organization: Optional[dict] = None,
        practitioners: Optional[list] = None,
        interactions: Optional[List[str]] = None,
        patient_data: Optional[DefaultDict] = None,
        patient_interaction_history: Optional[DefaultDict] = None,
        capacity: Optional[List[dict]] = None,
        wait_time: Optional[List[dict]] = None,
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ):
        """Initialize Environment agent class. The inputs are all set as
        attributes

        Parameters
        ----------
        environment_id : Union[str, int]
            Unique ID for the environment.
        environment_type : str, optional
            String defining environment type, e.g. "surgery", by default "".
            Note this is called "type" in the config.json
        name : str, optional
            Name for the environment, by default ""
        patient_present : bool, optional
            Whether the patient is physically present when interacting with
            this environment, by default True
        location : Optional[dict], optional
            Location of the environment, by default None
        organization : Optional[dict], optional
            Organization of the environment, by default None
        practitioners : Optional[list], optional
            List containing practitioner(s) information,
            by default None
        interactions : Optional[List[str]], optional
            List of interaction names that the intelligence layer can
            apply to the patient when visiting this environment, by default
            None
        patient_data : Optional[DefaultDict], optional
            Store patient data like scans or letters, by default None
        patient_interaction_history : Optional[DefaultDict], optional
            Log of patient interactions, keyed by patient_id, by default None
        capacity : Optional[List[dict]], optional
            Capacity of environment over time, by default None
        wait_time : Optional[List[dict]], optional
            Wait time of the environment over time, by default None
        id_ : Optional[Union[str, int]], optional
            Unique ID, by default None. If not supplied, will be
            automatically set by uuid.uuid4().urn. The actual attribute
            name will be 'id' not 'id_'.
        created_at : Optional[Union[str, datetime.datetime]], optional
            Time agent is created, by default None. If not supplied, will be
            automatically set by datetime.datetime.now()
        kwargs : dict
            Keyword arguments set as attributes
        """

        super().__init__(id_=id_, created_at=created_at)

        self.environment_id = environment_id
        self.environment_type = environment_type
        self.name = name
        self.patient_present = patient_present
        self.location = location
        self.organization = organization
        self.practitioners = practitioners

        # TODO: Implement more robust / automated way to add default
        # interactions. Also a method to override them if required
        # TODO: each subclass env can have different default interactions
        # -> make into attribute?
        default_interactions = ["death"]
        interactions_to_add = [] if interactions is None else interactions
        self.interactions = sorted(
            set(default_interactions + interactions_to_add)
        )

        self.patient_data = (
            defaultdict(list) if patient_data is None else patient_data
        )
        self.patient_interaction_history = (
            defaultdict(list)
            if patient_interaction_history is None
            else patient_interaction_history
        )

        self.capacity = [] if capacity is None else capacity
        self.wait_time = [] if wait_time is None else wait_time

        # Store kwargs for serialization
        self.kwargs = kwargs

        for key, value in kwargs.items():
            if key not in inspect.getmembers(self):
                self.__setattr__(key, value)
            else:
                print(
                    f"WARNING: cannot set EnvironmentAgent attribute {key}, "
                    "there is already an attribute with this name."
                )

    def _update_patient_interaction_history(self, patient: PatientAgent):
        # TODO: If multiple record entries are written in a single
        # simulation step, decide whether to refer to all here
        # (can get this info by looking for all patient.record entries with
        # same simulation_step)
        self.patient_interaction_history[patient.patient_id].append(
            {
                "time": patient.record[-1].patient_time,
                "last_record_index": len(patient.record) - 1,
                "interactions": patient.record[-1].interactions,
            }
        )

    def _update_patient_data(
        self, patient: PatientAgent, patient_data: DefaultDict
    ):
        self.patient_data[patient.patient_id].extend(patient_data)

    def update(
        self, patient: PatientAgent, patient_data: Optional[DefaultDict] = None
    ):
        """Update environment:

        - log patient interaction in patient_interaction_history

        - update patient_data (if not None)

        Parameters
        ----------
        patient : PatientAgent
            Patient agent object
        patient_data : Optional[DefaultDict], optional
            New patient data like scans or letters, by default None
        """
        self._update_patient_interaction_history(patient)
        if patient_data is not None:
            self._update_patient_data(patient, patient_data)

    @classmethod
    def from_fhir(
        cls,
        fhir_paths: List[Union[Path, str]],
        resource_types: List[str],
        environment_id: Union[str, int],
        server_url: Optional[str] = None,
        **kwargs,
    ):
        """
        Load environment from FHIR Location, Organization, Practitioner
        resources.

        NOTE: this method has not been used very much, and could potentially
        be removed. We recommend further development if it is required.
        """
        # TODO: check for address consistency?
        # TODO: selectively choose information from input fhir_paths?
        # TODO: currently each resource type must have separate fhir_path file.
        # Leave like this or restructure? e.g. could be json = list of dicts
        if len(fhir_paths) != len(resource_types):
            raise ValueError(
                "The lengths of `fhir_paths` and `input_resource_types` "
                "do not match. There must be a resource type in "
                "`input_resource_types` for every path in `fhir_paths`."
            )

        if (
            len(
                set([s.lower() for s in resource_types])
                - {"location", "organization", "practitioner"}
            )
            > 0
        ):
            raise ValueError(
                "resource_types should only contain "
                "Location, Organization, Practitioner"
            )

        # TODO: may want to convert to a simpler internal representation of
        # "Location, Organization, Practitioner"

        fhir_inputs = defaultdict(list)
        for fhir_path, resource_type in zip(fhir_paths, resource_types):
            data = FHIRHandler().load(
                fhir_path,
                input_resource_type=resource_type,
                output_resource_type=resource_type,
                server_url=server_url,
            )
            if isinstance(data, list):
                raise TypeError(
                    "Expecting `fhir_path` to load as a dictionary. Instead "
                    "it is a list."
                )
            fhir_inputs[resource_type.lower()].append(data)

        # TODO: sort out possible name clash: could be because there is a
        # FHIR resource_type which is the same as the name of an attribute,
        # which might be appearing in kwargs, or gets set and overwrites wrong
        # thing

        return cls(
            environment_id=environment_id,
            **fhir_inputs,
            **kwargs,
        )


class AandEEnvironmentAgent(EnvironmentAgent):
    """
    Class for A&E environment agent.

    NOTE: a placeholder for future development. The current version is
    almost identical to parent EnvironmentAgent class
    """

    def __init__(
        self,
        environment_id: Union[str, int],
        environment_type: str = "a_and_e",
        name: str = "a_and_e",
        patient_present: bool = True,
        location: Optional[dict] = None,
        organization: Optional[dict] = None,
        practitioners: Optional[list] = None,
        interactions: Optional[list] = None,
        patient_data: Optional[DefaultDict] = None,
        patient_interaction_history: Optional[DefaultDict] = None,
        capacity: Optional[List[dict]] = [],
        wait_time: Optional[List[dict]] = [datetime.timedelta(days=3)],
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ):
        """Initialize AandEEnvironmentAgent agent class.

        Parameters
        ----------
        environment_id : Union[str, int]
            Unique ID for the environment.
        environment_type : str, optional
            String defining environment type, by default "a_and_e".
            Note this is called "type" in the config.json
        name : str, optional
            Name for the environment, by default "a_and_e"
        patient_present : bool, optional
            Whether the patient is physically present when interacting with
            this environment, by default True
        location : Optional[dict], optional
            Location of the environment, by default None
        organization : Optional[dict], optional
            Organization of the environment, by default None
        practitioners : Optional[list], optional
            List containing one or more practitioners at this environments,
            by default None
        interactions : Optional[List[str]], optional
            List of interaction names that the intelligence layer can
            apply to the patient when visiting this environment, by default
            None
        patient_data : Optional[DefaultDict], optional
            Store patient data like scans or letters, by default None
        patient_interaction_history : Optional[DefaultDict], optional
            Log of patient interactions, keyed by patient_id, by default None
        capacity : Optional[List[dict]], optional
            Capacity of environment over time, by default None
        wait_time : Optional[List[dict]], optional
            Wait time of the environment over time, by default None
        id_ : Optional[Union[str, int]], optional
            Unique ID, by default None. If not supplied, will be
            automatically set by uuid.uuid4().urn. The actual attribute
            name will be 'id' not 'id_'.
        created_at : Optional[Union[str, datetime.datetime]], optional
            Time agent is created, by default None. If not supplied, will be
            automatically set by datetime.datetime.now()
        kwargs : dict
            Keyword arguments, passed to parent EnvironmentAgent class and
            set as attributes
        """

        super().__init__(
            environment_id=environment_id,
            environment_type=environment_type,
            name=name,
            patient_present=patient_present,
            location=location,
            organization=organization,
            practitioners=practitioners,
            interactions=interactions,
            patient_data=patient_data,
            patient_interaction_history=patient_interaction_history,
            capacity=capacity,
            wait_time=wait_time,
            id_=id_,
            created_at=created_at,
            **kwargs,
        )


class GPEnvironmentAgent(EnvironmentAgent):
    """
    Class for GP environment agent.

    NOTE: a placeholder for future development. The current version is
    almost identical to parent EnvironmentAgent class
    """

    def __init__(
        self,
        environment_id: Union[str, int],
        environment_type: str = "gp",
        name: str = "gp",
        patient_present: bool = True,
        location: Optional[dict] = None,
        organization: Optional[dict] = None,
        practitioners: Optional[list] = None,
        interactions: Optional[list] = None,
        patient_data: Optional[DefaultDict] = None,
        patient_interaction_history: Optional[DefaultDict] = None,
        capacity: Optional[List[dict]] = [5],
        wait_time: Optional[List[dict]] = [datetime.timedelta(hours=4)],
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ):
       

        super().__init__(
            environment_id=environment_id,
            environment_type=environment_type,
            name=name,
            patient_present=patient_present,
            location=location,
            organization=organization,
            practitioners=practitioners,
            interactions=interactions,
            patient_data=patient_data,
            patient_interaction_history=patient_interaction_history,
            capacity=capacity,
            wait_time=wait_time,
            id_=id_,
            created_at=created_at,
            **kwargs,
        )
class COEnvironmentAgent(EnvironmentAgent):
    """
    Class for community environment agent.

    NOTE: a placeholder for future development. The current version is
    almost identical to parent EnvironmentAgent class
    """

    def __init__(
        self,
        environment_id: Union[str, int],
        environment_type: str = "community",
        name: str = "community",
        patient_present: bool = True,
        location: Optional[dict] = None,
        organization: Optional[dict] = None,
        practitioners: Optional[list] = None,
        interactions: Optional[list] = None,
        patient_data: Optional[DefaultDict] = None,
        patient_interaction_history: Optional[DefaultDict] = None,
        capacity: Optional[List[dict]] = [10],
        wait_time: Optional[List[dict]] = [datetime.timedelta(weeks=2)],
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ):

        super().__init__(
            environment_id=environment_id,
            environment_type=environment_type,
            name=name,
            patient_present=patient_present,
            location=location,
            organization=organization,
            practitioners=practitioners,
            interactions=interactions,
            patient_data=patient_data,
            patient_interaction_history=patient_interaction_history,
            capacity=capacity,
            wait_time=wait_time,
            id_=id_,
            created_at=created_at,
            **kwargs,
        )

class OPEnvironmentAgent(EnvironmentAgent):
    """
    Class for outpatient environment agent.

    NOTE: a placeholder for future development. The current version is
    almost identical to parent EnvironmentAgent class
    """

    def __init__(
        self,
        environment_id: Union[str, int],
        environment_type: str = "outpatient",
        name: str = "outpatient",
        patient_present: bool = True,
        location: Optional[dict] = None,
        organization: Optional[dict] = None,
        practitioners: Optional[list] = None,
        interactions: Optional[list] = None,
        patient_data: Optional[DefaultDict] = None,
        patient_interaction_history: Optional[DefaultDict] = None,
        capacity: Optional[List[dict]] = [10],
        wait_time: Optional[List[dict]] = [datetime.timedelta(weeks=4)],
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ):

        super().__init__(
            environment_id=environment_id,
            environment_type=environment_type,
            name=name,
            patient_present=patient_present,
            location=location,
            organization=organization,
            practitioners=practitioners,
            interactions=interactions,
            patient_data=patient_data,
            patient_interaction_history=patient_interaction_history,
            capacity=capacity,
            wait_time=wait_time,
            id_=id_,
            created_at=created_at,
            **kwargs,
        )

class IPEnvironmentAgent(EnvironmentAgent):
    """
    Class for inpatient environment agent.

    NOTE: a placeholder for future development. The current version is
    almost identical to parent EnvironmentAgent class
    """

    def __init__(
        self,
        environment_id: Union[str, int],
        environment_type: str = "inpatient",
        name: str = "inpatient",
        patient_present: bool = True,
        location: Optional[dict] = None,
        organization: Optional[dict] = None,
        practitioners: Optional[list] = None,
        interactions: Optional[list] = None,
        patient_data: Optional[DefaultDict] = None,
        patient_interaction_history: Optional[DefaultDict] = None,
        capacity: Optional[List[dict]] = [20],
        wait_time: Optional[List[dict]] = [datetime.timedelta(days=1)],
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ):
        
        super().__init__(
            environment_id=environment_id,
            environment_type=environment_type,
            name=name,
            patient_present=patient_present,
            location=location,
            organization=organization,
            practitioners=practitioners,
            interactions=interactions,
            patient_data=patient_data,
            patient_interaction_history=patient_interaction_history,
            capacity=capacity,
            wait_time=wait_time,
            id_=id_,
            created_at=created_at,
            **kwargs,
        )