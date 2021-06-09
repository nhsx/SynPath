import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, List, Optional, Union

import fhir.resources
import pydantic
import requests

from patient_abm.data_handler._fhir_resources import *  # noqa
from patient_abm.data_handler.base import DataHandler
from patient_abm.utils import datetime_to_string

# NOTE: we recommend implementing a custom FHIR validation server
# The reason that there are two servers is because mid-way the HAPI FHIR
# server stopped working - see the comment in the
# tests/data_handler/test_fhir.py test_load_resources function
HAPI_FHIR_SERVER_4 = "http://hapi.fhir.org/baseR4"
PYRO_FHIR_SERVER_4 = "https://r4.test.pyrohealth.net/fhir"


class FHIRValidationError(Exception):
    pass


class FHIRHandler(DataHandler):
    """
    Class for handling FHIR data
    """

    logger = logging.getLogger("FHIRHandler")

    def get_fhir_resources_parser(self, resource_type: str) -> Any:
        """Gets `fhir.resources` validator class corresponding to
        `resource_type`

        Parameters
        ----------
        resource_type : str
            Name of the resource type (case-sensitive)

        Returns
        -------
        Any
            Class for validating resource_type
        """

        lib = getattr(fhir.resources, resource_type.lower())
        return getattr(lib, resource_type)

    def validate(
        self,
        data: dict,
        resource_type: str = None,
        server_url: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Validate FHIR data. If `server_url` is not None, it will attempt to
        validate using operation at '{server_url}/{resource_type}/$validate'.
        If server is not available and is returning a 404 or 504 status code,
        validation will fall back to offline using the `fhir.resources`
        library (which is the method used if `server_url` is None.)

        Parameters
        ----------
        data : dict
            Data to be validated
        resource_type : str, optional
            Name of the resource type (case-sensitive). If not supplied,
            attempts to find the resource type from data["resourceType"]
            by default None
        server_url : Optional[str], optional
            For online validation, a server URL, by default None
        kwargs: dict
            Keyword arguments for the online validation method - gets
            passed to the python requests.post function. For example,
            if want to pass custom headers with the request.

        Returns
        -------
        bool
            True if validation successful

        Raises
        ------
        FHIRValidationError
            If fails online and / or offline validation methods
        """

        if resource_type is None:
            resource_type = data["resourceType"]

        if server_url is not None:

            url = f"{server_url}/{resource_type}/$validate"
            r = requests.post(url, json=data, **kwargs)

            if r.status_code == 200:
                return True
            elif r.status_code not in [404, 504]:
                # TODO: add any other codes which indicate a server error as
                # opposed to validation error
                raise FHIRValidationError(
                    "Failed to validate FHIR data using server operation at "
                    f"{url}. Status code returned: {r.status_code}. Message "
                    f"returned:\n{r.text}"
                )

            self.logger.warning(
                f"Could not reach FHIR server operation at {url} to validate "
                "FHIR data. Will attempt to validate using `fhir.resources` "
                "library."
            )

        try:
            self.get_fhir_resources_parser(resource_type).validate(data)
        except pydantic.ValidationError as e:
            raise FHIRValidationError(
                "Failed to validate FHIR data using `fhir.resources` "
                f"library.\n\n{e}"
            )

        return True

    def load(
        self,
        path: Union[Path, str],
        input_resource_type: str,
        output_resource_type: str = None,
        xml_schema_dir: Optional[Union[Path, str]] = None,
        server_url: str = HAPI_FHIR_SERVER_4,
        validate: bool = True,
        **kwargs,
    ) -> Union[list, dict]:
        """Load and validate FHIR data with specific input_resource_type.
        If output_resource_type is different to input_resource_type, then
        attempt to filter input_resource_type to output_resource_type and
        return that.

        Parameters
        ----------
        path : Union[Path, str]
            Path containing FHIR data. Must be either XML or JSON
        input_resource_type : str
            Resource type of the input data in path
        output_resource_type : str
            If input_resource_type is Bundle, the output resource type could
            be one of the resources contained in the Bundle, this allows
            filtering for that resource type. If None, the input is returned
        xml_schema_dir : Optional[Union[Path, str]], optional
            If data is XML, this is path to .xsd schema, by default None
        server_url : Optional[str], optional
            For online validation, a server URL, by default HAPI_FHIR_SERVER_4
            which is http://hapi.fhir.org/baseR4
        validate : bool, optional
            Whether to validate the input, by default True
        kwargs: dict
            Keyword arguments for the online validation method - gets
            passed to the python requests.post function. For example,
            if want to pass custom headers with the request.

        Returns
        -------
        Union[list, dict]
            Returns a FHIR resource type as a dicstionary, or if several FHIR
            resources of type output_resource_type were found in an input
            bundle, then all those are returned as a list.

        Raises
        ------
        FHIRValidationError
            Raised if validation fails
        ValueError
            If path is not XML or JSON
        ValueError
            If no resource of type output_resource_type is found in input
            bundle
        """

        if path.suffix == ".json":

            data = self.load_json(path)

        elif path.suffix == ".xml":

            # TODO: Improve XML handling. Currently it's quite inefficient
            # for two reasons:
            # (1) To convert XML string to dict, we use `xmlschema` which
            # validates data in `path` against the XML schema .xsd file.
            # Loading this schema takes some time.
            # (2) Effectively XML is getting validated twice, once in (1) and
            # then again by the `fhir.resources` parser which converts from
            # dict to a class

            import xmlschema

            xml_schema_dir = self.convert_path(xml_schema_dir)
            xml_schema_path = (
                xml_schema_dir / f"{input_resource_type.lower()}.xsd"
            )
            xml_schema = xmlschema.XMLSchema(xml_schema_path)
            try:
                data = xml_schema.to_dict(path)
            except xmlschema.validators.exceptions.XMLSchemaValidationError as e:  # noqa
                raise FHIRValidationError(
                    f"Failed to validate FHIR XML data located at {path} "
                    f"using schema {xml_schema_path}.\n\n{e}"
                )

        else:

            raise ValueError(
                f"`path` is an unsupported FHIR file type '{path.suffix}'. "
                "Must be either '.json' or '.xml'"
            )

        if validate:
            self.validate(data, input_resource_type, server_url, **kwargs)

        if (output_resource_type is None) or (
            output_resource_type == input_resource_type
        ):
            return data
        else:
            filtered_data = [
                item["resource"]
                for item in data["entry"]
                if item["resource"]["resourceType"].lower()
                == output_resource_type.lower()
            ]
            if len(filtered_data) == 0:
                raise ValueError(
                    f"No FHIR resource {output_resource_type} in {path}."
                )
            elif len(filtered_data) > 1:
                if output_resource_type.lower() == "patient":
                    raise FHIRValidationError(
                        "FHIR data contains more than one patient resource."
                    )
                return filtered_data
            else:
                return filtered_data[0]

    def save(
        self,
        path: Union[Path, str],
        data: dict,
        resource_type: str = None,
        validate: bool = True,
        server_url: str = HAPI_FHIR_SERVER_4,
        **kwargs,
    ) -> None:
        """Validate and save FHIR data as JSON file

        Parameters
        ----------
        path : Union[Path, str]
            Path in which to save FHIR data as JSON
        data : dict
            Data to save
        resource_type : str, optional
            Name of the resource type (case-sensitive). If not supplied,
            attempts to find the resource type from data["resourceType"]
            by default None
        validate : bool, optional
            Whether to validate data before saving, by default True
        server_url : Optional[str], optional
            For online validation, a server URL, by default HAPI_FHIR_SERVER_4
        kwargs: dict
            Keyword arguments for the online validation method - gets
            passed to the python requests.post function. For example,
            if want to pass custom headers with the request.
        """

        # TODO: add XML to save?
        if validate:
            self.validate(data, resource_type, server_url, **kwargs)

        self.save_json(path, data)


def create_fhir_bundle(
    resources: List[dict], bundle_type: str = "transaction"
) -> dict:
    """Creates a FHIR bundle from a list of FHIR resources

    Parameters
    ----------
    resources : List[dict]
        List of FHIR resources
    bundle_type : str, optional
        FHIR Bundle type
        https://www.hl7.org/fhir/bundle-definitions.html#Bundle.type,
        by default "transaction"

    Returns
    -------
    dict
        FHIR Bundle
    """

    return {
        "resourceType": "Bundle",
        "type": bundle_type,
        "entry": [
            {
                "resource": resource,
                "request": {"method": "POST", "url": resource["resourceType"]},
            }
            for resource in resources
        ],
    }


def get_fhir_to_patient_record_entry_map():
    """Returns a map that can convert FHIR resource to patient record entry.
    The map is a dictionary where the keys are a tuple:
    (k_0, k_1, ...)
    and each entry k_i is itself a key in a FHIR resource, that is to be
    applied sequentially to get to the relevant value.

    The values of the map are the names of the patient record entry keys
    that the FHIR resource at (k_0, k_1, ...) maps to.

    Currently the map is only available for certain fields of the following
    FHIR resource types:

      - Patient
      - Encounter
      - Condition
      - Observation
      - Procedure
      - MedicationRequest
      - ServiceRequest
      - Appointment

    Returns
    -------
    dict
        A map from FHIR a field to patient record entry field

    Raises
    ------
    AssertionError
        If the key in the map is not a tuple
    AssertionError
        If the value in the map is not a string
    """

    map_ = {
        "Patient": {
            ("birthDate",): "birth_date",
            ("gender",): "gender",
            ("id",): "patient_id",
        },
        "Encounter": {
            ("class", "display"): "name",
            ("class", "code"): "code",
            ("period", "start"): "start",
            ("period", "end"): "end",
        },
        "Condition": {
            ("code", "coding", 0, "display"): "name",
            ("code", "coding", 0, "code"): "code",
            ("recordedDate",): "start",
            ("abatementDateTime",): "end",
        },
        "Observation": {
            ("code", "coding", 0, "display"): "name",
            ("code", "coding", 0, "code"): "code",
            ("valueQuantity",): "value",  # TODO: a dict
            ("effectivePeriod", "start"): "start",
            ("effectivePeriod", "end"): "end",
        },
        "Procedure": {
            ("code", "coding", 0, "display"): "name",
            ("code", "coding", 0, "code"): "code",
            ("performedPeriod", "start"): "start",
            ("performedPeriod", "end"): "end",
        },
        # NOTE: currently no end in MedicationRequest, calculate from start
        # and duration?
        "MedicationRequest": {
            ("contained", 0, "code", "coding", 0, "display"): "name",
            ("contained", 0, "code", "coding", 0, "code"): "code",
            ("reasonCode", 0, "coding", 0, "display"): "reason",
            ("dispenseRequest", "validityPeriod", "start"): "start",
            ("dosageInstruction", 0, "text"): "dosage",
            (
                "dispenseRequest",
                "expectedSupplyDuration",
                "value",
            ): "duration_value",
            (
                "dispenseRequest",
                "expectedSupplyDuration",
                "unit",
            ): "duration_unit",
        },
        "ServiceRequest": {
            ("code", "coding", 0, "display"): "name",
            ("code", "coding", 0, "code"): "code",
            ("reasonCode", 0, "text"): "reason",
            (
                "occurrenceDateTime",
            ): "start",  # NOTE: may want occurrencePeriod
        },
        "Appointment": {
            ("serviceCategory", 0, "coding", 0, "display"): "name",
            ("serviceCategory", 0, "coding", 0, "code"): "code",
            ("reasonReference", 0, "display"): "reason",
            ("description",): "description",
            ("start",): "start",
            ("end",): "end",
        },
    }

    for resource_type, map_resource_type in map_.items():
        for fhir_key, entry_key in map_resource_type.items():
            try:
                assert isinstance(fhir_key, tuple)
            except AssertionError:
                raise AssertionError(
                    f"Incorrect type in get_fhir_to_patient_record_entry_map "
                    f"map fhir_key for resource_type {resource_type}: "
                    f"{fhir_key} should be a tuple."
                )
            try:
                assert isinstance(entry_key, str)
            except AssertionError:
                raise AssertionError(
                    f"Incorrect type in get_fhir_to_patient_record_entry_map "
                    f"map entry_key for resource_type {resource_type}: "
                    f"{entry_key} should be a str."
                )

    return map_


def get_supported_fhir_resources():
    return set(get_fhir_to_patient_record_entry_map())


def get_required_entry_fields():
    return {"name", "start", "resource_type"}


def convert_fhir_to_patient_record_entry(
    resource: dict,
) -> Union[List[dict], dict]:
    """Convert a FHIR resource to a patient record entry using the map
    from `get_fhir_to_patient_record_entry_map`.

    NOTE: Only information in input resource that can be mapped to the entry is
    selected, any other information is lost. This could be extended in future.

    Parameters
    ----------
    resource : dict
        A FHIR resource

    Returns
    -------
    Union[List[dict], dict]
        If the input resource is a Bundle, returns a list of patient record
        entry dictionaries, otherwise return a single entry
    """

    def get_entry_from_resource(map_, resource):
        entry = {}
        for fhir_key, entry_key in map_.items():
            a = deepcopy(resource)
            exists = True
            for k in fhir_key:
                try:
                    b = a[k]
                except TypeError:
                    raise TypeError(
                        f'{resource["resourceType"]}, {fhir_key, entry_key}'
                    )
                except KeyError:
                    exists = False
                    break
                a = b
            if exists:
                entry[entry_key] = a
        entry["resource_type"] = resource["resourceType"]
        return entry

    map_ = get_fhir_to_patient_record_entry_map()

    if resource["resourceType"] == "Bundle":
        resources = [entry["resource"] for entry in resource["entry"]]
        return [
            get_entry_from_resource(map_[resource_["resourceType"]], resource_)
            for resource_ in resources
        ]
    else:
        return get_entry_from_resource(
            map_[resource["resourceType"]], resource
        )


def convert_patient_record_entry_to_fhir(
    entry: "PatientRecordEntry",  # noqa
    patient: "PatientAgent",  # noqa
    environments: "Dict[Union[str, int], EnvironmentAgent]" = None,  # noqa
) -> dict:
    """Converts a patient record entry (of type PatientRecordEntry) to a
    FHIR resource.

    The contents of entry.entry are converted to a FHIR dictionary `x`
    according to the mapping below. If there is raw FHIR data `y` in
    entry.fhir_resource, then the output will be the combined dictionary
    `{**x, **y}`

    NOTE: there is much room for expansion and improvement here. More
    resource types and fields could be added, fields like 'status' should
    probably be deduced and depend on input (for now we have set fixed
    place holder values), also for resource types like MedicationRequest, an
    'end' date could be mapped to the duration values.

    Parameters
    ----------
    entry : PatientRecordEntry
        A patient record entry
    patient : PatientAgent
        The instance of the PatientAgent with this entry
    environments : List[Dict[EnvironmentAgent]]
        Dictionary of environments, keyed by environment_id, that may have
        interacted with the patient. Currently this is not used, but could be
        useful in future if environment attribtues could enrich the FHIR data,
        for example, the location

    Returns
    -------
    dict
        A FHIR resource

    Raises
    ------
    ValueError
        If the resource type is not a type that is currently supported for
        conversion
    """
    # NOTE: noqas above avoid circular import

    def set_subject(resource, patient):
        resource["subject"] = {
            "display": str(patient.name),
        }

    def set_coding(_entry):
        coding = {
            "coding": [
                {
                    "display": _entry["name"],
                }
            ]
        }
        if "code" in _entry:
            coding["coding"][0]["code"] = _entry["code"]
        if "system" in _entry:
            coding["coding"][0]["system"] = _entry["system"]
        return coding

    resource_type = entry.fhir_resource_type
    _entry = entry.entry

    if resource_type == "Encounter":

        resource = {
            # status: planned | arrived | triaged | in-progress | onleave
            # | finished | cancelled +.
            "status": "finished",  # required
            "class": {  # required
                "display": _entry["name"],
            },
            "period": {
                "start": datetime_to_string(_entry["start"]),
            },
        }

        set_subject(resource, patient)

        if "code" in _entry:
            resource["class"]["code"] = _entry["code"]

        if "end" in _entry:
            resource["period"]["end"] = datetime_to_string(_entry["end"])

    elif resource_type == "Condition":

        resource = {
            "code": set_coding(_entry),
            "recordedDate": datetime_to_string(_entry["start"]),
        }

        set_subject(resource, patient)

        if "end" in _entry:
            resource["abatementDateTime"] = datetime_to_string(_entry["end"])
            resource["clinicalStatus"] = {
                "coding": [
                    {
                        "system": (
                            "http://terminology.hl7.org/CodeSystem/"
                            "condition-clinical"
                        ),
                        "code": "inactive",
                    }
                ]
            }

    elif resource_type == "Observation":

        resource = {
            # required
            "status": "final",
            "code": set_coding(_entry),
            "effectivePeriod": {
                "start": datetime_to_string(_entry["start"]),
            },
        }

        set_subject(resource, patient)

        if "end" in _entry:
            resource["effectivePeriod"]["end"] = datetime_to_string(
                _entry["end"]
            )
        if "value" in _entry:
            # NOTE: _entry["value"] must be a dictionary like
            # {
            #     "value": 4.12,
            #     "unit": "10^12/L",
            #     "system": "http://unitsofmeasure.org",
            #     "code": "10*12/L"
            # }
            resource["valueQuantity"] = _entry["value"]

    elif resource_type == "Procedure":

        resource = {
            # required
            "status": "final",
            "code": set_coding(_entry),
            "performedPeriod": {
                "start": datetime_to_string(_entry["start"]),
            },
        }

        set_subject(resource, patient)

        if "end" in _entry:
            resource["performedPeriod"]["end"] = datetime_to_string(
                _entry["end"]
            )

    elif resource_type == "MedicationRequest":

        med_id = f"medication-{entry.entry_id}"

        resource = {
            # required
            "status": "final",
            "intent": "order",
            "contained": [
                {
                    "resourceType": "Medication",
                    "id": med_id,
                    "code": set_coding(_entry),
                }
            ],
            "dispenseRequest": {
                "validityPeriod": {
                    "start": datetime_to_string(_entry["start"]),
                },
            },
            "medicationReference": {"reference": f"#{med_id}"},
        }

        set_subject(resource, patient)

        if "dosage" in _entry:
            resource["dosageInstruction"] = [
                {
                    "text": _entry["dosage"],
                },
            ]
        if "duration_value" in _entry and "duration_unit" in _entry:
            resource["dispenseRequest"]["expectedSupplyDuration"] = {
                "value": _entry["duration_value"],
                "unit": _entry["duration_unit"],
            }

    elif resource_type == "ServiceRequest":

        resource = {
            "status": "active",
            "intent": "order",
            "code": set_coding(_entry),
            "reasonCode": [
                {
                    "text": _entry["name"],
                }
            ],
            "occurrenceDateTime": datetime_to_string(_entry["start"]),
        }

        set_subject(resource, patient)

    elif resource_type == "Appointment":

        resource = {
            "status": "active",
            "serviceCategory": [set_coding(_entry)],
            "reasonReference": [
                {
                    "display": _entry["name"],
                }
            ],
            "description": "description",
            "start": datetime_to_string(_entry["start"]),
            "participant": [
                {
                    "actor": {
                        "reference": f"Patient/{patient.patient_id}",
                        "display": str(patient.name),
                    },
                    "status": "accepted",
                }
            ],
        }
        if "end" in _entry:
            resource["end"] = datetime_to_string(_entry["end"])

    elif resource_type == "Patient":
        resource = {
            "id": str(patient.patient_id),
            "gender": patient.gender,
            "birthDate": datetime_to_string(
                patient.birth_date, format_str="%Y-%m-%d"
            ),
        }
        if "end" in _entry:
            resource["deceasedDateTime"] = datetime_to_string(_entry["end"])
    else:
        raise ValueError(
            f"Currently cannot convert FHIR resource type {resource_type}."
        )

    if "id" not in resource:
        resource["id"] = str(entry.entry_id)

    resource["resourceType"] = resource_type

    if entry.fhir_resource is None:
        return resource
    else:
        return {**resource, **entry.fhir_resource}


def generate_patient_fhir_resources(
    patient: "PatientAgent",  # noqa
    environments: "Dict[Union[str, int], EnvironmentAgent]" = None,  # noqa
    validate: bool = True,
    server_url: Optional[str] = None,
    **kwargs,
):
    """Generate list of FHIR resources from patient record

    NOTE: there is much room for expansion and improvement here. For example,
    resources connected to the same encounter could all have references to
    that encounter id.

    Parameters
    ----------
    patient : PatientAgent
        The instance of the PatientAgent with this entry
    environments : List[Dict[EnvironmentAgent]]
        Dictionary of environments, keyed by environment_id, that may have
        interacted with the patient. Currently this is not used, but could be
        useful in future if environment attribtues could enrich the FHIR data,
        for example, the location
    server_url : Optional[str], optional
        URL for server to validate each resource, by default None, in which
        case only offline validation is performed
    kwargs: dict
        Keyword arguments for the online validation method - gets
        passed to the python requests.post function. For example,
        if want to pass custom headers with the request.

    Returns
    -------
    List[dict]
        List of FHIR resources
    """
    # NOTE: noqas above avoid circular import

    resources = []
    for entry in patient.record:
        resource = convert_patient_record_entry_to_fhir(
            entry, patient, environments
        )

        resources.append(resource)

    for resource in resources:
        FHIRHandler().validate(
            resource, resource["resourceType"], server_url, **kwargs
        )

    return resources


def generate_patient_fhir_bundle(
    patient: "PatientAgent",  # noqa
    environments: "Dict[Union[str, int], EnvironmentAgent]" = None,  # noqa
    bundle_type: str = "transaction",
    validate: bool = True,
    server_url: Optional[str] = None,
    save_path: Optional[Union[str, Path]] = None,
    **kwargs,
):
    """Generate FHIR bundle from patient record

    Parameters
    ----------
    patient : PatientAgent
        The instance of the PatientAgent with this entry
    environments : List[Dict[EnvironmentAgent]]
        Dictionary of environments, keyed by environment_id, that may have
        interacted with the patient. Currently this is not used, but could be
        useful in future if environment attribtues could enrich the FHIR data,
        for example, the location
    validate : bool, optional
        Whether to validate the bundle, by default True
    server_url : Optional[str], optional
        URL for server to validate each resource, by default None, in which
        case only offline validation is performed
    save_path : Optional[Union[str, Path]], optional
        JSON path if want to save bundle, by default None
    kwargs: dict
        Keyword arguments for the online validation method - gets
        passed to the python requests.post function. For example,
        if want to pass custom headers with the request.

    Returns
    -------
    dict
        FHIR bundle
    """
    # NOTE: noqas above avoid circular import

    resources = generate_patient_fhir_resources(
        patient,
        environments,
        validate=False,
        server_url=None,
    )

    bundle = create_fhir_bundle(resources, bundle_type)

    if save_path is not None:
        FHIRHandler().save(
            save_path, bundle, "Bundle", validate, server_url, **kwargs
        )
    elif validate:
        FHIRHandler().validate(
            bundle,
            "Bundle",
            server_url,
            **kwargs,
        )

    return bundle
