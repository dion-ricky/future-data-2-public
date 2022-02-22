import os
from pathlib import Path

class DAGOutputPath:

    def __init__(
            self,
            path):
        self.__path = path
        dir = os.path.dirname(path)

        Path(dir).mkdir(parents=True, exist_ok=True)

        assert os.path.exists(dir)
        assert os.path.isdir(dir)

    @property
    def path(self):
        return self.__path