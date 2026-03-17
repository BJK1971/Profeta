from typing import Optional

from cfx_markets.auth_interfaces import AuthInterface
from cfx_markets.logger import get_logger

logger = get_logger(__name__)


class StandardAuth(AuthInterface):
    def __init__(self, access_token) -> None:
        super().__init__()
        self.access_token = access_token

    def generate_access_token(self, user: str, password: str) -> Optional[str]:
        """
        Generate a new access token if the current one is expired.
        """
        return self.access_token
