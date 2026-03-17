import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from cfx_markets.api_client.auth import AwsApiAuth
from cfx_markets.auth_interfaces import AuthInterface
from cfx_markets.exceptions import DataNotFoundException
from cfx_markets.helpers import encode_datetime
from cfx_markets.logger import get_logger
from cfx_markets.models import (
    AggMethod,
    FunctionResponse,
    IntervalUnit,
    JoinMethod,
    SortMode,
)

logger = get_logger(__name__)


class ApiClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        auth: AuthInterface = AwsApiAuth(),
    ):
        self.base_url = base_url
        self.auth = auth
        self.username = username
        self.password = password

    def _execute_request(
        self, req: requests.Request, additional_headers: dict | None = None
    ) -> FunctionResponse:
        """Execute the request to the server.
        This method is responsible for sending the request to the server and returning the response.

        :param req: the prepared request to be sent to the server
        :param additional_headers: additional headers that might be needed, defaults to None
        :return: the response from the server as a FunctionResponse object
        """
        response = None
        try:
            access_token = self.auth.generate_access_token(self.username, self.password)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "cfx-markets-client",
            }
            if additional_headers:
                headers.update(additional_headers)
            req.headers = headers
            with requests.Session() as session:
                prepared_request = session.prepare_request(req)
                response = session.send(prepared_request, verify=False)
                response.raise_for_status()
                if "application/json" in response.headers.get("Content-Type", ""):
                    return FunctionResponse(success=True, data=response.json())
                else:
                    return FunctionResponse(status_code=200, success=True)
        except requests.exceptions.HTTPError as e:
            if response is not None:
                try:
                    return FunctionResponse(
                        status_code=response.status_code,
                        message=f"HTTP error in executing API request {req.url}: {e}",
                        data=response.json(),
                        success=False,
                    )
                except json.JSONDecodeError:
                    error_message = response.text
                    logger.error(f"Response content: {error_message}")
                    return FunctionResponse(
                        status_code=response.status_code,
                        message=error_message,
                        data=None,
                        success=False,
                    )
            return FunctionResponse(
                status_code=500,
                message=f"HTTP error in executing API request {req.url}: {e}",
                data=None,
                success=False,
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return FunctionResponse(
                status_code=500,
                message=f"Unexpected error in executing API request {req.url}: {e}",
                data=None,
                success=False,
            )

    def get_forecasts(
        self,
        algo_id: int,
        instr_id: int,
        market_id: int,
        join_type: JoinMethod = JoinMethod.inner,
        count: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        sort_mode: SortMode = SortMode.ascending,
    ) -> Dict[Any, Any]:
        """Make a GET request to the forecast endpoint to get JSON forecast data.

        :param algo_id: the ID of the forecast algorithm
        :param instr_id: the ID of the chosen instrument
        :param market_id: the ID of the chosen market
        :param join_type: How to join the market prices with the forecasts:
            * inner (Returned records will have a price and a forecast)
            * left (Prices have priority: if there is no forecast for a
            price, it will be added to the result as null)
            * right (Forecasts have priority: if there is no prices for
            a forecast, they will be added to the result as null)
            * full (Returned records will have either a Price or a
            Forecast record (or both))
            * only_forecasts (Returns only available forecasts without any
            combination with the related prices), defaults to inner
        :param count: how many records can be downloaded, defaults to None
        :param start: start timestamp, defaults to None
        :param end: end timestamp, defaults to None
        :param sort_mode: how to sort the data:
            * ascending (Sorts the data in ascending order)
            * descending (Sorts the data in descending order), defaults to ascending
        :return: the forecast data as a dictionary
        """
        url = f"{self.base_url}/api/Forecast/{algo_id}/{instr_id}/{market_id}"
        params = {
            "joinType": join_type.value if join_type is not None else None,
            "count": count,
            "start": start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if start is not None
            else None,
            "end": end.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if end is not None
            else None,
            "sortMode": sort_mode.value if sort_mode is not None else None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        request = requests.Request("GET", url, params=params)
        response = self._execute_request(request)
        if response.success:
            return response.data if response.data else {}
        else:
            msg = f"Error fetching forecasts: {response.message}"
            logger.error(msg)
            raise DataNotFoundException(msg)

    def upload_forecasts(
        self,
        algo_id: int,
        data: List[Dict[str, Any]],
    ) -> bool:
        """Upload forecast data in JSON form.

        :param algo_id: ID of the forecast algorithm.
        :param data: List of forecast data in JSON format.
        :return: True if the upload was successful, False otherwise.
        """
        url = f"{self.base_url}/api/Forecast/{algo_id}"
        request = requests.Request(
            "POST",
            url,
            data=json.dumps(data, default=encode_datetime),
        )

        response = self._execute_request(
            request,
            additional_headers={"Content-Type": "application/json"},
        )

        return response.success

    def get_exchange_candles(
        self,
        instr_id: int,
        market_id: int,
        interval_unit: IntervalUnit,
        interval: int,
        agg_method: AggMethod = AggMethod.time_simple,
        count: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        sort_mode: SortMode = SortMode.ascending,
    ) -> Dict[Any, Any]:
        """Get candlestick data for a given instrument and market.
        This method fetches candlestick data from the exchange using the specified parameters.
        The data is returned as a dictionary.

        :param instr_id: ID of the instrument.
        :param market_id: ID of the market.
        :param interval_unit: Unit of the interval
        (second, minute, hour, day, week, month).
        :param interval: Interval value.
        :param agg_method: Aggregation method
        :param count: Number of records to return.
        :param start: Start timestamp.
        :param end: End timestamp.
        :param sort_mode: Sort mode (default is ascending).
        :return: Candlestick data.
        """
        url = f"{self.base_url}/api/Price/candle/{interval_unit.value}/{interval}/{instr_id}/{market_id}"
        params = {
            "method": agg_method.value if agg_method is not None else None,
            "count": count,
            "start": start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if start is not None
            else None,
            "end": end.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if end is not None
            else None,
            "sortMode": sort_mode.value if sort_mode is not None else None,
        }
        request = requests.Request("GET", url, params=params)
        response = self._execute_request(request)
        if response.success:
            return response.data if response.data else {}
        else:
            msg = f"Error fetching exchange candles: {response.message}"
            logger.error(msg)
            raise DataNotFoundException(msg)
