import datetime
import tarfile
import tempfile
from abc import abstractmethod
from pathlib import Path
from typing import Optional, TypeVar, Union

from patient_abm.data_handler.base import DataHandler
from patient_abm.utils import make_uuid, string_to_datetime

AgentType = TypeVar("AgentType", bound="Agent")


class Agent:
    """Base class for agent"""

    serialisable_attributes = [  #  TODO: change to serializable_attributes
        "id",
        "created_at",
        "tz",
    ]

    def __init__(
        self,
        id_: Optional[Union[str, int]] = None,
        created_at: Optional[Union[str, datetime.datetime]] = None,
        tz: datetime.timezone = datetime.timezone.utc,
    ):
        """Initialize base agent class. The inputs are all set as
        attributes

        Parameters
        ----------
        id_ : Optional[Union[str, int]], optional
            Unique ID, by default None. If not supplied, will be
            automatically set by uuid.uuid4().urn. The actual attribute
            name will be 'id' not 'id_'.
        created_at : Optional[Union[str, datetime.datetime]], optional
            Time agent is created, by default None. If not supplied, will be
            automatically set by datetime.datetime.now()
        tz : datetime.timezone, optional
            Timezone for created_at, by default datetime.timezone.utc
        """
        if id_ is None:
            self.id = make_uuid()
        else:
            self.id = id_

        self.tz = tz

        if created_at is None:
            # TODO: improve timezone handling
            self.created_at = datetime.datetime.now(tz=self.tz)
        else:
            self.created_at = string_to_datetime(created_at)

    def __repr__(self) -> str:
        # TODO: make improved repr in each subclass
        return (
            f"{self.__class__.__name__}(id={self.id}, "
            f"created_at={self.created_at})"
        )

    def _prepare_for_save(self, attr_name: str):
        return getattr(self, attr_name)

    def save(self, tar_file: Union[str, Path]) -> None:
        """Save agent object as a tar file.

        Parameters
        ----------
        tar_file : Union[str, Path]
            Path to tar file.
        """
        data_handler = DataHandler()

        Path(tar_file).parent.mkdir(exist_ok=True, parents=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            paths = []
            for attr_name in self.serialisable_attributes:
                path = temp_dir / f"{attr_name}.pickle"
                paths.append(path)
                attr = self._prepare_for_save(attr_name)
                data_handler.save_pickle(path, attr)

            with tarfile.open(tar_file, "w") as archive:
                for path in paths:
                    archive.add(str(path), arcname=path.name)

    @classmethod
    def load(cls, tar_file: Union[str, Path]) -> AgentType:
        """Load an agent object from a tar file

        Parameters
        ----------
        tar_file : Union[str, Path]
            Path to tar file.
        """

        data_handler = DataHandler()

        kwargs = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            with tarfile.open(tar_file, "r") as archive:
                archive.extractall(path=str(temp_dir))

            for attr_name in cls.serialisable_attributes:

                path = temp_dir / f"{attr_name}.pickle"
                kwargs[attr_name] = data_handler.load_pickle(path)

        _kwargs = kwargs["kwargs"]
        del kwargs["kwargs"]

        kwargs["id_"] = kwargs["id"]
        del kwargs["id"]

        return cls(**kwargs, **_kwargs)

    @abstractmethod
    def update(self, *args, **kwargs):
        pass
