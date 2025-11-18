import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse
from src.core.config import config


class RateLimiter:
    def __init__(self):
        self.global_limit = config.GLOBAL_RATE_LIMIT
        self.domain_limit = config.DOMAIN_RATE_LIMIT
        self.last_global_request = 0.0
        self.last_domain_request = defaultdict(float)
        self.lock = asyncio.Lock()

    async def acquire(self, url: str):
        domain = urlparse(url).netloc
        sleep_time = 0.0

        async with self.lock:
            now = time.time()

            # Global Rate Limit
            time_since_global = now - self.last_global_request
            if time_since_global < (1.0 / self.global_limit):
                sleep_time = max(
                    sleep_time, (1.0 / self.global_limit) - time_since_global
                )

            # Domain Rate Limit
            time_since_domain = now - self.last_domain_request[domain]
            if time_since_domain < (1.0 / self.domain_limit):
                sleep_time = max(
                    sleep_time, (1.0 / self.domain_limit) - time_since_domain
                )

            # Reserve the slot by updating times assuming we sleep
            # This is a slight approximation but prevents race conditions
            # effectively "booking" the time slot
            self.last_global_request = now + sleep_time
            self.last_domain_request[domain] = now + sleep_time

        # Sleep outside the lock
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
