from patient_abm import PATIENT_ABM_DIR
from patient_abm.simulation.template import parse_config

TEST_DATA_DIR = PATIENT_ABM_DIR / "tests" / "data"


def test_parse_config():
    for i in range(3):
        config_path = TEST_DATA_DIR / f"config_{i}.json"
        assert parse_config(config_path)
