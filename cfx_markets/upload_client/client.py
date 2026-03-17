import os
import pathlib
from typing import Any, Dict, List, Optional

import pandas as pd

from cfx_markets.api_client.client import ApiClient
from cfx_markets.logger import get_logger
from cfx_markets.models import (
    MappingConfig,
)

logger = get_logger(__name__)


class UploadClient:
    """This class is responsible for uploading forecast data to the server using the API client.
    It handles the mapping of the data from the CSV files to the required JSON format and uploads it to the server.
    It also handles the authentication and configuration of the API client.
    The class uses the ApiClient class to perform the actual API calls.
    """

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str,
        config_path: Optional[str] = None,
    ):
        self.client = ApiClient(
            username=username,
            password=password,
            base_url=base_url,
        )
        self.config_path = config_path
        if self.config_path is not None:
            if not (os.path.exists(self.config_path)):
                error = f"Config file {self.config_path} does not exist. Please provide a valid config file."
                logger.error(error)
                raise FileNotFoundError(error)

    def _map_upload_data(
        self,
        file_id: str,
        market_id: int,
        instr_id: int,
        df: pd.DataFrame,
    ) -> Dict[int, Optional[List[Dict[str, Any]]]]:
        """Map the data from the CSV files to the required JSON format.

        :param market_id: ID of the market.
        :param instr_id: ID of the instrument.
        :param file_path: Path to the CSV file.
        :return: List of dictionaries containing the mapped data.
        """
        if self.config_path is None:
            msg = (
                "Mapping config is not provided. Please provide a mapping config file."
            )
            logger.error(msg)
            raise FileNotFoundError(msg)

        json_string = pathlib.Path(self.config_path).read_text()
        config = MappingConfig.model_validate_json(json_string)
        mapping_items = config.mapping_config
        if len(mapping_items) == 0:
            msg = "Mapping config is empty. Please provide a valid mapping config file."
            logger.error(msg)
            raise ValueError(msg)

        config_match = next(
            (
                config_item
                for config_item in mapping_items
                if config_item.file_id == file_id
            ),
            None,
        )

        if config_match is None:
            msg = f"File {file_id} not found in the mapping config."
            logger.error(msg)
            raise ValueError(msg)

        if config_match.tms_name is None:
            msg = "Timestamp name is not provided in the mapping config."
            logger.error(msg)
            raise ValueError(msg)

        if config_match.tms_name not in df.columns:
            msg = f"Timestamp name '{config_match.tms_name}' not found in the upload data."
            logger.error(msg)
            raise ValueError(msg)

        df.loc[:, config_match.tms_name] = pd.to_datetime(
            df.loc[:, config_match.tms_name],
            errors="coerce",
            utc=True,
        )

        algo_config = config_match.algorithm_config
        return {
            algo_config_item.algorithm_id: self._parse_data_to_json(
                algo_config_item.algorithm_id,
                instr_id,
                market_id,
                config_match.tms_name,
                algo_config_item.value_name,
                df,
            )
            for algo_config_item in algo_config
        }

    def _parse_data_to_json(
        self,
        algo_id: int,
        instr_id: int,
        market_id: int,
        tms_name: str,
        value_name: str,
        df: pd.DataFrame,
    ) -> Optional[List[Dict[str, Any]]]:
        """Parse the data to JSON format.
        This method is used to convert the data from the CSV files to the required JSON format.

        :param algo_id: the algorithm ID.
        :param instr_id: the instrument ID.
        :param market_id: the market ID.
        :param tms_name: the name of the timestamp column.
        :param value_name: the name of the value column.
        :param df: the DataFrame containing the data.
        :return: List of dictionaries containing the mapped data.
        """
        try:
            if value_name not in df.columns:
                msg = f"Value name '{value_name}' not found in the upload data."
                logger.warning(msg)
                return None

            json_data = [
                {
                    "algorithmId": algo_id,
                    "marketId": market_id,
                    "instrumentId": instr_id,
                    "forecast": x,
                    "tms": y.to_pydatetime(),
                }
                for x, y in zip(
                    df.loc[:, value_name].tolist(),
                    df.loc[:, tms_name].tolist(),
                )
            ]
            return json_data
        except Exception as e:
            msg = f"Error parsing data to JSON: {e}"
            logger.error(msg)
            return None

    def upload_forecasts_file(
        self,
        instr_id,
        market_id,
        file_path: str,
    ) -> bool:
        """Upload forecast data from a .csv file.

        :param algo_id: ID of the forecast algorithm.
        :param file_path: Path to the .csv file containing forecast data.
        :param instr_id: ID of the instrument to upload forecasts for.
        :param market_id: ID of the market to upload forecasts for.
        :return: True if the upload was successful, False otherwise.
        :raises FileNotFoundError: If the file does not exist or is empty.
        :raises ValueError: If the file is empty or if the mapping config is invalid.
        """
        success = True

        if not os.path.exists(file_path):
            msg = f"File {file_path} does not exist. Please provide a valid file."
            logger.error(msg)
            raise FileNotFoundError(msg)

        if os.path.getsize(file_path) == 0:
            msg = f"File {file_path} is empty. Please provide a valid file."
            logger.error(msg)
            raise ValueError(msg)

        df = pd.read_csv(file_path, encoding="utf-8", header=0)

        json_data = self._map_upload_data(
            file_id=os.path.basename(file_path),
            market_id=market_id,
            instr_id=instr_id,
            df=df,
        )
        for key, value in json_data.items():
            if value is None or len(value) == 0:
                msg = f"File {file_path} has no data for algorithm ID {key}."
                logger.warning(msg)
                return False
            success = success and self.client.upload_forecasts(
                algo_id=key,
                data=value,
            )
        return success

    def upload_forecasts_dataframe(
        self,
        instr_id: int,
        market_id: int,
        data: pd.DataFrame,
        file_path: str,  # need to find a better way to handle this
    ) -> bool:
        """Upload forecast data from a .csv file.

        :param algo_id: ID of the forecast algorithm.
        :param file_path: Path to the .csv file containing forecast data.
        :param instr_id: ID of the instrument to upload forecasts for.
        :param market_id: ID of the market to upload forecasts for.
        :return: True if the upload was successful, False otherwise.
        :raises ValueError: If the mapping config is invalid.
        """
        success = True

        json_data = self._map_upload_data(
            file_id=os.path.basename(file_path),
            market_id=market_id,
            instr_id=instr_id,
            df=data,
        )
        for key, value in json_data.items():
            if value is None or len(value) == 0:
                msg = f"File {file_path} has no data for algorithm ID {key}."
                logger.warning(msg)
                return False
            success = success and self.client.upload_forecasts(
                algo_id=key,
                data=value,
            )
        return success
