"""
Base interfaces and data structures for OmniConvert engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List


@dataclass
class ConversionProgress:
    progress: float  # 0.0 to 100.0
    speed_bytes_sec: float = 0.0  # Bytes per second
    eta_seconds: float = 0.0  # Estimated remaining seconds
    status_text: str = ""
    current_bytes: int = 0
    total_bytes: int = 0
    fps: float = 0.0  # For video conversions


@dataclass
class CancellationToken:
    _cancelled: bool = False

    def cancel(self):
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled


ProgressCallback = Callable[[ConversionProgress], None]


class BaseConverter(ABC):
    """Abstract base class for all file conversion engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the conversion engine."""
        pass

    @property
    @abstractmethod
    def supported_source_formats(self) -> List[str]:
        """List of supported lowercase source file extensions (without dot)."""
        pass

    @property
    @abstractmethod
    def supported_target_formats(self) -> List[str]:
        """List of supported lowercase target file extensions (without dot)."""
        pass

    @abstractmethod
    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        """Returns True if this engine can convert from src_ext to dst_ext."""
        pass

    @abstractmethod
    def convert(
        self,
        source_path: str,
        target_path: str,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_token: Optional[CancellationToken] = None,
    ) -> bool:
        """
        Execute conversion from source_path to target_path.
        Returns True if successful, raises exception on failure.
        """
        pass
