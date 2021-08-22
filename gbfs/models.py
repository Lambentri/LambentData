import datetime
from typing import Dict, List, Optional

from aenum import Enum
from geojson_pydantic import MultiPolygon
from pydantic import BaseModel, Field


class GBFSFeedName(Enum):
    SYSTEM_INFORMATION = "system_information"
    STATION_INFORMATION = "station_information"
    STATION_STATUS = "station_status"
    FREE_BIKE_STATUS = "free_bike_status"
    SYSTEM_HOURS = "system_hours"
    SYSTEM_CALENDAR = "system_calendar"
    SYSTEM_REGIONS = "system_regions"
    SYSTEM_ALERTS = "system_alerts"


class GBFSIndexFeed(BaseModel):
    name: GBFSFeedName
    url: str


class GBFSIndex(BaseModel):
    last_updated: int  # unix timestamp
    tll: int
    data: Dict[str, Dict[str, List[GBFSIndexFeed]]]


# Entities (System Information)
class GBFSSystemInformationData(BaseModel):
    purchase_url: str
    start_date: datetime.date
    system_id: str
    language: str
    email: str
    operator: str
    name: str
    url: str
    timezone: str
    phone_number: str
    license_url: str
    short_name: str


class GBFSSystemInformation(BaseModel):
    data: GBFSSystemInformationData
    late_updated: int
    ttl: int


# Entities (Station Information)
class GBFSRentalMethod(Enum):
    KEY = "key"
    CREDITCARD = "creditcard"
    PAYPASS = "paypass"
    APPLEPAY = "applepay"
    ANDROIDPAY = "androidpay"
    TRANSITCARD = "transitcard"
    ACCOUNTNUMBER = "accountnumber"
    PHONE = "phone"


class GBFSStation(BaseModel):
    station_id: str
    name: str
    short_name: str
    lat: str
    lon: str

    address: Optional[str]
    cross_street: Optional[str]
    region_id: Optional[str]
    post_code: Optional[str]
    rental_methods: List[GBFSRentalMethod]
    is_virtual_station: Optional[bool]
    station_area: Optional[MultiPolygon]
    capacity: Optional[int]
    vehicle_capacity: Optional[Dict[str, int]]
    vehicle_type_capacity: Optional[Dict[str, int]]
    is_valet_station: Optional[bool]
    rental_uris: Dict[str, str]

    rental_url: str
    # bluebikes (GBoston/MA) fields
    legacy_id: Optional[str]
    eightd_station_services: List[str] = Field(default_factory=list)  # ???
    eightd_has_key_dispenser: Optional[bool]
    station_type: Optional[str]
    electric_bike_surcharge_waiver: Optional[bool]
    has_kiosk: Optional[bool]
    external_id: Optional[str]


class GBFSStationInformation(BaseModel):
    data: List[GBFSStation]
    late_updated: int
    ttl: int


# Entities (Station Status)
class GBFSVehicleType(BaseModel):
    vehicle_type_id: str
    count: int


class GBFSVehicleDock(BaseModel):
    vehicle_type_ids: List[str]
    count: int


class GBFSStationStatus(BaseModel):
    station_id: str

    vehicle_types_available: Optional[List[GBFSVehicleType]]
    vehicle_docks_available: Optional[List[GBFSVehicleDock]]

    num_bikes_available: int
    num_bikes_disabled: Optional[int]
    num_docks_available: Optional[int]
    num_docks_disabled: Optional[int]

    is_installed: bool
    is_renting: bool
    is_returning: bool
    last_reported: int

    # bluebikes (GBoston/MA) Fields
    eightd_has_available_keys: Optional[bool]
    station_status: Optional[str]
    num_ebikes_available: Optional[str]


class GBFSStationStatus(BaseModel):
    data: List[GBFSStationStatus]
    late_updated: int
    ttl: int


# Entities (Free Bike Status
class GBFSFreeBikeBike(BaseModel):
    bike_id: str
    system_id: Optional[str]
    lat: Optional[str]
    lon: Optional[str]
    is_reserved: bool
    is_disabled: bool
    rental_uris: Dict[str, str]
    vehicle_type_id: Optional[str]
    last_reported: Optional[int]
    current_range_meter: Optional[float]
    station_id: Optional[str]
    pricing_plan_id: Optional[str]


class GBFSFreeBikeData(BaseModel):
    bikes: List[GBFSFreeBikeBike]


class GBFSFreeBikeStatus(BaseModel):
    data: GBFSFreeBikeData
    late_updated: int
    ttl: int


# Entities (System Hours)
class GBFSSystemHoursHour(BaseModel):
    user_types: List["str"]
    days: List[str]
    start_time: datetime.time
    end_time: datetime.time


class GBFSSystemHoursData(BaseModel):
    rental_hours: List[GBFSSystemHoursHour]


class GBFSSystemHours(BaseModel):
    data: GBFSSystemHoursData
    late_updated: int
    ttl: int


# Entities (System Calendar)
class GBFSSystemCalendarCalendar(BaseModel):
    start_month: int
    start_day: int
    start_year: Optional[int]

    end_month: int
    end_day: int
    end_year: Optional[int]


class GBFSSystemCalendarData(BaseModel):
    rental_hours: List[GBFSSystemCalendarCalendar]


class GBFSSystemCalendar(BaseModel):
    data: GBFSSystemCalendarData
    late_updated: int
    ttl: int


# Entities (System Regions)
class GBFSSystemRegionRegion(BaseModel):
    region_id: str
    name: str


class GBFSSystemRegionData(BaseModel):
    regions: List[GBFSSystemRegionRegion]


class GBFSSystemRegion(BaseModel):
    data: GBFSSystemRegionData
    late_updated: int
    ttl: int


# Entities (System Alerts)
class GBFSSystemAlertType(Enum):
    SYSTEM_CLOSURE = "system_closure"
    STATION_CLOSURE = "station_closure"


class GBFSSystemAlertsAlertTime(BaseModel):
    start: int
    end: Optional[int]


class GBFSSystemAlertsAlert(BaseModel):
    alert_id: str
    type: GBFSSystemAlertType
    times: Optional[GBFSSystemAlertsAlertTime]
    station_ids: Optional[List[str]]
    region_ids: Optional[List[str]]
    url: Optional[str]
    summary: str
    description: Optional[str]
    last_updated: int


class GBFSSystemAlertsData(BaseModel):
    alerts: List[GBFSSystemAlertsAlert]


class GBFSSystemAlerts(BaseModel):
    data: GBFSSystemAlertsData
    late_updated: int
    ttl: int
