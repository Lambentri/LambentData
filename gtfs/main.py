import csv
import datetime
import os
import zipfile
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import pytz
import treq
from aenum import Enum
from autobahn import wamp
from autobahn.twisted import ApplicationSession
from autobahn.twisted.component import Component
from autobahn.twisted.component import run
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from twisted.web._newclient import Response

import models
from config import NAMESPACE_PREFIX

GTFS_PREFIX = NAMESPACE_PREFIX + "gtfs."
ns = "LA4-DATA-GTFS"


class GTFSParsers(Enum):
    # map files to Parsers
    agency = models.Agency
    stops = models.Stop
    routes = models.Route
    trips = models.Trip
    stop_times = models.StopTime
    calendar = models.Calendar
    calendar_dates = models.CalendarDate
    fare_attributes = models.FareAttribute
    fare_rules = models.FareRule
    shapes = models.Shape
    frequencies = models.Frequency
    transfers = models.Transfer
    pathways = models.Pathway
    levels = models.Level
    feed_info = models.FeedInfo
    translations = models.Translation
    attributions = models.Attribution


class GTFSRTEnum(Enum):
    TRIP_UPDATES = "TripUpdates"
    SERVICE_ALERTS = "ServiceAlerts"
    VEHICLE_POSITIONS = "VehiclePositions"


@dataclass
class GTFSResults:
    timestamp: datetime.datetime
    agency: List[models.Agency]
    stops: List[models.Stop]
    routes: List[models.Route]
    trips: List[models.Trip]
    stop_times: List[models.StopTime]
    calendar: Optional[List[models.Calendar]] = None
    calendar_dates: Optional[List[models.CalendarDate]] = None
    fare_attributes: Optional[List[models.FareAttribute]] = None
    fare_rules: Optional[List[models.FareRule]] = None
    shapes: Optional[List[models.Shape]] = None
    frequencies: Optional[List[models.Frequency]] = None
    transfers: Optional[List[models.Transfer]] = None
    pathways: Optional[List[models.Pathway]] = None
    levels: Optional[List[models.Level]] = None
    feed_info: Optional[List[models.FeedInfo]] = None
    translations: Optional[List[models.Translation]] = None
    attributions: Optional[List[models.Attribution]] = None

    # utilities
    def _get_stop_by_id(self, id: str) -> Optional[models.Stop]:
        return next(iter([i for i in self.stops if i.stop_id == id]))

    def _get_stop_times_by_id(self, id: str) -> List[models.StopTime]:
        return [i for i in self.stop_times if i.stop_id == id]

    def _get_trips_by_id(self, id: List[str]) -> Dict[str, models.Trip]:
        return {i.trip_id:i for i in self.trips if i.trip_id in id}

    def _filter_to_find_closest_times(self, stop_times: List[models.StopTime], start: datetime.datetime, end: datetime.datetime, end_of_service_hour: int = 2) -> List[models.StopTime]:
        startstr = start.strftime("%H:%M:%S")
        endstr = end.strftime("%H:%M:%S")

        if start.hour <= end_of_service_hour: # handle the dumb 24h logic in gtfs
            startstr = str(int(startstr[0:2]) + 24) + startstr[2:]
        if end.hour <= end_of_service_hour:
            endstr = str(int(endstr[0:2]) + 24) + endstr[2:]

        things_coming_up = [i for i in stop_times if i.arrival_time > startstr ]
        things_within_bounds = [i for i in things_coming_up if i.arrival_time < endstr ]

        # print(things_within_bounds)
        # print([i.arrival_time for i in things_within_bounds])
        return things_within_bounds

    # high level
    def get_next_schedules_for_stop(self, id: str, tz: str = "America/New_York", minutes: int = 15):
        now = datetime.datetime.now(tz=pytz.timezone(tz))
        fut = now + datetime.timedelta(minutes=15)

        stop_times = self._get_stop_times_by_id(id)
        nearby_times = self._filter_to_find_closest_times(stop_times, now, fut)
        trips = self._get_trips_by_id([i.trip_id for i in nearby_times])
        self.log.info("Upcoming")
        for t in sorted(nearby_times, key=lambda x:x.arrival_time):
            self.log.info(
                f"Line {trips[t.trip_id].route_id} Arrives at {t.arrival_time} {t.arrival_time_as_delta_seconds(now)} ")



@dataclass
class GTFSConfig:
    name: str
    gtfs_url: str
    transit_system_tz: str  # America/New_York etc, can make a cheeky enum

    relevant_stops: List[str] = field(default_factory=list)
    gtfsrt_urls: Dict[GTFSRTEnum, str] = field(default_factory=dict)

    gtfs_ttl_days: int = 1
    gtfsrt_ttl_seconds: int = 300


