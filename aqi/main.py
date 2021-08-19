import datetime
from typing import Dict, List

import treq
from autobahn import wamp
from autobahn.twisted import ApplicationSession
from autobahn.twisted.component import Component
from autobahn.twisted.component import run
from autobahn.wamp import PublishOptions
from pydantic import BaseModel
from pydantic.dataclasses import dataclass, Field
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

from aqi.models import AirNowObservation, observation_color_map
from compat import LAMachineCompatMixin, CompatConfig, SRC_PREFIX, LEDS_IN_ARRAY_DEFAULT
from config import NAMESPACE_PREFIX

API_KEY = "53295F0D-285C-4787-8336-4DA76A434E03"

ns = "LA4-DATA-AQI"

AQI_PREFIX = NAMESPACE_PREFIX + "aqi."


@dataclass
class AQIConfig:
    name: str
    zip_code: str
    api_key: str
    distance: int = 25

    def as_obs_request(self):
        return AQIObservationRequestParams(
            zip_code=self.zip_code,
            distance=self.distance,
            api_key=self.api_key,
        )


class AQIObservationRequestParams(BaseModel):
    zipCode: str = Field(alias="zip_code")
    format: str = "application/json"  #
    distance: int = 25
    API_KEY: str = Field(alias="api_key")


class AQIForecastRequestParams(BaseModel):
    date: datetime.date

    zipCode: str = Field(alias="zip_code")
    format: str = "application/json"  #
    distance: int = 25
    API_KEY: str = Field(alias="api_key")


class AQISession(LAMachineCompatMixin, ApplicationSession):
    PATH_HOST = "https://www.airnowapi.org"
    PATH_OBSERVATIONS = PATH_HOST + "/aq/observation/zipCode/current/"
    PATH_FORECAST = PATH_HOST + "/aq/forecast/zipCode/"

    cconfig = CompatConfig(
        machine_name=ns,
        config_field="aqi_configs",
        result_field="aqi_results",
        desc_blurb="Machine presenting AQI",
        machine_iname_field="param_name",
        machine_subkey_field="param_name"
    )

    aqi_configs = {
        "boston": AQIConfig(
            name="Boston, MA",
            zip_code="02144",
            api_key=API_KEY,
        ),
        "denver": AQIConfig(
            name="Denver, CO",
            zip_code="80014",
            api_key=API_KEY,
        ),
        "spokane": AQIConfig(
            name="Spokane, WA",
            zip_code="99201",
            api_key=API_KEY,
        ),
        "houston": AQIConfig(
            name="Houston, TX",
            zip_code="77030",
            api_key=API_KEY,
        ),
        "sanfran": AQIConfig(
            name="San Francisco, CA",
            zip_code="94016",
            api_key=API_KEY,
        )
    }

    aqi_results: Dict[str, List[AirNowObservation]] = {}

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info("session ready")
        self.regs = yield self.register(self)
        self.subs = yield self.subscribe(self)

        self.ticker_aqi = LoopingCall(self.ticker_update_aqi)
        self.ticker_aqi.start(1800)  # 30m

        self.herald_aqi = LoopingCall(self.aqi_herald)
        self.herald_aqi.start(.05)
        self.log.info("completed startup")

    @wamp.register(AQI_PREFIX + "register")
    def register_config(self):
        pass

    @wamp.register(AQI_PREFIX + "register")
    def remove_config(self):
        pass

    @inlineCallbacks
    def aqi_herald(self):
        """Herald AQI Data (WIP)"""
        """ Herald line data (wip)"""
        options = PublishOptions(retain=True)
        for key, res_list in self.aqi_results.items():
            for res in res_list:
                id = f"{self.cconfig.machine_name.lower()}-{key}-{str(res.param_name).lower()}"
                yield self.publish(f"{SRC_PREFIX}{id}",
                                   self.run_brightness_on_val(
                                       observation_color_map[res.category.number] * LEDS_IN_ARRAY_DEFAULT),
                                   id=id, options=options)
        if not self.aqi_results:
            self.log.info("Herald: No data has been loaded, chilling")

    @inlineCallbacks
    def do_update_aqi(self, config_id: str):
        try:
            config = self.aqi_configs[config_id]

            result = yield treq.get(self.PATH_OBSERVATIONS, params=config.as_obs_request().dict())
            data = yield result.json()
            # pls forgive the fucking federal govt
            for i in data:
                i['DateObserved'] = i['DateObserved'].replace(" ", "")
            self.aqi_results[config_id] = [AirNowObservation(**i) for i in data]
        except Exception as e:
            import traceback
            self.log.error(e)
            self.log.error(traceback.format_exc())

    def ticker_update_aqi(self):
        uninstantiated_results = set(self.aqi_configs.keys()) - set(self.aqi_results.keys())
        other_results = set(self.aqi_configs.keys()) - uninstantiated_results
        for ur in uninstantiated_results:
            self.log.info(f"Updating {ur} (1st)")
            self.do_update_aqi(ur)

        for k in other_results:
            self.log.info(f"Updating {ur}")
            self.do_update_aqi(k)


comp = Component(
    transports=u"ws://localhost:8083/ws",
    realm=u"realm1",
    session_factory=AQISession
)
if __name__ == "__main__":
    run([comp], log_level="info")
