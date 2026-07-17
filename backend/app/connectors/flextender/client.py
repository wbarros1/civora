"""HTTP-client voor openbare Flextender-pagina's."""

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class FlextenderHttpClient:
    """Beheert HTTP-verzoeken naar openbare Flextender-pagina's."""

    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: int,
    ) -> None:
        """Initialiseer een herbruikbare HTTP-client."""

        transport = httpx.HTTPTransport(
            retries=2,
        )

        self._user_agent = user_agent
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.7",
            },
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            transport=transport,
        )

        self._robots_by_origin: dict[
            str,
            RobotFileParser | None,
        ] = {}

    def __enter__(self) -> "FlextenderHttpClient":
        """Ondersteun gebruik als contextmanager."""

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Sluit de HTTP-client."""

        self.close()

    def close(self) -> None:
        """Sluit netwerkverbindingen."""

        self._client.close()

    @staticmethod
    def _get_origin(url: str) -> str:
        """Bepaal scheme en host van een URL."""

        parsed_url = urlparse(url)

        return (
            f"{parsed_url.scheme}://"
            f"{parsed_url.netloc}"
        )

    def _get_robots_parser(
        self,
        url: str,
    ) -> RobotFileParser | None:
        """
        Haal robots.txt één keer per host op.

        None betekent dat robots.txt niet bestaat.
        """

        origin = self._get_origin(url)

        if origin in self._robots_by_origin:
            return self._robots_by_origin[origin]

        robots_url = f"{origin}/robots.txt"

        try:
            response = self._client.get(robots_url)
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"robots.txt kon niet worden opgehaald: "
                f"{robots_url}"
            ) from exc

        if response.status_code == 404:
            self._robots_by_origin[origin] = None
            return None

        response.raise_for_status()

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())

        self._robots_by_origin[origin] = parser

        return parser

    def assert_allowed(self, url: str) -> None:
        """Controleer of robots.txt het verzoek toestaat."""

        parser = self._get_robots_parser(url)

        if parser is None:
            return

        if not parser.can_fetch(
            self._user_agent,
            url,
        ):
            raise PermissionError(
                f"robots.txt staat ophalen niet toe: {url}"
            )

    def get_html(
        self,
        url: str,
        *,
        delay_seconds: float = 0,
    ) -> httpx.Response:
        """Haal een toegestane HTML-pagina op."""

        self.assert_allowed(url)

        if delay_seconds > 0:
            time.sleep(delay_seconds)

        response = self._client.get(url)
        response.raise_for_status()

        content_type = response.headers.get(
            "content-type",
            "",
        ).lower()

        if (
            content_type
            and "html" not in content_type
            and "xhtml" not in content_type
        ):
            raise ValueError(
                "Onverwacht content-type voor HTML-pagina: "
                f"{content_type}"
            )

        if not response.text.strip():
            raise ValueError(
                f"Flextender retourneerde een lege pagina: {url}"
            )

        return response