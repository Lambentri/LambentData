from dataclasses import dataclass
from typing import Dict, Union, List

from autobahn import wamp
from autobahn.twisted import ApplicationSession
from autobahn.twisted.component import Component
from autobahn.twisted.component import run
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

from compat import LAMachineCompatMixin, CompatConfig
from config import NAMESPACE_PREFIX

ns = "LA4-DATA-GBFS"
GBFS_PREFIX = NAMESPACE_PREFIX + "gbfs."


@dataclass
class SomeConfig:
    pass


@dataclass
class SomeResult:
    pass


class GBFSSession(LAMachineCompatMixin, ApplicationSession):
    cconfig = CompatConfig(
        machine_name=ns,
        desc_blurb="A GBFS Provider"
    )

    configs: Dict[str, SomeConfig] = {}
    results: Union[Dict[str, SomeResult], Dict[str, List[SomeResult]]] = {}

    @wamp.register(GBFS_PREFIX + "register")
    def register_config(self):
        pass

    @wamp.register(GBFS_PREFIX + "register")
    def remove_config(self):
        pass

    def update_data(self):
        raise NotImplementedError("Need to configure a data update")

    def herald_data(self):
        raise NotImplementedError("Need to configure a data herald")

    @inlineCallbacks
    def onJoin(self, details):
        self.log.info("session ready")
        self.regs = yield self.register(self)
        self.subs = yield self.subscribe(self)

        self.ticker_ex = LoopingCall(self.update_data)
        self.ticker_ex.start(1800)  # 30m

        self.herald_ex = LoopingCall(self.herald_data)
        self.herald_exs.start(10)


comp = Component(
    transports=u"ws://localhost:8083/ws",
    realm=u"realm1",
    session_factory=GBFSSession
)
if __name__ == "__main__":
    run([comp], log_level="info")
