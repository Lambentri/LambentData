import datetime
from dataclasses import dataclass
from typing import Optional

from aenum import IntEnum, Enum


class LocationType(IntEnum):
    NONE = -1
    Stop = 0
    Station = 1
    Entrance = 2
    Exit = 2
    Generic = 3
    Boarding = 4


class AccessibilityEnum(IntEnum):
    # used by wheelchair boarding / accessible / bikes allowed
    NONE = -1
    EMPTY = 0
    SOME = 1
    NO = 2


class RouteType(IntEnum):
    TRAM_STREETCAR_LR = 0
    SUBWAY_METRO = 1
    RAIL = 2
    BUS = 3
    FERRY = 4
    CABLE_TRAM = 5
    GONDOLA_TRAMWAY = 6
    FUNICULAR = 7
    TROLLEYBUS = 11
    MONORAIL = 12


class Pickup(IntEnum):
    NONE = -1
    CONTINUOUS = 0
    PHONE_AGENCY = 2
    COORDINATE_DRIVER = 3


class TimePoint(IntEnum):
    APPROXIMATE = 0
    EXACT = 1


class CalendarDay(IntEnum):
    AVAILABLE = 1
    UNAVAILABLE = 0


class CalendarException(IntEnum):
    ADDED = 1
    REMOVED = 2


class PaymentMethod(IntEnum):
    ONBOARD = 0
    PREBOARD = 1


class Transfers(IntEnum):
    NONE = 0
    ONCE = 1
    TWICE = 2


class Exactness(IntEnum):
    FREQUENCY = 0
    SCHEDULE = 1


class TransferType(IntEnum):
    RECOMMENDED = 0
    TIMED = 1
    MINIMUM_TIME = 2
    NOT_POSSIBLE = 3


class PathwayMode(IntEnum):
    WALKWAY = 1
    STAIRS = 2
    MOVING_SIDEWALK = 3
    ESCALATOR = 4
    ELEVATOR = 5
    FAREGATE = 6


class BiDirectionality(IntEnum):
    UNIDIRECTIONAL = 0
    BIDIRECTIONAL = 1


class TableName(Enum):
    AGENCY = "agency"
    STOPS = "stops"
    ROUTES = "routes"
    TRIPS = "trips"
    STOP_TIMES = "stop_times"
    FEED_INFO = "feed_info"
    PATHWAYS = "pathways"
    LEVELS = "levels"
    ATTRIBUTIONS = "attributions"


class YesNo(IntEnum):
    NO = 0
    YES = 1


class NoYes(IntEnum):
    YES = 0
    NO = 1


# some liberties have been taken, most dates/times/and ids are cast to strings for convenience
@dataclass
class Agency:
    agency_id: str
    agency_name: str
    agency_url: str
    agency_timezone: Optional[str] = None
    agency_lang: Optional[str] = None
    agency_phone: Optional[str] = None
    agency_fare_url: Optional[str] = None
    agency_email: Optional[str] = None


@dataclass
class Stop:
    stop_id: str
    stop_name: str

    stop_code: Optional[str] = None
    stop_desc: Optional[str] = None
    stop_lat: Optional[str] = None
    stop_lon: Optional[str] = None
    zone_id: Optional[int] = None
    stop_url: Optional[str] = None
    location_type: Optional[LocationType] = None
    parent_station: Optional[int] = None
    stop_timezone: Optional[str] = None
    wheelchair_boarding: Optional[AccessibilityEnum] = None
    level_id: Optional[int] = None
    platform_code: Optional[str] = None
    platform_name: Optional[str] = None  # gtfs-exp
    stop_address: Optional[str] = None  # gtfs-exp
    municipality: Optional[str] = None  # gtfs-exp
    on_street: Optional[str] = None  # gtfs-exp
    at_street: Optional[str] = None  # gtfs-exp
    vehicle_type: Optional[str] = None  # gtfs-exp


@dataclass
class Route:
    route_id: str
    route_type: RouteType

    agency_id: Optional[int] = None
    route_short_name: Optional[str] = None
    route_long_name: Optional[str] = None
    route_desc: Optional[str] = None
    route_color: Optional[str] = None
    route_text_color: Optional[str] = None
    route_sort_order: Optional[int] = None
    route_url: Optional[str] = None  # gtfs-exp???
    route_fare_class: Optional[str] = None  # gtfs-exp
    continuous_pickup: Optional[Pickup] = None
    continuous_drop_off: Optional[Pickup] = None

    line_id: Optional[str] = None  # gtfs-exp
    listed_route: Optional[NoYes] = None  # gtfs-exp


@dataclass
class Trip:
    route_id: str
    service_id: str
    trip_id: str
    trip_headsign: Optional[str] = None
    trip_short_name: Optional[str] = None
    direction_id: Optional[int] = None
    block_id: Optional[str] = None
    shape_id: Optional[int] = None
    wheelchair_accessible: Optional[AccessibilityEnum] = None
    bikes_allowed: Optional[AccessibilityEnum] = None

    trip_route_type: Optional[RouteType] = None  # gtfs-exp
    route_pattern_id: Optional[str] = None  # gtfs-exp


