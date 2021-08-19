import dataclasses
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional

from autobahn import wamp
from autobahn.wamp import RegisterOptions
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

logger = logging.Logger("LA4-COMPAT")

SRC_PREFIX = "com.lambentri.edge.la4.machine.link.src."
LEDS_IN_ARRAY_DEFAULT = 300


# the Machine Structure
class RunningEnum(Enum):
    RUNNING = "RUNNING"
    NOTRUNNING = "NOTRUNNING"


class SpeedEnum(Enum):
    HUNDREDTHS = .01
    FHUNDREDTHS = .05
    TENTHS = .1
    FTENTHS = .5
    ONES = 1
    TWOS = 2
    FIVES = 5
    TENS = 10
    TWENTYS = 20
    THIRTHYS = 30
    MINS = 60


class BrightnessEnum(Enum):
    FULL = 255
    HALF = 127
    QUARTER = 63
    EIGHTH = 31
    SIXTEENTH = 15
    THIRTY2ND = 7
    SIXTYFOURTH = 3
    OFF = 0


class Machine(BaseModel):
    name: str
    iname: str

    id: str
    desc: str

    speed: str = "FHUNDREDTHS"
    running: RunningEnum = RunningEnum.RUNNING

    class Config:
        use_enum_names = True


@dataclass
class MachineDict:
    machines: Dict[str, Machine]
    speed_enum: Dict[str, float] = dataclasses.field(default_factory=lambda: {"TENTHS": .1})


## Compat config work
@dataclass
class CompatConfig:
    machine_name: str  # use the namespace logger declaration
    # prefix: str #
    config_field: str = "configs"
    result_field: str = "results"
    machine_iname_field: str = "name"  # lazy
    desc_blurb: str = "A LA4 Data Machine Outputting Data"

    machine_subkey_field: Optional[str] = None  # for lists-of-dicts
    speed_enum: SpeedEnum = SpeedEnum.ONES


class LAMachineCompatMixin:
    cconfig: CompatConfig
    brightness_tgt = BrightnessEnum(3)
    brightness_act = 255

    # classes to provide similar machine data that our clients expect
    @wamp.register("com.lambentri.edge.la4.machine.list", options=RegisterOptions(invoke="roundrobin"))
    def machine_schema(self):
        if not self.cconfig:
            raise Exception("CompatConfig must be added to subclasses for LA4 Autocompat")

        res_field: Dict[str, Any] = getattr(self, self.cconfig.result_field)
        schemas = {}
        for key, d in res_field.items():
            if isinstance(d, list):
                for m in d:  # this is fucked, fix it.
                    schemas[f"{key}-{getattr(m, str(self.cconfig.machine_subkey_field))}"] = Machine(
                        name=self.cconfig.machine_name,
                        iname=f"{key.title()}-{str(getattr(m, self.cconfig.machine_iname_field)).upper()}",
                        id=self.cconfig.machine_name.lower() + f"-{key}-" + str(
                            getattr(m, self.cconfig.machine_iname_field)).lower(),
                        desc=self.cconfig.desc_blurb,
                        speed=self.cconfig.speed_enum.name
                    )

            if isinstance(d, dict):
                working = {
                    key: Machine(
                        name=self.cconfig.machine_name,
                        iname=key.title(),
                        id=self.cconfig.machine_name.lower() + f"-{key}-" + str(
                            getattr(d, self.cconfig.machine_iname_field)).lower(),
                        desc=self.cconfig.desc_blurb,
                        speed=self.cconfig.speed_enum.name
                    ) for i, d in res_field.items()
                }

                schemas.update(working)

        schema = MachineDict(
            machines=schemas,
            speed_enum={self.cconfig.speed_enum.name: self.cconfig.speed_enum.value}
        )
        serialized = json.loads(json.dumps(schema, indent=4, default=pydantic_encoder))
        return serialized

    def __init__(self, config=None):
        super().__init__(config)

        self.brightness_ticker = LoopingCall(self.ticker_brightness_ctrl)
        self.brightness_ticker.start(.1)

    def ticker_brightness_ctrl(self):
        if self.brightness_act != self.brightness_tgt.value:
            if self.brightness_act < self.brightness_tgt.value:
                self.brightness_act += 1
            else:
                self.brightness_act -= 1

    def run_brightness_on_val(self, val):
        if self.brightness_act == 0:
            res = [0] * len(val)
        elif self.brightness_act != 255:
            res = [int(i * self.brightness_act / 255.) for i in val]
        else:
            res = val

        return res

    # brightness control (todo, rework this overall interface)
    @inlineCallbacks
    def global_brightness_publish(self):
        yield self.publish("com.lambentri.edge.la4.machine.gb", brightness=self.brightness_tgt.value)

    @wamp.register("com.lambentri.edge.la4.machine.gb.up", options=RegisterOptions())
    def global_brightness_value_up(self):
        """Move the global brightness up a single tick"""
        self.brightness_tgt = self.brightness_tgt.next_up(self.brightness_tgt)
        self.global_brightness_publish()
        return {"brightness": self.brightness_tgt.value}

    @wamp.register("com.lambentri.edge.la4.machine.gb.dn")
    def global_brightness_value_dn(self):
        """Move the global brightness down a single tick"""
        self.brightness_tgt = self.brightness_tgt.next_dn(self.brightness_tgt)
        self.global_brightness_publish()
        return {"brightness": self.brightness_tgt.value}

    @wamp.register("com.lambentri.edge.la4.machine.gb.set")
    def global_brightness_value_set(self, value: int):
        """Set the global brightness"""
        self.brightness_tgt = BrightnessEnum(value)
        self.global_brightness_publish()
        return {"brightness": self.brightness_tgt.value}

    @wamp.register("com.lambentri.edge.la4.machine.gb.get")
    def global_brightness_value_get(self):
        """get the global brightness"""
        return {"brightness": self.brightness_tgt.value}
