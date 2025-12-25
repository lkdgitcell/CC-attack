"""HTTP request builder with randomization and caching."""

import random
import secrets
from functools import lru_cache
from typing import Dict, Optional
from urllib.parse import urlparse, urlencode

from src.models import AttackMode
from src.config import USER_AGENTS, ACCEPT_HEADERS, ACCEPT_LANGUAGE, ACCEPT_ENCODING, REFERERS


@lru_cache(maxsize=1000)
def _get_cached_user_agent(seed: int, browser: str) -> str:
    """Cache user-agent generation for performance."""
    random.seed(seed)
    ua_list = USER_AGENTS.get(browser, USER_AGENTS["chrome"])
    return random.choice(ua_list)


class RequestBuilder:
    """Build HTTP requests with randomized headers and efficient caching."""

    def __init__(
        self,
        target_url: str,
        mode: AttackMode = AttackMode.GET,
        custom_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        post_data: Optional[str] = None,
    ):
        self.target_url = target_url
        self.mode = mode
        self.custom_headers = custom_headers or {}
        self.cookies = cookies or {}
        self.post_data = post_data

        parsed = urlparse(target_url)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.path = parsed.path or "/"
        self.query = parsed.query

    def build_headers(self, randomize: bool = True) -> Dict[str, str]:
        headers = {
            "Host": self.host,
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
        }

        if randomize:
            seed = random.randint(0, 1000000)
            browser = random.choice(list(USER_AGENTS.keys()))
            headers["User-Agent"] = _get_cached_user_agent(seed, browser)
            headers["Accept"] = random.choice(ACCEPT_HEADERS)
            headers["Accept-Language"] = random.choice(ACCEPT_LANGUAGE)
            headers["Accept-Encoding"] = random.choice(ACCEPT_ENCODING)

            if random.random() > 0.3:
                headers["Referer"] = random.choice(REFERERS)
        else:
            headers["User-Agent"] = USER_AGENTS["chrome"][0]
            headers["Accept"] = ACCEPT_HEADERS[0]
            headers["Accept-Language"] = ACCEPT_LANGUAGE[0]
            headers["Accept-Encoding"] = ACCEPT_ENCODING[0]

        headers.update(self.custom_headers)

        if self.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            headers["Cookie"] = cookie_str

        if self.mode == AttackMode.POST:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            if self.post_data:
                headers["Content-Length"] = str(len(self.post_data))

        return headers

    def build_url(self, add_random_param: bool = True) -> str:
        url = f"{self.scheme}://{self.host}{self.path}"

        if add_random_param:
            separator = "&" if self.query else "?"
            random_value = secrets.token_hex(8)
            url += f"{separator if self.query else '?'}"
            if self.query:
                url += f"{self.query}&"
            url += f"_={random_value}"
        elif self.query:
            url += f"?{self.query}"

        return url

    def build_post_data(self, randomize: bool = True) -> Optional[str]:
        if self.mode != AttackMode.POST:
            return None

        if self.post_data:
            return self.post_data

        if randomize:
            num_fields = random.randint(3, 8)
            data = {}
            for i in range(num_fields):
                key = f"field_{i}"
                value = secrets.token_urlsafe(random.randint(8, 32))
                data[key] = value

            return urlencode(data)

        return None

    def build_request_kwargs(self, randomize: bool = True) -> Dict:
        kwargs = {
            "headers": self.build_headers(randomize=randomize),
            "timeout": 10,
            "allow_redirects": False,
        }

        kwargs["url"] = self.build_url(add_random_param=randomize)

        if self.mode == AttackMode.POST:
            data = self.build_post_data(randomize=randomize)
            if data:
                kwargs["data"] = data

        return kwargs

    def get_method(self) -> str:
        method_map = {
            AttackMode.GET: "GET",
            AttackMode.POST: "POST",
            AttackMode.HEAD: "HEAD",
            AttackMode.HTTP2: "GET",
        }
        return method_map.get(self.mode, "GET")

    @staticmethod
    def generate_random_string(length: int = 16) -> str:
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_random_bytes(size: int = 1024) -> bytes:
        return secrets.token_bytes(size)
