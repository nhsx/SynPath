import json
import pickle
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Union

import pandas


class DataHandler:
    """
    Base class to handle basic data operations
    """

    def convert_path(function: Callable):
        """
        Decorator function to convert path to pathlib.Path
        """

        @wraps(function)
        def wrapper(self, path: Union[Path, str], *args, **kwargs):
            if isinstance(path, Path):
                pass
            elif isinstance(path, str):
                path = Path(path)
            else:
                raise ValueError("`path` must be string or pathlib.Path type")
            return function(self, path, *args, **kwargs)

        return wrapper

    def make_dir(function: Callable):
        """
        Decorator function to make path directory
        """

        @wraps(function)
        def wrapper(self, path: Union[Path, str], *args, **kwargs):
            if path.suffix == "":
                path.mkdir(exist_ok=True, parents=True)
            else:
                path.parent.mkdir(exist_ok=True, parents=True)
            return function(self, path, *args, **kwargs)

        return wrapper

    @convert_path
    def load_text(self, path: Union[Path, str]) -> str:
        """
        Load text data
        """
        with path.open("r") as f:
            data = f.read()
        return data

    @convert_path
    def load_json(self, path: Union[Path, str], **kwargs) -> Union[dict, list]:
        """
        Load JSON data
        """
        with path.open("r") as f:
            data = json.load(f, **kwargs)
        return data

    @convert_path
    def load_csv(self, path: Union[Path, str], **kwargs) -> pandas.DataFrame:
        """
        Load CSV data
        """
        return pandas.read_csv(path, **kwargs)

    @convert_path
    def load_pickle(self, path: Union[Path, str], **kwargs) -> Any:
        """
        Load CSV data
        """
        with path.open("rb") as f:
            data = pickle.load(f, **kwargs)
        return data

    @convert_path
    def load(
        self, path: Union[Path, str], **kwargs
    ) -> Union[dict, list, str, pandas.DataFrame]:
        """
        Load JSON, text, CSV, or pickle data
        """
        if path.suffix == ".json":
            return self.load_json(path, **kwargs)
        elif path.suffix == ".txt":
            return self.load_text(path)
        elif path.suffix == ".csv":
            return self.load_csv(path, **kwargs)
        elif path.suffix in [".pkl", ".pickle"]:
            return self.load_pickle(path, **kwargs)

    @convert_path
    @make_dir
    def save_text(self, path: Union[Path, str], data: str) -> None:
        """
        Save text data
        """
        with path.open("w") as f:
            f.write(data)

    @convert_path
    @make_dir
    def save_json(
        self, path: Union[Path, str], data: Union[dict, list], **kwargs
    ) -> None:
        """
        Save JSON data
        """
        with path.open("w") as f:
            json.dump(data, f, **kwargs)

    @convert_path
    @make_dir
    def save_csv(
        self, path: Union[Path, str], data: pandas.DataFrame, **kwargs
    ) -> None:
        """
        Save JSON data
        """
        data.to_csv(path, **kwargs)

    @convert_path
    @make_dir
    def save_pickle(self, path: Union[Path, str], data: Any, **kwargs) -> None:
        """
        Save pickle data
        """
        with path.open("wb") as f:
            pickle.dump(data, f, **kwargs)

    @convert_path
    @make_dir
    def save(
        self,
        path: Union[Path, str],
        data: Union[dict, list, str, pandas.DataFrame],
        **kwargs
    ):
        """
        Save JSON, text, CSV, or pickle data
        """
        if path.suffix == ".json":
            return self.save_json(path, data, **kwargs)
        elif path.suffix == ".txt":
            return self.save_text(path, data)
        elif path.suffix == ".csv":
            return self.save_csv(path, data, **kwargs)
        elif path.suffix in [".pkl", ".pickle"]:
            return self.save_pickle(path, data, **kwargs)
