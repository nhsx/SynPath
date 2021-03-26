import random

from patient_abm import PATIENT_ABM_DIR
from patient_abm.data_handler.base import DataHandler

TEST_DATA_DIR = PATIENT_ABM_DIR / "tests" / "data"


def test_mkdir_save_and_load_text_with_path_string_input():

    text_to_save = " ".join(
        [str(random.choice(range(1000))) for _ in range(10)]
    )

    path = TEST_DATA_DIR / "new_test_dir" / "test.txt"

    assert not path.parent.exists()

    path_str = str(path)

    DataHandler().save_text(path_str, text_to_save)

    assert path.is_file()

    loaded_text = DataHandler().load_text(path_str)

    assert text_to_save == loaded_text

    path.unlink()
    path.parent.rmdir()
