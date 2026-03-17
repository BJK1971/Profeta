from datetime import datetime, timedelta
from typing import Optional

import requests

from cfx_markets.auth_interfaces import AuthInterface
from cfx_markets.config import AWS_CLIENT_ID, AWS_COGNITO_URL
from cfx_markets.logger import get_logger
from cfx_markets.models import AwsAuthenticationResponse, AwsAuthRequest

logger = get_logger(__name__)


class AwsApiAuth(AuthInterface):
    def __init__(
        self,
    ):
        self.auth_url = AWS_COGNITO_URL
        self.client_id = AWS_CLIENT_ID
        self.refresh_token = None
        self.expiration_time = None
        self.access_token = None

    def _execute_request(self, request_content: AwsAuthRequest) -> dict:
        """Execute the request to the auth server.
        This method is responsible for sending the request to the AWS Cognito authentication server and returning the response.

        :param request_content: the request content to be sent to the server
        :return: the response from the server as a dictionary
        :raises requests.exceptions.HTTPError: if the request fails
        """
        headers = {
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            "Content-Type": "application/x-amz-json-1.1",
        }
        payload = request_content.model_dump_json(by_alias=True)
        response = requests.post(self.auth_url, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def initiate_auth(self, username, password) -> AwsAuthenticationResponse:
        """Request a new token from the auth server.

        :param username: the username
        :param password: the password
        """
        request = AwsAuthRequest(
            auth_flow="USER_PASSWORD_AUTH",
            client_id=self.client_id,
            auth_parameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )
        json_response = self._execute_request(request)
        return AwsAuthenticationResponse.model_validate(json_response)

    def initiate_refresh_token(self, refresh_token: str) -> AwsAuthenticationResponse:
        """Refresh the token when the user has already been authenticated.

        :param refresh_token: the refresh token
        :return: the response from the server as a dictionary
        """
        request = AwsAuthRequest(
            auth_flow="REFRESH_TOKEN_AUTH",
            client_id=self.client_id,
            auth_parameters={
                "REFRESH_TOKEN": refresh_token,
            },
        )

        json_response = self._execute_request(request)
        return AwsAuthenticationResponse.model_validate(json_response)

    def generate_access_token(self, username: str, password: str) -> Optional[str]:
        """Generate a new access token if the current one is expired."""
        try:
            if (
                self.expiration_time is None
                or self.access_token is None
                or self.refresh_token is None
            ):
                aws_response = self.initiate_auth(username=username, password=password)
                if aws_response.authentication_result is not None:
                    self.access_token = aws_response.authentication_result.access_token
                    self.refresh_token = (
                        aws_response.authentication_result.refresh_token
                    )
                    expires_in = (
                        0
                        if aws_response.authentication_result.expires_in is None
                        else aws_response.authentication_result.expires_in
                    )
                    self.expiration_time = datetime.now() + timedelta(
                        seconds=float(expires_in)
                    )
                    return self.access_token
                return None

            if datetime.now() > self.expiration_time:
                aws_response = self.initiate_refresh_token(self.refresh_token)
                if aws_response.authentication_result is not None:
                    self.access_token = aws_response.authentication_result.access_token
                    expires_in = (
                        0
                        if aws_response.authentication_result.expires_in is None
                        else aws_response.authentication_result.expires_in
                    )
                    self.expiration_time = datetime.now() + timedelta(
                        seconds=float(expires_in)
                    )
                    return self.access_token
                return None
            return self.access_token

        except Exception as e:
            logger.error(f"Error generating access token: {e}")
            return None
