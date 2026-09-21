"""
Universal Format Registry and Engine Resolver for OmniConvert.
Inspects file signatures, associates extensions to categories, and resolves the best conversion engine.
"""

import os
from typing import List, Dict, Optional, Tuple
from converter.engines.base import BaseConverter
from converter.engines.media import MediaConverter
from converter.engines.images import ImageConverter
from converter.engines.documents import DocumentConverter
from converter.engines.data import DataConverter
from converter.engines.archives import ArchiveConverter
from converter.engines.binary import BinaryConverter


class ConversionRegistry:
    """Registry coordinating all specialized conversion engines."""

    def __init__(self):
        self.engines: List[BaseConverter] = [
            ImageConverter(),
            MediaConverter(),
            DataConverter(),
            DocumentConverter(),
            ArchiveConverter(),
            BinaryConverter(),
        ]

    def get_extension(self, file_path: str) -> str:
        """Extract clean lowercase extension without leading dot."""
        _, ext = os.path.splitext(file_path)
        return ext.lower().lstrip(".")

    def detect_category(self, file_path: str) -> str:
        """Classify file into high-level category."""
        ext = self.get_extension(file_path)
        if ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "ico", "gif", "ppm", "tga", "eps"):
            return "Image"
        if ext in ("mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "ts", "ogv", "3gp"):
            return "Video"
        if ext in ("mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "wma", "aiff", "alac", "ac3"):
            return "Audio"
        if ext in ("csv", "xlsx", "xls", "tsv", "parquet"):
            return "Spreadsheet/Data"
        if ext in ("pdf", "docx", "txt", "md", "html", "htm", "rtf"):
            return "Document"
        if ext in ("zip", "tar", "gz", "bz2", "xz", "tgz", "tbz2"):
            return "Archive"
        if ext in ("json", "yaml", "yml", "xml"):
            return "Code/Data"
        return "Universal/Binary"

    def get_compatible_targets(self, file_path: str) -> List[str]:
        """
        Return an intelligent, ordered list of target format extensions
        supported for the given input file.
        """
        src_ext = self.get_extension(file_path)
        targets = set()

        for engine in self.engines:
            # Check all supported targets of engines that can handle this source
            for target_ext in engine.supported_target_formats:
                if target_ext != src_ext and engine.can_convert(src_ext, target_ext):
                    targets.add(target_ext)

        # Always offer universal fallback encodings/archives
        targets.add("zip")
        targets.add("b64")
        targets.add("hex")
        targets.add("sha256")

        if src_ext in targets:
            targets.remove(src_ext)

        # Categorized sorting
        category = self.detect_category(file_path)
        priority_orders = {
            "Image": ["webp", "png", "jpg", "pdf", "ico", "bmp", "tiff", "gif"],
            "Video": ["mp4", "webm", "mkv", "mov", "gif", "mp3", "wav", "flac"],
            "Audio": ["mp3", "wav", "flac", "aac", "ogg", "m4a", "opus"],
            "Spreadsheet/Data": ["xlsx", "csv", "json", "parquet", "tsv", "html"],
            "Document": ["pdf", "docx", "txt", "md", "html"],
            "Archive": ["zip", "tar", "gz", "bz2", "xz"],
        }

        priorities = priority_orders.get(category, [])
        sorted_targets = []
        for p in priorities:
            if p in targets and p != src_ext:
                sorted_targets.append(p)
                targets.remove(p)

        # Append remainder sorted alphabetically
        sorted_targets.extend(sorted(list(targets)))
        return sorted_targets

    def resolve_engine(self, src_ext: str, dst_ext: str) -> Optional[BaseConverter]:
        """Find the best engine suited for converting src_ext to dst_ext."""
        src = src_ext.lower().lstrip(".")
        dst = dst_ext.lower().lstrip(".")

        # Media converter handles audio extraction from video, so prioritize appropriately
        if src in MediaConverter.VIDEO_FORMATS and dst in MediaConverter.AUDIO_FORMATS:
            for engine in self.engines:
                if isinstance(engine, MediaConverter):
                    return engine

        # Try specific engines first
        for engine in self.engines:
            if not isinstance(engine, BinaryConverter) and engine.can_convert(src, dst):
                return engine

        # Fallback to binary / universal engine
        for engine in self.engines:
            if isinstance(engine, BinaryConverter) and engine.can_convert(src, dst):
                return engine

        return None


# Global singleton instance
registry = ConversionRegistry()
