"""
Tabular Data and Spreadsheet Engine for OmniConvert.
Converts CSV, XLSX, JSON, TSV, Parquet, HTML tables, and XML using Pandas and OpenPyXL.
"""

import os
import time
from typing import List, Dict, Any, Optional
import pandas as pd
from converter.engines.base import BaseConverter, ConversionProgress, ProgressCallback, CancellationToken


class DataConverter(BaseConverter):
    """Tabular data & spreadsheet converter powered by Pandas & OpenPyXL."""

    DATA_FORMATS = ["csv", "xlsx", "xls", "json", "tsv", "parquet", "html", "xml"]

    @property
    def name(self) -> str:
        return "Tabular Data & Spreadsheet Engine"

    @property
    def supported_source_formats(self) -> List[str]:
        return self.DATA_FORMATS

    @property
    def supported_target_formats(self) -> List[str]:
        return self.DATA_FORMATS

    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        src = src_ext.lower().lstrip(".")
        dst = dst_ext.lower().lstrip(".")
        if src == dst:
            return False
        return src in self.DATA_FORMATS and dst in self.DATA_FORMATS

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

        if progress_callback:
            progress_callback(
                ConversionProgress(
                    progress=15.0,
                    status_text=f"Parsing {src_ext.upper()} dataset...",
                    current_bytes=0,
                    total_bytes=source_size
                )
            )

        if cancel_token and cancel_token.is_cancelled:
            raise RuntimeError("Conversion cancelled by user.")

        # Read source data
        if src_ext in ("csv", "tsv"):
            sep = "\t" if src_ext == "tsv" else ","
            df = pd.read_csv(source_path, sep=sep, encoding="utf-8", on_bad_lines="skip")
        elif src_ext in ("xlsx", "xls"):
            df = pd.read_excel(source_path)
        elif src_ext == "json":
            df = pd.read_json(source_path)
        elif src_ext == "parquet":
            df = pd.read_parquet(source_path)
        elif src_ext == "html":
            dfs = pd.read_html(source_path)
            df = dfs[0] if dfs else pd.DataFrame()
        elif src_ext == "xml":
            df = pd.read_xml(source_path)
        else:
            raise ValueError(f"Unsupported source format: {src_ext}")

        if progress_callback:
            progress_callback(
                ConversionProgress(
                    progress=60.0,
                    status_text=f"Exporting {len(df)} rows to {dst_ext.upper()}...",
                    current_bytes=source_size // 2,
                    total_bytes=source_size
                )
            )

        if cancel_token and cancel_token.is_cancelled:
            raise RuntimeError("Conversion cancelled by user.")

        # Write target data
        if dst_ext == "csv":
            df.to_csv(target_path, index=False, encoding="utf-8")
        elif dst_ext == "tsv":
            df.to_csv(target_path, sep="\t", index=False, encoding="utf-8")
        elif dst_ext == "xlsx":
            df.to_excel(target_path, index=False, engine="openpyxl")
        elif dst_ext == "json":
            df.to_json(target_path, orient="records", indent=2)
        elif dst_ext == "parquet":
            df.to_parquet(target_path, index=False)
        elif dst_ext == "html":
            df.to_html(target_path, index=False)
        elif dst_ext == "xml":
            df.to_xml(target_path, index=False)
        else:
            raise ValueError(f"Unsupported target format: {dst_ext}")

        elapsed = max(0.001, time.time() - start_time)
        final_size = os.path.getsize(target_path) if os.path.exists(target_path) else source_size

        if progress_callback:
            progress_callback(
                ConversionProgress(
                    progress=100.0,
                    speed_bytes_sec=final_size / elapsed,
                    eta_seconds=0.0,
                    status_text="Data conversion completed successfully",
                    current_bytes=final_size,
                    total_bytes=final_size
                )
            )

        return True
