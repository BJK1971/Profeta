from enum import Enum
from typing import Dict, List, Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_pascal


class BaseAwsSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            validation_alias=to_pascal, serialization_alias=to_pascal
        ),
        populate_by_name=True,
        from_attributes=True,
    )


class ConfigItem(BaseModel):
    algorithm_id: int
    value_name: str


class DatasetConfig(BaseModel):
    file_id: str
    tms_name: str
    algorithm_config: List[ConfigItem] = Field(default_factory=list)


class MappingConfig(BaseModel):
    mapping_config: List[DatasetConfig] = Field(default_factory=list)


class JoinMethod(int, Enum):
    inner = 1
    left = 2
    right = 3
    full = 4
    only_forecast = 5


class IntervalUnit(str, Enum):
    second = "Second"
    minute = "Minute"
    hour = "Hour"
    day = "Day"
    week = "Week"
    month = "Month"


class AggMethod(str, Enum):
    time_simple = "TimeSimple"
    time_and_view = "TimeAndView"
    agg_candlesticks = "AggregatedCandlesticks"


class SortMode(int, Enum):
    ascending = 1
    descending = 2


class AwsAuthenticationResult(BaseAwsSchema):
    access_token: Optional[str] = Field(default=None)
    expires_in: Optional[int] = Field(default=None)
    id_token: Optional[str] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)
    token_type: Optional[str] = Field(default=None)


class AwsAuthenticationResponse(BaseAwsSchema):
    authentication_result: Optional[AwsAuthenticationResult] = Field(
        default=None, alias="AuthenticationResult"
    )
    challenge_parameters: Optional[Dict[str, str]] = Field(default_factory=dict)
    challenge_name: Optional[str] = None
    available_challenges: Optional[List[str]] = Field(default_factory=list)
    session: Optional[str] = None
    exception: Optional[str] = Field(default=None, alias="_type")
    message: Optional[str] = Field(default=None)


class AwsAuthRequest(BaseAwsSchema):
    auth_flow: str
    client_id: str
    auth_parameters: Dict[str, str] = Field(default_factory=dict)


class FunctionResponse(BaseModel):
    status_code: int = Field(default=200)
    message: Optional[str] = Field(default=None)
    success: bool = Field(default=False)
    data: Optional[Dict] = Field(default=None)
