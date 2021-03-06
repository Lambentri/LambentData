import datetime
from enum import Enum

from pydantic import BaseModel, Field

observation_color_map = {
    1: [0, 228, 0],
    2: [255, 255, 0],
    3: [255, 126, 0],
    4: [255, 0, 0],
    5: [143, 239, 151],
    6: [126, 0, 35],
}


class ObservationParameter(Enum):
    O3 = "O3"
    PM2_5 = "PM2.5"
    PM10 = "PM10"

    def __str__(self):
        return self.value.lower()


class AirNowCategory(BaseModel):
    number: int = Field(alias="Number")
    name: str = Field(alias="Name")


class AirNowObservation(BaseModel):
    class Config:
        allow_population_by_field_name = False

    date_observed: datetime.date = Field(alias="DateObserved")
    hour_observed: int = Field(alias="HourObserved")
    local_tz: str = Field(alias="LocalTimeZone")
    reporting_area: str = Field(alias="ReportingArea")
    state_code: str = Field(alias="StateCode")
    lat: str = Field(alias="Latitude")
    lon: str = Field(alias="Longitude")
    param_name: ObservationParameter = Field(alias="ParameterName")
    aqi: int = Field(alias="AQI")
    category: AirNowCategory = Field(alias="Category")


