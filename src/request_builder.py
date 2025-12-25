"""
HTTP request builder with randomization and header generation.
"""

import random
import secrets
from typing import Dict, Optional
from urllib.parse import urlparse, urlencode

from src.models import AttackMode
from src.config import USER_AGENTS, ACCEPT_HEADERS, ACCEPT_LANGUAGE, ACCEPT_ENCODING, REFERERS
from src.logger import logger


class RequestBuilder:
    """Build HTTP requests with randomized headers and data."""

    def __init__(
        self,
        target_url: str,
        mode: AttackMode = AttackMode.GET,
        custom_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        post_data: Optional[str] = None,
    ):
        """
        Initialize RequestBuilder.

        Args:
            target_url: Target URL.
            mode: Attack mode.
            custom_headers: Custom HTTP headers.
            cookies: Cookies dictionary.
            post_data: POST data string.
        """
        self.target_url = target_url
        self.mode = mode
        self.custom_headers = custom_headers or {}
        self.cookies = cookies or {}
        self.post_data = post_data

        # Parse URL
        parsed = urlparse(target_url)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.path = parsed.path or "/"
        self.query = parsed.query

        logger.debug(
            "request_builder_initialized",
            target=target_url,
            mode=mode.value,
            scheme=self.scheme,
        )

    def build_headers(self, randomize: bool = True) -> Dict[str, str]:
        """
        Build HTTP headers with optional randomization.

        Args:
            randomize: Whether to randomize headers.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = {
            "Host": self.host,
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
        }

        if randomize:
            # Random User-Agent
            browser = random.choice(list(USER_AGENTS.keys()))
            headers["User-Agent"] = random.choice(USER_AGENTS[browser])

            # Random Accept headers
            headers["Accept"] = random.choice(ACCEPT_HEADERS)
            headers["Accept-Language"] = random.choice(ACCEPT_LANGUAGE)
            headers["Accept-Encoding"] = random.choice(ACCEPT_ENCODING)

            # Random Referer
            if random.random() > 0.3:  # 70% chance of having referer
                headers["Referer"] = random.choice(REFERERS)
        else:
            # Default headers
            headers["User-Agent"] = USER_AGENTS["chrome"][0]
            headers["Accept"] = ACCEPT_HEADERS[0]
            headers["Accept-Language"] = ACCEPT_LANGUAGE[0]
            headers["Accept-Encoding"] = ACCEPT_ENCODING[0]

        # Add custom headers (override defaults)
        headers.update(self.custom_headers)

        # Add cookies
        if self.cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
            headers["Cookie"] = cookie_str

        # Mode-specific headers
        if self.mode == AttackMode.POST:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            if self.post_data:
                headers["Content-Length"] = str(len(self.post_data))

        return headers

    def build_url(self, add_random_param: bool = True) -> str:
        """
        Build request URL with optional random parameter.

        Args:
            add_random_param: Whether to add random query parameter.

        Returns:
            Complete URL string.
        """
        url = f"{self.scheme}://{self.host}{self.path}"

        # Combine existing query with random param
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
        """
        Build POST data with optional randomization.

        Args:
            randomize: Whether to randomize POST data.

        Returns:
            POST data string or None.
        """
        if self.mode != AttackMode.POST:
            return None

        if self.post_data:
            return self.post_data

        if randomize:
            # Generate random form data
            num_fields = random.randint(3, 8)
            data = {}
            for i in range(num_fields):
                key = f"field_{i}"
                value = secrets.token_urlsafe(random.randint(8, 32))
                data[key] = value

            return urlencode(data)

        return None

    def build_request_kwargs(self, randomize: bool = True) -> Dict:
        """
        Build complete request kwargs for aiohttp/httpx.

        Args:
            randomize: Whether to use randomization.

        Returns:
            Dictionary of request parameters.
        """
        kwargs = {
            "headers": self.build_headers(randomize=randomize),
            "timeout": 10,
            "allow_redirects": False,  # Don't follow redirects in attack mode
        }

        # Add URL
        kwargs["url"] = self.build_url(add_random_param=randomize)

        # Add POST data if applicable
        if self.mode == AttackMode.POST:
            data = self.build_post_data(randomize=randomize)
            if data:
                kwargs["data"] = data

        return kwargs

    def get_method(self) -> str:
        """
        Get HTTP method for current attack mode.

        Returns:
            HTTP method string (GET, POST, HEAD).
        """
        method_map = {
            AttackMode.GET: "GET",
            AttackMode.POST: "POST",
            AttackMode.HEAD: "HEAD",
            AttackMode.SLOW: "GET",  # Slowloris uses GET
            AttackMode.HTTP2: "GET",  # Default to GET for HTTP/2
        }
        return method_map.get(self.mode, "GET")

    @staticmethod
    def generate_random_string(length: int = 16) -> str:
        """
        Generate cryptographically secure random string.

        Args:
            length: Length of string to generate.

        Returns:
            Random string.
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_random_bytes(size: int = 1024) -> bytes:
        """
        Generate random bytes for payload.

        Args:
            size: Number of bytes to generate.

        Returns:
            Random bytes.
        """
        return secrets.token_bytes(size)
