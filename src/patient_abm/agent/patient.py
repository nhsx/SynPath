import copy
import datetime
import inspect
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, List, Optional, Set, TypeVar, Union

import pandas

from patient_abm.agent.base import Agent
from patient_abm.data_handler.fhir import (
    FHIRHandler,
    convert_fhir_to_patient_record_entry,
)
from patient_abm.utils import (
    datetime_to_string,
    make_uuid,
    print_log,
    string_to_datetime,
)

PatientAgentType = TypeVar("PatientAgentType", bound="PatientAgent")


# TODO: change name to wrap_entry
def wrap_fhir_resource(
    entry: dict,
    patient_time: Union[str, datetime.datetime],
    environment_id: Optional[Union[str, int]] = None,
    interactions: Optional[List[str]] = None,
    simulation_step: Optional[int] = None,
    tag: Optional[str] = None,
    raw_fhir_resource: Optional[dict] = None,
) -> dict:
    """Wraps a minimal record 'entry' into a dictionary that
    can be used in the PatientRecordEntry constructor.

    Parameters
    ----------
    entry : dict
        Entry to be wrapped, written in the internal patient record
        representation. Must at least have "name", "start" and "resource_type"
        keys. Please refer to the notebook 'patient-agent.ipynb' in the
        notebooks folder for an example.
    patient_time : Union[str, datetime.datetime]
        The timestamp in patient-time attached to the entry
    environment_id : Optional[Union[str, int]], optional
        If the entry was the result of interacting with an environment, this
        is the environment_id, by default None
    interactions : Optional[List[str]], optional
        If the entry was the result of interacting with an environment, this
        is the list of interactions that were used in that process,
        by default None
    simulation_step : Optional[int], optional
        If this entry was generated in a simulation, this is the simulation
        step that produced the entry (useful if, say, a simulation step
        generated multiple entries), by default None
    tag : Optional[str], optional
        A human-readable name for the the entry, by default None
    raw_fhir_resource : Optional[dict], optional
        Additional raw FHIR data that can be added to the entry when
        converting to FHIR, by default None

    Returns
    -------
    dict
        A wrapped entry
    """
    return {
        "patient_time": string_to_datetime(patient_time),
        "environment_id": environment_id,
        "interactions": interactions,
        "simulation_step": simulation_step,
        "fhir_resource_time": string_to_datetime(entry.get("start")),
        "fhir_resource_type": entry["resource_type"],
        "fhir_resource": copy.deepcopy(raw_fhir_resource),
        "entry": copy.deepcopy(entry),
        "tag": tag,
    }


@dataclass
class PatientRecordEntry:
    """The patient record 'entry' object. Forms an element of the PatientAgent
    record attribute.

    Parameters
    ----------
    entry : dict
        The actual content of the PatientRecordEntry. A FHIR-style resource
        written in the internal patient record representation.
        Must at least have "name", "start" and "resource_type"
        keys. Please refer to the notebook 'patient-agent.ipynb' in the
        notebooks folder for an example.
    real_time : datetime.datetime
        The real timestamp attached to the entry
    patient_time : datetime.datetime
        The timestamp in patient-time attached to the entry
    environment_id : Optional[Union[str, int]], optional
        If the entry was the result of interacting with an environment, this
        is the environment_id, by default None
    interactions : Optional[List[str]], optional
        If the entry was the result of interacting with an environment, this
        is the list of interactions that were used in that process,
        by default None
    simulation_step : Optional[int], optional
        If this entry was generated in a simulation, this is the simulation
        step that produced the entry (useful if, say, a simulation step
        generated multiple entries), by default None
    fhir_resource_time: Optional[Union[str, datetime.datetime]]
        The time of the entry (to be deprecated).
    fhir_resource_type: str
        The FHIR resource type of the entry
    fhir_resource : Optional[dict], optional
        Additional raw FHIR data that can be added to the entry when
        converting to FHIR, by default None
    record_index : int
        The index in the record list corresponding to this entry
    entry_id : str
        A unique ID for the entry
    tag : Optional[str], optional
        A human-readable name for the the entry, by default None
    """

    entry: dict
    real_time: Union[str, datetime.datetime]
    patient_time: Union[str, datetime.datetime]
    environment_id: Optional[Union[str, int]]
    interactions: Optional[List[str]]
    simulation_step: Optional[int]
    fhir_resource_time: Optional[Union[str, datetime.datetime]]  # TODO: remove
    fhir_resource_type: str
    fhir_resource: dict
    record_index: int
    entry_id: str
    tag: Optional[str]


