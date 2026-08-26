from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    base_url: str = "https://example.test"
    timeout: float = 10.0

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            base_url=os.getenv("API_BASE_URL", cls.base_url).rstrip("/"),
            timeout=float(os.getenv("API_TIMEOUT", cls.timeout)),
        )