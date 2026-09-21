"""
Archive and Compression Engine for OmniConvert.
Converts between ZIP, TAR, GZ, BZ2, and XZ archive formats with lossless preservation of contents.
"""

import os
import time
import zipfile
import tarfile
import shutil
import tempfile
from typing import List, Dict, Any, Optional
from converter.engines.base import BaseConverter, ConversionProgress, ProgressCallback, CancellationToken


class ArchiveConverter(BaseConverter):
    """Lossless archive converter supporting ZIP, TAR, GZ, BZ2, and XZ."""

    ARCHIVE_FORMATS = ["zip", "tar", "gz", "bz2", "xz", "tgz", "tbz2"]

    @property
    def name(self) -> str:
        return "Universal Archive & Compression Engine"

    @property
    def supported_source_formats(self) -> List[str]:
        return self.ARCHIVE_FORMATS

    @property
    def supported_target_formats(self) -> List[str]:
        return ["zip", "tar", "gz", "bz2", "xz"]

    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        src = src_ext.lower().lstrip(".")
        dst = dst_ext.lower().lstrip(".")
        if src == dst:
            return False
        return src in self.ARCHIVE_FORMATS and dst in self.supported_target_formats

    def _extract_all(self, archive_path: str, extract_dir: str, cancel_token: Optional[CancellationToken] = None):
        ext = os.path.splitext(archive_path)[1].lower().lstrip(".")
        if ext == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        elif ext in ("tar", "gz", "bz2", "xz", "tgz", "tbz2"):
            mode = "r:*"
            with tarfile.open(archive_path, mode) as tf:
                tf.extractall(extract_dir)
        else:
            raise ValueError(f"Unsupported archive format: {ext}")

    def _create_archive(self, source_dir: str, target_path: str, dst_ext: str, cancel_token: Optional[CancellationToken] = None):
        if dst_ext == "zip":
            with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        if cancel_token and cancel_token.is_cancelled:
                            raise RuntimeError("Conversion cancelled by user.")
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        zf.write(full_path, rel_path)
        elif dst_ext in ("tar", "gz", "bz2", "xz"):
            mode_map = {
                "tar": "w",
                "gz": "w:gz",
                "bz2": "w:bz2",
                "xz": "w:xz"
            }
            mode = mode_map[dst_ext]
            with tarfile.open(target_path, mode) as tf:
                for root, _, files in os.walk(source_dir):
                    for file in files:
                        if cancel_token and cancel_token.is_cancelled:
                            raise RuntimeError("Conversion cancelled by user.")
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        tf.add(full_path, arcname=rel_path)
        else:
            raise ValueError(f"Unsupported target archive format: {dst_ext}")

    def convert(
        self,
        source_path: str,
        target_path: str,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[ProgressCallback] = None,
        cancel_token: Optional[CancellationToken] = None,
    ) -> bool:
        options = options or {}
        src_ext = os.path.splitext(source_path)[1].lower().lstrip(".")
        dst_ext = os.path.splitext(target_path)[1].lower().lstrip(".")
        start_time = time.time()
        source_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0

        temp_dir = tempfile.mkdtemp(prefix="omniconvert_archive_")
        try:
            if progress_callback:
                progress_callback(
                    ConversionProgress(
                        progress=20.0,
                        status_text=f"Extracting {src_ext.upper()} archive contents...",
                        current_bytes=0,
                        total_bytes=source_size
                    )
                )

            if cancel_token and cancel_token.is_cancelled:
                raise RuntimeError("Conversion cancelled by user.")

            self._extract_all(source_path, temp_dir, cancel_token)

            if progress_callback:
                progress_callback(
                    ConversionProgress(
                        progress=60.0,
                        status_text=f"Recompressing into {dst_ext.upper()}...",
                        current_bytes=source_size // 2,
                        total_bytes=source_size
                    )
                )

            if cancel_token and cancel_token.is_cancelled:
                raise RuntimeError("Conversion cancelled by user.")

            self._create_archive(temp_dir, target_path, dst_ext, cancel_token)

            elapsed = max(0.001, time.time() - start_time)
            final_size = os.path.getsize(target_path) if os.path.exists(target_path) else source_size

            if progress_callback:
                progress_callback(
                    ConversionProgress(
                        progress=100.0,
                        speed_bytes_sec=final_size / elapsed,
                        eta_seconds=0.0,
                        status_text="Archive recompressed successfully",
                        current_bytes=final_size,
                        total_bytes=final_size
                    )
                )

            return True

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