class GTFSSession(ApplicationSession):
    # gtfs_configs: Dict[str, GTFSConfig] = field(default_factory=list)
    # burned in since I don't have any UI built, we're heralding the teele square stop
    gtfs_configs: Dict[str, GTFSConfig] = {"mbta": GTFSConfig(
        name="MBTA",
        gtfs_url="https://cdn.mbta.com/MBTA_GTFS.zip",
        transit_system_tz="America/New_York",
        relevant_stops=["2634"]
    )}

    gtfs_results: Dict[str, GTFSResults] = {}

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info("session ready")
        self.regs = yield self.register(self)
        self.subs = yield self.subscribe(self)

        self.ticker_gtfs = LoopingCall(self.ticker_update_gtfs)
        self.ticker_gtfs.start(60)

        self.herald_stfs = LoopingCall(self.gtfs_herald)
        self.herald_stfs.start(10)

        # self.ticker_gtfs_rt = LoopingCall(self.ticker_update_gtfs_rt)
        # self.ticker_gtfs_rt.start(10)

    @wamp.register(GTFS_PREFIX + "register")
    def register_config(self):
        pass

    @wamp.register(GTFS_PREFIX + "register")
    def remove_config(self):
        pass

    @wamp.register(GTFS_PREFIX + "assert_url")
    @inlineCallbacks
    def assert_url(self, url: str) -> bool:
        response: Response = yield treq.get(url)
        return response.code in [200, 201, 202]

    def assert_directory_structure(self, config_id: str):
        if not os.path.isdir("cache"):
            os.mkdir("cache")
        if not os.path.isdir(f"cache/{config_id}"):
            os.mkdir(f"cache/{config_id}")
        if not os.path.isdir(f"cache/{config_id}/bundle"):
            os.mkdir(f"cache/{config_id}/bundle")

    @inlineCallbacks
    def retrieve_url(self, url: str, kwargs: Dict[str, Any] = {}) -> Optional[Response]:
        response: Response = yield treq.get(url, **kwargs)
        if response.code in [200, 201, 202]:
            return response

    @inlineCallbacks
    def download_and_write(self, config_id: str) -> bool:
        config = self.gtfs_configs[config_id]
        bundle = yield self.retrieve_url(config.gtfs_url, kwargs={"unbuffered": True})
        if bundle:
            destination = open(f"cache/{config_id}/bundle.zip", 'wb')
            yield treq.collect(bundle, destination.write)
            destination.close()

    def unzip_bundle(self, config_id: str):
        with zipfile.ZipFile(f"cache/{config_id}/bundle.zip", 'r') as zip:
            zip.extractall(f"cache/{config_id}/bundle")
        # print(os.listdir(f"cache/{config_id}/bundle"))

    def parse_bundle(self, config_id: str):
        try:
            kwargs = {"timestamp": datetime.datetime.now()}
            for file in os.listdir(f"cache/{config_id}/bundle"):
                file_pre = file.replace('.txt', '')
                if file_pre not in [i.name for i in GTFSParsers]:
                    self.log.info(f"{file_pre} was not found in our parser list, may be a gtfs+/experimental entity")
                    continue
                kwargs[file_pre] = []
                with open(f"cache/{config_id}/bundle/{file}", 'r') as file_handle:
                    csvreader = list(csv.reader(file_handle))
                    header = csvreader[0]
                    for row in csvreader[1:]:
                        kwargs[file_pre].append(getattr(GTFSParsers, file_pre).value(**dict(zip(header, row))))

            self.gtfs_results[config_id] = GTFSResults(**kwargs)
            self.log.info(f"Completed Ingesting {config_id}")

        except Exception as e:
            self.log.error(e)

    @inlineCallbacks
    def do_update(self, config_id: str):
        self.log.info(f"Updating {config_id}")
        self.assert_directory_structure(config_id)
        yield self.download_and_write(config_id)
        self.unzip_bundle(config_id)
        self.parse_bundle(config_id)

    def ticker_update_gtfs(self):
        uninstantiated_results = set(self.gtfs_configs.keys()) - set(self.gtfs_results.keys())
        for ur in uninstantiated_results:
            self.do_update(ur)

        # todo handle configs being removed

    def ticker_update_gtfs_rt(self):
        pass

    def gtfs_herald(self):
        """ Herald line data (wip)"""
        try:
            for i in self.gtfs_results:
                config = self.gtfs_configs[i]
                for stop in config.relevant_stops:
                    self.log.debug(f"heralding {i} - {stop}")
                    self.gtfs_results[i].get_next_schedules_for_stop(stop)
            if not self.gtfs_results:
                self.log.info("Herald: No data has been loaded, chilling")
        except Exception as e:
            import traceback
            self.log.error(e)
            self.log.error(traceback.format_exc())

comp = Component(
    transports=u"ws://localhost:8083/ws",
    realm=u"realm1",
    session_factory=GTFSSession
)

if __name__ == "__main__":
    run([comp])
