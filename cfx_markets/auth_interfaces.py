from abc import ABC, abstractmethod
from typing import Optional


class AuthInterface(ABC):
    @abstractmethod
    def generate_access_token(self, *args, **kwargs) -> Optional[str]:
        """
        Generate a new access token if the current one is expired.
        """
        pass