class PatientAgent(Agent):
    """Class for patient agent"""

    serialisable_attributes = [  #  TODO: change to serializable_attributes
        "patient_id",
        "gender",
        "birth_date",
        "start_time",
        "name",
        "conditions",
        "medications",
        "actions",
        "conditions_custom_fields",
        "medications_custom_fields",
        "actions_custom_fields",
        "inpatient",
        "alive",
        "id",
        "created_at",
        "record",
        "kwargs",
        "profile",
    ]

    _core_dataframe_fields = [
        "name",
        "start",
        "real_start_time",
        "end",
        "real_end_time",
        "active",
        "count",
        "record_index",  #  TODO: Consider converting to list of record_indices
    ]

    _dataframe_attributes_to_kwargs = {
        "conditions": {
            "additional_core_fields": ["code"],
            "fhir_resource_types": {"Condition"},
        },
        "medications": {
            "additional_core_fields": ["code", "dosage", "frequency"],
            "fhir_resource_types": {"MedicationRequest"},
        },
        "actions": {
            "additional_core_fields": ["resource_type"],
            "fhir_resource_types": {"Appointment", "ServiceRequest"},
        },
    }

    def __init__(
        self,
        patient_id: Union[str, int],
        gender: str,
        birth_date: Union[str, datetime.datetime],
        start_time: Union[str, datetime.datetime] = None,
        name: Optional[str] = None,
        conditions: Optional[Union[pandas.DataFrame, List[dict]]] = None,
        medications: Optional[Union[pandas.DataFrame, List[dict]]] = None,
        actions: Optional[Union[pandas.DataFrame, List[dict]]] = None,
        conditions_custom_fields: List[str] = [],
        medications_custom_fields: List[str] = [],
        actions_custom_fields: List[str] = [],
        inpatient: Optional[dict] = None,
        alive: bool = True,
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        record: List[dict] = [],
        profile: Optional[dict] = None,
        **kwargs,
    ):
        """Initialize Patient agent class. The inputs are all set as
        attributes

        Parameters
        ----------
        patient_id : Union[str, int]
            Unique ID for the patient.
        gender : str
            Patient gender, either "male" or "female"
        start_time : Union[str, datetime.datetime], optional
            "Patient time" that patient starts pathway i.e. datetime from the
            patient's point of view, by default None. If no supplied, defaults
            to created_at
        name : Optional[str], optional
            Patient name, by default None. Defaults to patient_id if not
            supplied
        conditions : Optional[Union[pandas.DataFrame, List[dict]]], optional
            Patient conditions (problems or diseases), by default None.
            Internally represented as a pandas dataframe with the following
            columns: "name" (name of condition),
            "start" (start time in patient perspective),
            "real_start_time", "end" (end time in patient perspective),
            "real_end_time", "active" (whether condition is active, True if
            "end" is None, else False),
            "count" (number of times patient has had this conditions),
            "record_index" (the first index in patient record referring to
            this condition) and "code" (SNOMED code for condition).
            This variable can be used to initialise the patient with
            existing comorbidities. Whenever the patient is updated with new
            record entries, the conditions table is updated by any entry with
            fhir_resource_type Condition. A condition is active until a
            patient record entry appears
            with the same 'name' and 'start' fields also has a non-null
            'end' date. The table should have unique (name, start) pair index.
        medications : Optional[Union[pandas.DataFrame, List[dict]]], optional
            Patient outstanding actions, by default None.
            Internally represented as a pandas dataframe with the following
            columns: "name" (name of medication),
            "start" (start time in patient perspective),
            "real_start_time", "end" (end time in patient perspective),
            "real_end_time", "active" (whether medication is active, True if
            "end" is None, else False),
            "count" (number of times patient has taken this medication),
            "record_index" (the first index in patient record referring to
            this medication)  and "code" (SNOMED code for medication),
            "dosage", "frequency".
            Whenever the patient is updated with new
            record entries, the medications table is updated by any entry with
            fhir_resource_type MedicationRequest.
            A medication is active until a patient record entry appears
            with the same 'name' and 'start' fields also has a non-null
            'end' date. The table should have unique (name, start) pair index.
        actions : Optional[Union[pandas.DataFrame, List[dict]]], optional
            Patient actions that they might have outsanding,
            e.g. and upcoming appointment, by default None.
            Internally represented as a pandas dataframe with the following
            columns: "name" (name of action),
            "start" (start time in patient perspective),
            "real_start_time", "end" (end time in patient perspective),
            "real_end_time", "active" (whether action is active, True if
            "end" is None, else False),
            "count" (number of times patient has had this action),
            "record_index" (the first index in patient record referring to
            this action)  and "resource_type" (the FHIR resource type
            generating this action).
            Whenever the patient is updated with new
            record entries, the actions table is updated by any entry with
            fhir_resource_types "Appointment" and "ServiceRequest".
            An action is active until a patient record entry appears
            with the same 'name' and 'start' fields also has a non-null
            'end' date. The table should have unique (name, start) pair index.
        conditions_custom_fields : List[str], optional
            Additional custom fields to add to conditions table, e.g.
            ["severity"], by default []
        medications_custom_fields : List[str], optional
            Additional custom fields to add to medications table, e.g.
            ["side_effect_experienced"], by default []
        actions_custom_fields : List[str], optional
            Additional custom fields to add to actions table, e.g.
            ["delay"], by default []
        inpatient : Optional[dict], optional
            Information about inpatient status e.g. when started, where
            located, by default None
        alive : bool, optional
            Whether the patient is alive, by default True
        id_ : Optional[Union[str, int]], optional
            Unique ID, by default None. If not supplied, will be
            automatically set by uuid.uuid4().urn. The actual attribute
            name will be 'id' not 'id_'.
        created_at : Optional[Union[str, datetime.datetime]], optional
            Time agent is created, by default None. If not supplied, will be
            automatically set by datetime.datetime.now()
        record : List[dict], optional
            The patient record. Can start non-empty if patient has existing
            record. If existing record has e.g. Condition entry, then
            conditions table is populated, by default []
        profile : Optional[dict], optional
            Patient demographic profile. Essentially maps to FHIR Patient
            resource and becomes the first entry in the patient record,
            by default None
        kwargs : dict
            Keyword arguments, set as attributes. If key starts with prefix
            'patient__' it will also get added to the patient_profile
            (with prefix removed)
        """

        if gender not in {"male", "female"}:
            raise ValueError(
                f"Invalid value for gender '{gender}'. Must be either "
                "'male' or 'female'."
            )

        super().__init__(id_=id_, created_at=created_at)

        self.fhir_handler = FHIRHandler()

        self.patient_id = patient_id
        self.gender = gender
        self.birth_date = string_to_datetime(birth_date)
        self.start_time = (
            string_to_datetime(start_time)
            if start_time is not None
            else self.created_at
        )
        self.name = self.patient_id if name is None else name

        self.record = []
        if profile is not None:
            self.profile = PatientRecordEntry(**profile)
        elif (
            len(record) == 0
            or profile is None
            or record[0]["fhir_resource_type"] != "Patient"
        ):
            profile = {
                "resource_type": "Patient",
                "id": str(patient_id),
                "gender": gender,
                "birth_date": datetime_to_string(birth_date, "%Y-%m-%d"),
            }

            for key, value in kwargs.items():
                if key.startswith("patient__"):
                    profile[key.replace("patient__", "")] = value

            self.profile = PatientRecordEntry(
                real_time=self.created_at,
                patient_time=self.start_time,
                environment_id=-1,
                interactions=None,
                simulation_step=None,
                fhir_resource_time=None,
                fhir_resource_type="Patient",
                fhir_resource=None,
                record_index=0,
                # NOTE: entry_id is used lated for FHIR resource id, which
                # does not allow colons (hence use uuid hex and not urn)
                entry_id=make_uuid("hex"),
                entry=profile,
                tag="patient_profile",
            )

            self.record = [self.profile]

            if len(record) > 0:
                if record[0]["fhir_resource_type"] == "Patient":
                    record = record[1:]

        self.alive = alive
        self.inpatient = inpatient

        # Store kwargs for serialization
        self.kwargs = kwargs

        for key, value in kwargs.items():
            if key not in inspect.getmembers(self):
                self.__setattr__(key, value)
            else:
                print(
                    f"WARNING: cannot set PatientAgent attribute {key}, "
                    "there is already an attribute with this name."
                )

        self.conditions_custom_fields = conditions_custom_fields
        self.medications_custom_fields = medications_custom_fields
        self.actions_custom_fields = actions_custom_fields

        attrs_name_to_input = {
            "conditions": [] if conditions is None else conditions,
            "medications": [] if medications is None else medications,
            "actions": [] if actions is None else actions,
        }

        attrs_name_to_custom_fields = {
            "conditions": conditions_custom_fields,
            "medications": medications_custom_fields,
            "actions": actions_custom_fields,
        }

        for (
            attrs_name,
            attrs_kwargs,
        ) in self._dataframe_attributes_to_kwargs.items():

            self._initialize_dataframe_attributes(
                attrs_name,
                self.record,
                attrs_name_to_input[attrs_name],
                custom_fields=attrs_name_to_custom_fields[attrs_name],
                **attrs_kwargs,
            )

        self.update(record, skip_existing=False, logger=None, print_=False)

    def _initialize_dataframe_attributes(
        self,
        attrs_name: str,
        record: List[PatientRecordEntry],
        attrs_input: Union[List[dict], pandas.DataFrame],
        custom_fields: List[str],
        additional_core_fields: List[str],
        fhir_resource_types: Set[str],
    ):

        setattr(
            self,
            f"{attrs_name}_fhir_resource_types",
            fhir_resource_types,
        )

        if isinstance(attrs_input, pandas.DataFrame):
            setattr(
                self,
                attrs_name,
                attrs_input,
            )
        elif isinstance(attrs_input, list) and len(attrs_input) == 0:
            fields = (
                self._core_dataframe_fields
                + additional_core_fields
                + custom_fields
            )
            setattr(
                self,
                attrs_name,
                pandas.DataFrame(attrs_input, columns=fields),
            )
        else:
            setattr(
                self,
                attrs_name,
                pandas.DataFrame(attrs_input),
            )

        df = getattr(self, attrs_name)
        for col in custom_fields + additional_core_fields:
            if col not in df.columns:
                df[col] = None

        missing_core_columns = set(self._core_dataframe_fields) - set(
            df.columns
        )
        if len(missing_core_columns) > 0:
            print(
                f"WARNING: Columns {missing_core_columns} are missing from "
                f"patient {attrs_name}. Appending"
            )

            for col in missing_core_columns:
                df[col] = None

        df["start"] = pandas.to_datetime(df["start"], errors="raise", utc=True)

        for col in getattr(self, attrs_name).columns:
            if attrs_name.endswith("_time") or attrs_name in ["end"]:
                df[col] = pandas.to_datetime(
                    df[col], errors="ignore", utc=True
                )

        df["active"] = df["active"].astype("bool")

        df.loc[df[df["count"].isnull()].index, "count"] = 1
        df.loc[df[df["record_index"].isnull()].index, "record_index"] = -1

        df["count"] = df["count"].astype("int")
        df["record_index"] = df["record_index"].astype("int")

        if len(df) > 0:

            df = df.reset_index(drop=True)

            df.loc[
                df[df["real_start_time"].isnull()].index, "real_start_time"
            ] = self.created_at
            df.loc[df[df["end"].isnull()].index, "active"] = True
            df.loc[df[df["end"].notnull()].index, "active"] = False

            for col in ["name", "start"]:
                try:
                    assert df[col].isnull().sum() == 0
                except AssertionError:
                    raise AssertionError(
                        f"Patient {attrs_name} table cannot have null values "
                        f"in column '{col}'."
                    )

            try:
                assert len(df) == len(df[["name", "start"]].drop_duplicates())
            except AssertionError:
                raise AssertionError(
                    f"Patient {attrs_name} table must have unique "
                    "('name', 'start') column pair values."
                )

            df = df.sort_values(["name", "start"])

            count = (
                df.groupby(["name", "start"])[["count"]]
                .apply(lambda x: list(range(1, len(x) + 1)))
                .explode()
                .tolist()
            )

            if (
                len(df["count"].isnull()) == 0
                and df["count"].tolist() != count
            ):
                print(
                    f"WARNING: patient {attrs_name} 'count' does not equal "
                    "calculated value. Replacing"
                )
            df["count"] = count

        setattr(self, attrs_name, df)

        self._update_dataframe_attributes(attrs_name, record, df)

    def _update_dataframe_attributes(
        self,
        attrs_name: str,
        record: List[PatientRecordEntry],
        df: pandas.DataFrame,
    ):

        for entry in record:

            if entry.fhir_resource_type in getattr(
                self, f"{attrs_name}_fhir_resource_types"
            ):

                name = entry.entry["name"]
                start = string_to_datetime(entry.entry["start"])

                count = len(df[df["name"] == name])

                df_name_start = df[
                    (df["name"] == name) & (df["start"] == start)
                ]

                if len(df_name_start) >= 1:

                    if len(df_name_start) > 1:
                        # TODO: suggest handling this in a better
                        # way in future, it is a little crude at the moment
                        print(
                            "WARNING: there is more than one row "
                            f"in the patient {attrs_name} table "
                            f"with name = {name} and "
                            f"start_date = {start}. "
                            "Removing duplicate rows."
                        )
                        df = df.reset_index(drop=True)
                        df_name_start_inds = df[
                            (df["name"] == name) & (df["start"] == start)
                        ].index
                        df = df.drop(index=df_name_start_inds[:-1])
                        df = df.reset_index(drop=True)
                        df_name_start = df[
                            (df["name"] == name) & (df["start"] == start)
                        ]

                    df.loc[df_name_start.index, "end"] = string_to_datetime(
                        entry.entry.get("end")
                    )

                    df.loc[df_name_start.index, "real_end_time"] = (
                        None
                        if entry.entry.get("end") is None
                        else string_to_datetime(entry.real_time)
                    )

                    df.loc[df_name_start.index, "active"] = (
                        entry.entry.get("end") is None
                    )

                    for col in df.columns:
                        if col in [
                            "name",
                            "start",
                            "end",
                            "real_end_time",
                            "real_start_time",
                            "active",
                            "record_index",
                            "count",
                        ]:
                            continue
                        df.loc[df_name_start.index, col] = entry.entry.get(col)

                elif len(df) == 0 or len(df_name_start) == 0:

                    new_row = {
                        "name": entry.entry["name"],
                        "start": string_to_datetime(entry.entry["start"]),
                        "real_start_time": string_to_datetime(entry.real_time),
                        "end": string_to_datetime(entry.entry.get("end")),
                        "real_end_time": (
                            None
                            if string_to_datetime(entry.entry.get("end"))
                            is None
                            else string_to_datetime(entry.real_time)
                        ),
                        "record_index": entry.record_index,
                        "count": count + 1,
                        "active": entry.entry.get("end") is None,
                    }
                    for col in df.columns:
                        if col in self._core_dataframe_fields:
                            continue
                        if col in entry.entry:
                            new_row[col] = entry.entry[col]
                        else:
                            new_row[col] = None

                    df = pandas.concat(
                        [df, pandas.DataFrame([new_row])]
                    ).reset_index(drop=True)

        setattr(self, attrs_name, df)

    def _sort_record(self, by: str = "record_index"):
        profile = self.record[0]
        _record = [(getattr(e, by), e) for e in self.record[1:]]
        _, sorted_record = list(zip(*sorted(_record, key=lambda x: x[0])))
        self.record = [profile] + sorted_record

    def _validate_entry(
        self,
        entry: dict,
        skip_existing: bool = False,
        logger: logging.Logger = None,
        print_: bool = False,
    ) -> str:

        skip_msg = "Adding."
        if skip_existing:
            skip_msg = "Skipping"

        existing_patient_entries = []
        for e in self.record:
            if e.entry not in existing_patient_entries:
                existing_patient_entries.append(e.entry)

        if entry["entry"] in existing_patient_entries:
            print_log(
                f"WARNING: {entry['entry']} is already in the patient "
                f"record. {skip_msg}",
                print_=True,
                logger=logger,
            )

            return "duplicate_patient_entry"

        existing_patient_times = [e.patient_time for e in self.record]

        if entry["patient_time"] < existing_patient_times[-1]:
            print_log(
                f"WARNING: {entry['entry']} has a patient_time that is "
                f"earlier than the last entry in the patient_record.",
                print_=False,
                logger=logger,
            )
            return "early_patient_time"

        if entry["fhir_resource_type"] == "Bundle":
            raise ValueError("Cannot update patient record with a FHIR Bundle")

    def _update_record(
        self,
        record: List[dict],
        skip_existing: bool = False,
        logger: logging.Logger = None,
        print_: bool = False,
        wrapped: bool = True,
    ) -> None:

        for entry in record:

            if not wrapped:
                entry = wrap_fhir_resource(
                    entry,
                    patient_time=entry["start"]
                    if entry.get("end") is None
                    else entry["end"],
                )

            len_record = len(self.record)

            if len_record > 0:
                validation = self._validate_entry(
                    entry,
                    skip_existing,
                    logger,
                    print_,
                )

                if validation == "duplicate_patient_entry" and skip_existing:
                    continue

            self.record.append(
                PatientRecordEntry(
                    real_time=string_to_datetime(
                        entry.get("real_time", datetime.datetime.now(self.tz))
                    ),
                    patient_time=string_to_datetime(entry["patient_time"]),
                    environment_id=entry.get("environment_id"),
                    interactions=entry.get("interactions"),
                    simulation_step=entry.get("simulation_step"),
                    fhir_resource_time=string_to_datetime(
                        entry.get("fhir_resource_time")
                    ),
                    fhir_resource_type=entry["fhir_resource_type"],
                    fhir_resource=entry.get("fhir_resource"),
                    record_index=entry.get("record_index", len_record),
                    entry_id=entry.get("entry_id", make_uuid("hex")),
                    entry=entry["entry"],
                    tag=entry.get("tag"),
                )
            )

    def update(
        self,
        record: List[dict],
        skip_existing: bool = False,
        logger: logging.Logger = None,
        print_: bool = False,
        wrapped: bool = True,
    ) -> None:
        """Update patient record by appending new 'record' entries and perform
        validation (deduplication and time order checking) and
        subsequently updating conditions, medications and actions numbers.

        The record contains 'entries' which each get converted into
        PatientRecordEntry objects. To facilitate this, they may need to be
        wrapped by wrap_fhir_resource. An unwrapped entry (or equivalently,
        the 'entry' field of a wrapped entry)
        must at least have the following fields: "name", "start" and
        "resource_type". Please refer to the notebook 'patient-agent.ipynb'
        in the notebooks folder for an example.

        Parameters
        ----------
        record : List[dict]
            The new list of entries to append to existing patient record
        skip_existing : bool, optional
            Whether to skip the addition of new record entries if they are
            already present in the existing patient record (deduplication),
            by default False
        logger : logging.Logger, optional
            Logger to write validation messages to, by default None
        print_ : bool, optional
            Whether to also print validation messages, by default False
        wrapped : bool, optional
            Whether each entry in record should be wrapped using
            wrap_fhir_resource
        """

        self._update_record(record, skip_existing, logger, print_, wrapped)

        for attrs_name in self._dataframe_attributes_to_kwargs:
            self._update_dataframe_attributes(
                attrs_name, self.record, getattr(self, attrs_name)
            )

    def log_state(
        self,
        logger: logging.Logger = None,
        log_last_n_record_entries: int = 0,
        print_only: bool = False,
    ) -> None:
        """Log patient state

        Parameters
        ----------
        logger : [type], optional
            Logger to log state to, by default None
        log_last_n_record_entries : int, optional
            Number of last record entries to log, by default 0
        print_only : bool, optional
            Whether to only print state instead of log, by default False
        """

        if logger is None:
            logger = logging.getLogger("patient_logger")

        last_record_entry = self.record[-1]

        # TODO: may want to convert patient times to nicer format if
        # e.g. days, years etc
        patient_time_elapsed = last_record_entry.patient_time - self.start_time

        state = {
            "agent_id": self.id,
            "agent_created_at": self.created_at,
            "time_elapsed": datetime.datetime.now(self.tz) - self.created_at,
            "patient_id": self.patient_id,
            "start_time": self.start_time,
            "patient_time_elapsed": patient_time_elapsed,
            "last_record_real_time": last_record_entry.real_time,
            "last_record_fhir_resource_type": (
                last_record_entry.fhir_resource_type
            ),
            "number_of_record_entries": len(self.record),
        }

        log_data = []
        if log_last_n_record_entries != 0:
            if log_last_n_record_entries == -1:
                last_n_record_entries = self.record
            else:
                last_n_record_entries = self.record[
                    -log_last_n_record_entries:
                ]

            for entry in last_n_record_entries:
                log_data.append(
                    {
                        "patient_state": state,
                        "patient_record_entry": asdict(entry),
                    }
                )
        else:
            log_data = [{"patient_state": state}]

        if print_only:
            print(log_data)
        else:
            for item in log_data:
                logger.info(item)

    def _prepare_for_save(self, attr_name: str) -> Any:

        attr = getattr(self, attr_name)
        if attr_name == "profile":
            return asdict(attr)
        elif attr_name == "record":
            return [asdict(item) for item in attr]
        elif attr_name in list(self._dataframe_attributes_to_kwargs):
            return attr.to_dict("records")
        else:
            return attr

    @classmethod
    def from_fhir(
        cls,
        fhir_data: Union[dict, str, Path],
        resource_type: str = "Bundle",
        patient_id: Optional[Union[int, str]] = None,
        start_time: Optional[Union[str, datetime.datetime]] = None,
        **kwargs,
    ) -> PatientAgentType:
        """Load patient from FHIR resource data.
        The data can either be a Patient resource, or a Bundle resource
        containing a Patient resource. The Patient resource is used to
        populate the patient profile, and (if Bundle) any other resources
        form populate the patient record.

        Parameters
        ----------
        fhir_data : Union[dict, str, Path]
            A dictionary contaning FHIR data, or a path to FHIR data
        resource_type : str, optional
            The resource type of the FHIR data, by default "Bundle"
        patient_id : Optional[Union[int, str]], optional
            Patient ID, if not set then is taken from the
            FHIR data Patient resource, by default None
        start_time : Optional[str, datetime.datetime], optional
            Start time in patient perspective, automatically set to
            datetime.datetime.now() if not supplied, by default None

        Returns
        -------
        PatientAgent
            An instance of the PatientAgent class loaded from fhir_data.

        Raises
        ------
        ValueError
            If more than one Patient resource is detected in fhir_data
        KeyError
            If any key in input kwargs has prefix patient__. This is not
            allowed here as all patient resource data should be contained in
            fhir_data
        ValueError
            If a non-None patient_id is passed as an argument, then a
            consistency check is made against the patient resource 'id' field
            in fhir_data. An error is raised if there is a mismatch
        """
        if start_time is None:
            start_time = datetime.datetime.now(datetime.timezone.utc)
            created_at = start_time
        else:
            created_at = None

        if isinstance(fhir_data, str) or isinstance(fhir_data, Path):
            data = FHIRHandler().load(
                fhir_data,
                input_resource_type=resource_type,
                output_resource_type=resource_type,
            )
        else:
            data = fhir_data

        if isinstance(data, dict):
            if resource_type == "Bundle":
                data = [item["resource"] for item in data["entry"]]
            else:
                data = [data]

        try:
            [patient_resource] = [
                item for item in data if item["resourceType"] == "Patient"
            ]
        except ValueError:
            raise ValueError("There must be one patient resource")

        record_unwrapped = [
            convert_fhir_to_patient_record_entry(
                item,
            )
            for item in data
            if item["resourceType"] != "Patient"
        ]

        record = [
            wrap_fhir_resource(
                item,
                patient_time=item["start"]
                if item.get("end") is None
                else item["end"],
            )
            for item in record_unwrapped
        ]

        patient_kwargs = {
            f"patient__{key}": value
            for key, value in patient_resource.items()
            if key not in ["resourceType", "id", "gender", "birthDate"]
        }
        for key in kwargs:
            if key.startswith("patient__"):
                raise KeyError(
                    "The keys of the kwargs supplied to the `from_fhir` "
                    "method should not start with 'patient_'. This prefix is "
                    "reserved for FHIR patient resource field names. "
                    "If you want to add a field to the FHIR patient resource, "
                    "then this must be included in `fhir_path`. Other "
                    "PatientAgent attributes may be added through `kwargs`, "
                    "but their attribute names cannot start with 'patient_'."
                )

        kwargs = {**patient_kwargs, **kwargs}

        if patient_id is not None:
            if patient_id != patient_resource["id"]:
                raise ValueError(
                    f"patient_id={patient_id} does not match value"
                    f"{patient_resource['id']} from the input FHIR data."
                )

        return cls(
            patient_id=(
                patient_resource["id"] if patient_id is None else patient_id
            ),
            gender=patient_resource["gender"],
            birth_date=patient_resource["birthDate"],
            record=record,
            start_time=start_time,
            created_at=created_at,
            **kwargs,
        )
