"""
Pillow Image Engine for OmniConvert.
Converts images with high fidelity, lossless compression options, color profile and alpha preservation.
"""

import os
import time
from typing import List, Dict, Any, Optional
from PIL import Image, ImageSequence, ImageOps
from converter.engines.base import BaseConverter, ConversionProgress, ProgressCallback, CancellationToken


class ImageConverter(BaseConverter):
    """High-fidelity image conversion powered by Pillow."""

    FORMATS = [
        "png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "ico",
        "gif", "ppm", "tga", "eps", "pdf", "dib"
    ]

    @property
    def name(self) -> str:
        return "Pillow High-Fidelity Image Engine"

    @property
    def supported_source_formats(self) -> List[str]:
        return self.FORMATS

    @property
    def supported_target_formats(self) -> List[str]:
        return self.FORMATS

    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        src = src_ext.lower().lstrip(".")
        dst = dst_ext.lower().lstrip(".")
        return src in self.FORMATS and dst in self.FORMATS

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
        lossless = options.get("lossless", True)
        quality = options.get("quality", 100 if lossless else 90)

        start_time = time.time()
        source_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0

        if progress_callback:
            progress_callback(
                ConversionProgress(
                    progress=10.0,
                    status_text="Loading image data...",
                    current_bytes=0,
                    total_bytes=source_size
                )
            )

        if cancel_token and cancel_token.is_cancelled:
            raise RuntimeError("Conversion cancelled by user.")

        with Image.open(source_path) as img:
            # Preserve EXIF and ICC profile if present
            icc_profile = img.info.get("icc_profile")
            exif = img.info.get("exif")

            # Check if animated (GIF or animated WebP)
            is_animated = getattr(img, "is_animated", False)

            # Target format string for Pillow
            fmt_mapping = {
                "jpg": "JPEG",
                "jpeg": "JPEG",
                "tif": "TIFF",
                "dib": "BMP"
            }
            save_format = fmt_mapping.get(dst_ext, dst_ext.upper())

            # Prepare save kwargs
            save_kwargs: Dict[str, Any] = {}
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile
            if exif:
                save_kwargs["exif"] = exif

            # Handle format specific configurations
            if save_format == "JPEG":
                # Handle Alpha channel compositing (white background for clean look)
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    alpha_img = img.convert("RGBA")
                    bg.paste(alpha_img, mask=alpha_img.split()[3])
                    work_img = bg
                elif img.mode != "RGB":
                    work_img = img.convert("RGB")
                else:
                    work_img = img

                save_kwargs["quality"] = 100 if lossless else max(10, min(100, quality))
                save_kwargs["subsampling"] = 0 if lossless else 1  # 4:4:4 for maximum fidelity
                save_kwargs["optimize"] = True

            elif save_format == "WEBP":
                work_img = img
                if lossless:
                    save_kwargs["lossless"] = True
                    save_kwargs["quality"] = 100
                else:
                    save_kwargs["lossless"] = False
                    save_kwargs["quality"] = max(10, min(100, quality))
                save_kwargs["method"] = 6  # Best compression speed/size trade-off

            elif save_format == "PNG":
                work_img = img
                save_kwargs["optimize"] = True
                save_kwargs["compress_level"] = 9 if lossless else 6

            elif save_format == "TIFF":
                work_img = img
                save_kwargs["compression"] = "tiff_deflate" if lossless else "jpeg"

            elif save_format == "ICO":
                # Convert to RGBA and resize for standard icon sizes
                work_img = img.convert("RGBA")
                save_kwargs["sizes"] = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

            elif save_format == "PDF":
                # Single or multi-page image to PDF
                if img.mode in ("RGBA", "LA"):
                    work_img = img.convert("RGB")
                else:
                    work_img = img
                save_kwargs["resolution"] = 300.0

            else:
                work_img = img

            if progress_callback:
                progress_callback(
                    ConversionProgress(
                        progress=50.0,
                        status_text=f"Encoding into {save_format}...",
                        current_bytes=source_size // 2,
                        total_bytes=source_size
                    )
                )

            if cancel_token and cancel_token.is_cancelled:
                raise RuntimeError("Conversion cancelled by user.")

            # Save operation
            if is_animated and save_format in ("GIF", "WEBP"):
                frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
                save_kwargs["save_all"] = True
                save_kwargs["append_images"] = frames[1:]
                save_kwargs["duration"] = img.info.get("duration", 100)
                save_kwargs["loop"] = img.info.get("loop", 0)
                frames[0].save(target_path, format=save_format, **save_kwargs)
            else:
                work_img.save(target_path, format=save_format, **save_kwargs)

        elapsed = max(0.001, time.time() - start_time)
        final_size = os.path.getsize(target_path) if os.path.exists(target_path) else source_size

        if progress_callback:
            progress_callback(
                ConversionProgress(
                    progress=100.0,
                    speed_bytes_sec=final_size / elapsed,
                    eta_seconds=0.0,
                    status_text="Image conversion completed",
                    current_bytes=final_size,
                    total_bytes=final_size
                )
            )

        return True
