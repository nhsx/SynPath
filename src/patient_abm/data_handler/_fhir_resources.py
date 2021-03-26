# flake8: noqa

# Need to import these classes so that they are in the
# namespace of fhir.resources which ensures that
# patient_abm.data_handler.fhir.get_fhir_resources_parser works

from fhir.resources.appointment import Appointment
from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.encounter import Encounter
from fhir.resources.location import Location
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.observation import Observation
from fhir.resources.organization import Organization
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner
from fhir.resources.procedure import Procedure
from fhir.resources.servicerequest import ServiceRequest
