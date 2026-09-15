import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

logger = structlog.stdlib.get_logger(__name__)


@dataclass
class HostPacer:
    min_seconds_between_requests: float
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    last_request_at_by_host: dict[str, float] = field(default_factory=dict)

    def wait_for_host(self, host: str) -> None:
        last_request_at = self.last_request_at_by_host.get(host, -math.inf)
        wait_seconds = max(0.0, last_request_at + self.min_seconds_between_requests - self.clock())
        if wait_seconds > 0:
            logger.info("request_paced", host=host, wait_seconds=wait_seconds)
            self.sleep(wait_seconds)
        self.last_request_at_by_host[host] = self.clock()
