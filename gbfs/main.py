from typing import Dict, Union, List, Optional

from autobahn import wamp
from autobahn.twisted import ApplicationSession
from autobahn.twisted.component import Component
from autobahn.twisted.component import run
from pydantic import BaseModel, Field
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall
from twisted.web._newclient import Response

from compat import LAMachineCompatMixin, CompatConfig, Machine
from config import NAMESPACE_PREFIX
from gbfs.models import GBFSIndex, GBFSSystemInformation, feed_to_parser, GBFSStationInformation, GBFSStationStatus, \
    GBFSFreeBikeStatus, GBFSSystemHours, GBFSSystemCalendar, GBFSSystemRegion, GBFSSystemAlerts, GBFSFeedName

ns = "LA4-DATA-GBFS"
GBFS_PREFIX = NAMESPACE_PREFIX + "gbfs."


class GBFSConfig(BaseModel):
    id: str  # bluebikes
    name: str  # BlueBikes
    url: str
    stations: List[str] = Field(default_factory=list)
    language: str = "en"

    gbfs_ttl_data_days: int = 1
    gbfs_ttl_stations_seconds: int = 300


class GBFSResult(BaseModel):
    config: GBFSConfig
    index: GBFSIndex
    system_information: Optional[GBFSSystemInformation]
    station_information: Optional[GBFSStationInformation]
    station_status: Optional[GBFSStationStatus]
    free_bike_status: Optional[GBFSFreeBikeStatus]
    system_hours: Optional[GBFSSystemHours]
    system_calendar: Optional[GBFSSystemCalendar]
    system_regions: Optional[GBFSSystemRegion]
    system_alerts: Optional[GBFSSystemAlerts]

    def _nice_names(self, station_id):
        return "".join(self.station_information.by_id(station_id).name.split(' ')[0:2])

    def complex_machines(self, cconfig: CompatConfig) -> Dict[str, Machine]:
        if not self.station_information:
            return {}
        if len(cconfig.smears) == 1:
            # F for fill, will add other ones
            return {id: Machine(
                name=ns,
                iname=f"{self.config.name}-{self._nice_names(id)}-F",
                id=f"{ns}-{self.config.id}-{id}".lower(),
                desc=f"Bike Count for Station {id} (fill)",
                speed=cconfig.speed_enum.name
            ) for id in self.config.stations}
        else:
            ret = {}
            for smear in cconfig.smears:
                ret.update(**{f"{id}-{smear}": Machine(
                    name=ns,
                    iname=f"{self.config.name}-{self._nice_names(id)}-F-S{smear}",
                    id=f"{ns}-{self.config.id}-{id}-F-S{smear}".lower(),
                    desc=f"Bike Count for Station {id} (fill-smear-{smear})",
                    speed=cconfig.speed_enum.name
                ) for id in self.config.stations})
            return ret


class GBFSSession(LAMachineCompatMixin, ApplicationSession):
    cconfig = CompatConfig(
        machine_name=ns,
        desc_blurb="A GBFS Provider",
        smears=[1, 8]
    )

    configs: Dict[str, GBFSConfig] = {
        "bluebikes": GBFSConfig(
            id="bluebikes",
            name="BlueBikes",
            url="https://gbfs.bluebikes.com/gbfs/gbfs.json",
            stations=["S32011", "M32001"],
        )
    }
    results: Union[Dict[str, GBFSResult], Dict[str, List[GBFSResult]]] = {}

    @wamp.register(GBFS_PREFIX + "register")
    def register_config(self):
        pass

    @wamp.register(GBFS_PREFIX + "remove")
    def remove_config(self):
        pass

    def update_data(self):
        uninstantiated_results = set(self.configs.keys()) - set(self.results.keys())
        other_results = set(self.configs.keys()) - uninstantiated_results
        for ur in uninstantiated_results:
            self.log.info(f"Updating {ur} (1st)")
            self.do_update(ur)

        # for k in other_results:
        #     # Check if the TTL is old here
        #     self.log.info(f"Updating {k}")
        #     self.do_update(k)
        #
        for k in other_results:
            self.log.info(f"Updating {k} stations")
            self.do_station_update(k)

    def herald_data(self):
        pass

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info("session ready")
        self.regs = yield self.register(self)
        self.subs = yield self.subscribe(self)

        self.ticker_up = LoopingCall(self.update_data)
        self.ticker_up.start(300)  # 5m

        self.herald_up = LoopingCall(self.herald_data)
        self.herald_up.start(10)

    @inlineCallbacks
    def do_update(self, config_id):
        try:
            config = self.configs[config_id]

            response: Response = yield self.retrieve_url(config.url)
            if response:
                json = yield response.json()
                index = GBFSIndex(**json)
                if config.language not in index.data:
                    self.log.info(
                        f"The configured language '{config.language}' was not found in the GBFS index {config.url}. Found {index.data.keys()}")
                    return

                curr_feeds = index.data.get(config.language)['feeds']
                if config_id not in self.results:
                    self.results[config_id] = GBFSResult(index=index, config=config)

                for entry in curr_feeds:
                    entry_response: Response = yield self.retrieve_url(entry.url)
                    entry_json = yield entry_response.json()
                    entry_obj = feed_to_parser[entry.name.value](**entry_json)
                    setattr(self.results[config_id], entry.name.value, entry_obj)

        except Exception as e:
            import traceback
            self.log.error(traceback.format_exc())

    def do_station_update(self, config_id):
        config = self.configs[config_id]
        station_feeds = self.results[config_id].index.data.get(config.language)['feeds'][
            GBFSFeedName.STATION_INFORMATION.value]
        entry_response: Response = yield self.retrieve_url(station_feeds.url)
        entry_json = yield entry_response.json()
        self.results[config_id].station_status = GBFSStationStatus(**entry_json)


comp = Component(
    transports=u"ws://localhost:8083/ws",
    realm=u"realm1",
    session_factory=GBFSSession
)
if __name__ == "__main__":
    run([comp], log_level="info")
