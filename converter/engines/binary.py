"""
Binary, Encoding, and Integrity Engine for OmniConvert.
Ensures literally ANY file can be converted without data loss to Base64, Hexadecimal, Hashes, or Binary.
"""

import os
import time
import base64
import hashlib
from typing import List, Dict, Any, Optional
from converter.engines.base import BaseConverter, ConversionProgress, ProgressCallback, CancellationToken


class BinaryConverter(BaseConverter):
    """Universal binary encoding and representation engine."""

    ENCODINGS = ["b64", "base64", "hex", "bin", "sha256", "md5"]

    @property
    def name(self) -> str:
        return "Universal Binary & Encoding Engine"

    @property
    def supported_source_formats(self) -> List[str]:
        return ["*"]  # Universal

    @property
    def supported_target_formats(self) -> List[str]:
        return ["b64", "hex", "bin", "sha256", "md5"]

    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        dst = dst_ext.lower().lstrip(".")
        src = src_ext.lower().lstrip(".")
        if dst in self.supported_target_formats:
            return True
        if src in ("b64", "base64", "hex") and dst not in ("b64", "base64", "hex"):
            return True  # Decoding back to original
        return False

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

        chunk_size = 64 * 1024  # 64 KB chunks for zero memory stress
        processed_bytes = 0

        # Decoding from Base64 or Hex back to Binary
        if src_ext in ("b64", "base64"):
            with open(source_path, "rb") as fin, open(target_path, "wb") as fout:
                b64_data = fin.read()
                fout.write(base64.b64decode(b64_data))
        elif src_ext == "hex":
            with open(source_path, "r", encoding="utf-8") as fin, open(target_path, "wb") as fout:
                hex_data = fin.read().replace("\n", "").replace(" ", "").strip()
                fout.write(bytes.fromhex(hex_data))

        # Encoding from any file to Base64
        elif dst_ext in ("b64", "base64"):
            with open(source_path, "rb") as fin, open(target_path, "wb") as fout:
                while True:
                    if cancel_token and cancel_token.is_cancelled:
                        raise RuntimeError("Conversion cancelled by user.")
                    chunk = fin.read(chunk_size)
                    if not chunk:
                        break
                    fout.write(base64.b64encode(chunk))
                    processed_bytes += len(chunk)
                    if progress_callback and source_size > 0:
                        progress_callback(
                            ConversionProgress(
                                progress=(processed_bytes / source_size) * 100.0,
                                speed_bytes_sec=processed_bytes / max(0.001, time.time() - start_time),
                                status_text="Encoding Base64 stream...",
                                current_bytes=processed_bytes,
                                total_bytes=source_size
                            )
                        )

        # Encoding from any file to Hex
        elif dst_ext == "hex":
            with open(source_path, "rb") as fin, open(target_path, "w", encoding="utf-8") as fout:
                while True:
                    if cancel_token and cancel_token.is_cancelled:
                        raise RuntimeError("Conversion cancelled by user.")
                    chunk = fin.read(chunk_size)
                    if not chunk:
                        break
                    fout.write(chunk.hex() + "\n")
                    processed_bytes += len(chunk)
                    if progress_callback and source_size > 0:
                        progress_callback(
                            ConversionProgress(
                                progress=(processed_bytes / source_size) * 100.0,
                                speed_bytes_sec=processed_bytes / max(0.001, time.time() - start_time),
                                status_text="Encoding Hex stream...",
                                current_bytes=processed_bytes,
                                total_bytes=source_size
                            )
                        )

        # Generating Checksum Hash Report
        elif dst_ext in ("sha256", "md5"):
            hasher = hashlib.sha256() if dst_ext == "sha256" else hashlib.md5()
            with open(source_path, "rb") as fin:
                while True:
                    if cancel_token and cancel_token.is_cancelled:
                        raise RuntimeError("Conversion cancelled by user.")
                    chunk = fin.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    processed_bytes += len(chunk)
                    if progress_callback and source_size > 0:
                        progress_callback(
                            ConversionProgress(
                                progress=(processed_bytes / source_size) * 100.0,
                                speed_bytes_sec=processed_bytes / max(0.001, time.time() - start_time),
                                status_text=f"Computing {dst_ext.upper()} hash...",
                                current_bytes=processed_bytes,
                                total_bytes=source_size
                            )
                        )
            digest = hasher.hexdigest()
            with open(target_path, "w", encoding="utf-8") as fout:
                fout.write(f"File: {os.path.basename(source_path)}\nAlgorithm: {dst_ext.upper()}\nHash: {digest}\nSize: {source_size} bytes\n")

        # Binary raw copy / stream
        elif dst_ext == "bin":
            with open(source_path, "rb") as fin, open(target_path, "wb") as fout:
                while True:
                    if cancel_token and cancel_token.is_cancelled:
                        raise RuntimeError("Conversion cancelled by user.")
                    chunk = fin.read(chunk_size)
                    if not chunk:
                        break
                    fout.write(chunk)
                    processed_bytes += len(chunk)

        elapsed = max(0.001, time.time() - start_time)
        final_size = os.path.getsize(target_path) if os.path.exists(target_path) else source_size

        if progress_callback:
            progress_callback(
                ConversionProgress(
                    progress=100.0,
                    speed_bytes_sec=final_size / elapsed,
                    eta_seconds=0.0,
                    status_text="Conversion completed successfully",
                    current_bytes=final_size,
                    total_bytes=final_size
                )
            )

        return True