@dataclass
class StopTime:
    trip_id: str
    stop_id: str
    stop_sequence: int

    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    stop_headsign: Optional[str] = None
    pickup_type: Optional[Pickup] = None
    drop_off_type: Optional[Pickup] = None
    continuous_pickup: Optional[Pickup] = None
    continuous_drop_off: Optional[Pickup] = None
    shape_dist_traveled: Optional[float] = None
    timepoint: Optional[TimePoint] = None

    checkpoint_id: Optional[str] = None  # gtfs-exp

    def arrival_time_as_delta_seconds(self, now: datetime.datetime) -> int:
        h, m, s = [int(i) for i in self.arrival_time.split(':')]
        if h > 23:
            h -= 24

        at_dt = datetime.datetime.combine(now.date(), datetime.time(h,m,s), tzinfo=now.tzinfo)
        delta = (at_dt - now).seconds
        return delta


@dataclass
class Calendar:
    service_id: str
    monday: CalendarDay
    tuesday: CalendarDay
    wednesday: CalendarDay
    thursday: CalendarDay
    friday: CalendarDay
    saturday: CalendarDay
    sunday: CalendarDay
    start_date: str
    end_date: str


@dataclass
class CalendarDate:
    service_id: int
    date: str
    exception_type: CalendarException
    holiday_name: str  # gtfs-exp


@dataclass
class FareAttribute:
    fare_id: str
    price: float
    currency_types: str
    payment_method: PaymentMethod
    transfers: Transfers
    agency_id: str
    transfer_duration: int


@dataclass
class FareRule:
    fare_id: str
    route_id: Optional[str] = None
    origin_id: Optional[str] = None
    destination_id: Optional[str] = None
    contains_id: Optional[str] = None


@dataclass
class Shape:
    shape_id: str
    shape_pt_lat: str
    shape_pt_lon: str
    shape_pt_sequence: int
    shape_dist_traveled: Optional[float] = None


@dataclass
class Frequency:
    trip_id: str
    start_time: str
    end_time: str
    headway_secs: int
    exact_times: Optional[Exactness] = None


@dataclass
class Transfer:
    from_stop_id: str
    to_stop_id: str
    transfer_type: TransferType
    min_transfer_time: Optional[int]

    min_walk_time: Optional[int] = None  # gtfs-exp
    min_wheelchair_time: Optional[int] = None  # gtfs-exp
    suggested_buffer_time: Optional[int] = None  # gtfs-exp
    wheelchair_transfer: Optional[AccessibilityEnum] = None  # gtfs-exp
    from_trip_id: Optional[str] = None  # gtfs-exp
    to_trip_id: Optional[str] = None  # gtfs-exp


@dataclass
class Pathway:
    pathway_id: str
    from_stop_id: str
    to_stop_id: str
    pathway_mode: PathwayMode
    is_bidirectional: BiDirectionality

    length: Optional[float] = None
    traversal_time: Optional[int] = None
    stair_count: Optional[int] = None
    max_slope: Optional[float] = None
    min_width: Optional[float] = None
    signposted_as: Optional[str] = None
    reverse_signposted_as: Optional[str] = None

    facility_id: Optional[str] = None  # gtfs-exp
    wheelchair_length: Optional[int] = None  # gtfs-exp
    wheelchair_traversal_time: Optional[int] = None  # gtfs-exp
    pathway_name: Optional[str] = None  # gtfs-exp
    pathway_code: Optional[str] = None  # gtfs-exp
    instructions: Optional[str] = None  # gtfs-exp


@dataclass
class Level:
    level_id: str
    level_index: float
    level_name: Optional[str] = None
    level_elevation: Optional[str] = None


@dataclass
class FeedInfo:
    feed_publisher_name: str
    feed_publisher_url: str
    feed_lang: str
    default_lang: Optional[str] = None
    feed_start_date: Optional[str] = None
    feed_end_date: Optional[str] = None
    feed_version: Optional[str] = None
    feed_contact_email: Optional[str] = None
    feed_contact_url: Optional[str] = None


@dataclass
class Translation:
    table_name: TableName
    field_name: str
    language: str
    translation: str
    record_id: Optional[str] = None
    record_sub_id: Optional[str] = None
    field_value: Optional[str] = None


@dataclass
class Attribution:
    organization_name: str

    attribution_id: Optional[str] = None
    agency_id: Optional[str] = None
    route_id: Optional[str] = None
    trip_id: Optional[str] = None
    is_producer: Optional[YesNo] = None
    is_operator: Optional[YesNo] = None
    is_authority: Optional[YesNo] = None

    attribution_url: Optional[str] = None
    attribution_email: Optional[str] = None
    attribution_phone: Optional[str] = None
