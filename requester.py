#!/usr/bin/env python3
"""
HTTP requester with retries, rate limiting, and proxy support.
"""

import asyncio
import aiohttp
import random
from typing import Optional, Dict
from aiohttp import ClientTimeout, ClientError, TCPConnector

# A small but effective list of User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

class Requester:
    """
    Manages HTTP requests with retries, rate limiting, and custom headers.
    """

    def __init__(self,
                 timeout: int = 10,
                 proxy: Optional[str] = None,
                 headers: Optional[Dict] = None,
                 user_agent: Optional[str] = None,
                 random_agent: bool = False,
                 follow_redirects: bool = False,
                 max_retries: int = 3,
                 rate_limit: Optional[int] = None,
                 delay: float = 0.0):
        self.timeout = ClientTimeout(total=timeout)
        self.proxy = proxy
        self.base_headers = headers or {}
        self.user_agent = user_agent
        self.random_agent = random_agent
        self.follow_redirects = follow_redirects
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.delay = delay
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0

    async def __aenter__(self):
        connector = TCPConnector(limit_per_host=0)  # no limit per host
        if self.proxy:
            try:
                from aiohttp_socks import ProxyConnector
                connector = ProxyConnector.from_url(self.proxy)
            except ImportError:
                print("⚠️  aiohttp-socks not installed. Install with: pip install aiohttp-socks")
        self._session = aiohttp.ClientSession(connector=connector, timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    def _get_headers(self) -> Dict:
        headers = self.base_headers.copy()
        if self.random_agent:
            headers['User-Agent'] = random.choice(USER_AGENTS)
        elif self.user_agent:
            headers['User-Agent'] = self.user_agent
        else:
            headers['User-Agent'] = USER_AGENTS[0]
        # Add common headers to appear more like a browser
        headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        headers.setdefault('Accept-Language', 'en-US,en;q=0.5')
        headers.setdefault('Connection', 'keep-alive')
        return headers

    async def _enforce_rate_limit(self):
        """Simple rate limiting using delays."""
        if self.rate_limit:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        if self.delay > 0:
            await asyncio.sleep(self.delay)

    async def request(self, method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """
        Perform an HTTP request with retries and rate limiting.
        Returns the response object or None on failure.
        """
        headers = self._get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        allow_redirects = kwargs.pop('allow_redirects', self.follow_redirects)

        for attempt in range(self.max_retries + 1):
            try:
                await self._enforce_rate_limit()
                async with self._session.request(
                    method, url,
                    headers=headers,
                    allow_redirects=allow_redirects,
                    **kwargs
                ) as resp:
                    # Read response to allow connection reuse
                    await resp.read()
                    self._last_request_time = asyncio.get_event_loop().time()
                    return resp
            except (ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries:
                    return None
                # Exponential backoff with jitter
                wait = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait)
            except Exception:
                if attempt == self.max_retries:
                    return None
                wait = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait)
        return None