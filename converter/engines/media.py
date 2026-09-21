"""
FFmpeg Multimedia Engine for OmniConvert.
Converts Video, Audio, and Video-to-Audio with high fidelity, stream copy, or lossless codecs.
Monitors progress in real time and enforces low hardware stress (Below Normal priority, capped threads).
"""

import os
import re
import sys
import time
import subprocess
from typing import List, Dict, Any, Optional
from converter.engines.base import BaseConverter, ConversionProgress, ProgressCallback, CancellationToken

try:
    import imageio_ffmpeg
    DEFAULT_FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    DEFAULT_FFMPEG_PATH = "ffmpeg"


class MediaConverter(BaseConverter):
    """High-fidelity multimedia conversion powered by FFmpeg."""

    VIDEO_FORMATS = [
        "mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "ts",
        "ogv", "3gp", "gif", "apng"
    ]

    AUDIO_FORMATS = [
        "mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "wma", "aiff",
        "alac", "ac3"
    ]

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or DEFAULT_FFMPEG_PATH

    @property
    def name(self) -> str:
        return "FFmpeg Multimedia Engine"

    @property
    def supported_source_formats(self) -> List[str]:
        return sorted(list(set(self.VIDEO_FORMATS + self.AUDIO_FORMATS)))

    @property
    def supported_target_formats(self) -> List[str]:
        return sorted(list(set(self.VIDEO_FORMATS + self.AUDIO_FORMATS)))

    def can_convert(self, src_ext: str, dst_ext: str) -> bool:
        src = src_ext.lower().lstrip(".")
        dst = dst_ext.lower().lstrip(".")
        
        # Audio -> Audio
        if src in self.AUDIO_FORMATS and dst in self.AUDIO_FORMATS:
            return True
        # Video -> Video
        if src in self.VIDEO_FORMATS and dst in self.VIDEO_FORMATS:
            return True
        # Video -> Audio (audio extraction)
        if src in self.VIDEO_FORMATS and dst in self.AUDIO_FORMATS:
            return True
        # Audio -> Video (e.g. creating video from audio, or audio to mp4)
        if src in self.AUDIO_FORMATS and dst in ["mp4", "mkv", "webm"]:
            return True

        return False

    def _get_media_duration(self, file_path: str) -> float:
        """Probe media duration in seconds using ffmpeg."""
        cmd = [self.ffmpeg_path, "-i", file_path]
        try:
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
                errors="replace"
            )
            _, stderr = proc.communicate(timeout=10)
            
            # Look for Duration: 00:01:23.45
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr)
            if match:
                hours, mins, secs = match.groups()
                return float(hours) * 3600 + float(mins) * 60 + float(secs)
        except Exception:
            pass
        return 0.0

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Parse HH:MM:SS.ms to total seconds."""
        parts = time_str.strip().split(":")
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return 0.0

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
        threads = options.get("threads", 2)
        power_mode = options.get("power_mode", "balanced")  # eco, balanced, turbo

        if power_mode == "eco":
            threads = 1
        elif power_mode == "turbo":
            threads = max(2, os.cpu_count() // 2 if os.cpu_count() else 4)

        duration = self._get_media_duration(source_path)
        source_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0

        # Build FFmpeg command arguments
        cmd = [self.ffmpeg_path, "-y", "-v", "info", "-progress", "pipe:1", "-nostats"]
        cmd += ["-threads", str(threads)]
        cmd += ["-i", source_path]

        # Audio target logic
        if dst_ext in self.AUDIO_FORMATS:
            if src_ext in self.VIDEO_FORMATS:
                cmd += ["-vn"]  # Strip video stream for extraction

            if dst_ext in ["wav", "aiff"]:
                cmd += ["-c:a", "pcm_s16le"]
            elif dst_ext == "flac":
                cmd += ["-c:a", "flac", "-compression_level", "8" if lossless else "5"]
            elif dst_ext == "alac":
                cmd += ["-c:a", "alac"]
            elif dst_ext == "mp3":
                if lossless:
                    cmd += ["-c:a", "libmp3lame", "-b:a", "320k", "-q:a", "0"]
                else:
                    cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]
            elif dst_ext in ["aac", "m4a"]:
                cmd += ["-c:a", "aac", "-b:a", "320k" if lossless else "192k"]
            elif dst_ext == "ogg":
                cmd += ["-c:a", "libvorbis", "-q:a", "8" if lossless else "5"]
            elif dst_ext == "opus":
                cmd += ["-c:a", "libopus", "-b:a", "256k" if lossless else "128k"]
            elif dst_ext == "wma":
                cmd += ["-c:a", "wmav2", "-b:a", "256k"]
            elif dst_ext == "ac3":
                cmd += ["-c:a", "ac3", "-b:a", "384k"]

        # Video target logic
        elif dst_ext in self.VIDEO_FORMATS:
            if dst_ext == "gif":
                # High-quality palette generation for crisp GIF
                cmd += ["-filter_complex", "[0:v] fps=15,scale=480:-1:flags=lanczos,split [a][b]; [a] palettegen [p]; [b][p] paletteuse"]
            elif dst_ext == "webm":
                cmd += ["-c:v", "libvpx-vp9", "-crf", "24" if lossless else "32", "-b:v", "0", "-c:a", "libopus"]
            elif dst_ext in ["mp4", "mkv", "mov", "m4v"]:
                # High-fidelity H.264
                crf = "18" if lossless else "23"
                cmd += ["-c:v", "libx264", "-crf", crf, "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k"]
            elif dst_ext == "avi":
                cmd += ["-c:v", "mpeg4", "-q:v", "2" if lossless else "4", "-c:a", "mp3", "-b:a", "256k"]
            else:
                # Default stream copy or standard encoder
                cmd += ["-c:v", "libx264", "-c:a", "aac"]

        cmd.append(target_path)

        # Setup Windows process creation flags (BELOW_NORMAL_PRIORITY_CLASS prevents stutter)
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

        start_time = time.time()
        last_update_time = start_time
        processed_seconds = 0.0

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            creationflags=creationflags,
            bufsize=1,
            errors="replace"
        )

        try:
            out_time_us = 0
            speed_val = 1.0
            fps_val = 0.0

            # Read stdout progress lines
            while True:
                if cancel_token and cancel_token.is_cancelled:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    if os.path.exists(target_path):
                        try:
                            os.remove(target_path)
                        except OSError:
                            pass
                    raise RuntimeError("Conversion cancelled by user.")

                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.02)
                    continue

                line = line.strip()
                if "=" in line:
                    key, val = line.split("=", 1)
                    key, val = key.strip(), val.strip()

                    if key == "out_time_us":
                        try:
                            out_time_us = int(val)
                            processed_seconds = out_time_us / 1_000_000.0
                        except ValueError:
                            pass
                    elif key == "out_time":
                        processed_seconds = self._parse_time_to_seconds(val)
                    elif key == "speed":
                        val_cleaned = val.rstrip("x")
                        try:
                            speed_val = float(val_cleaned)
                        except ValueError:
                            speed_val = 1.0
                    elif key == "fps":
                        try:
                            fps_val = float(val)
                        except ValueError:
                            fps_val = 0.0
                    elif key == "progress" and val in ("continue", "end"):
                        now = time.time()
                        if now - last_update_time >= 0.25 or val == "end":
                            last_update_time = now
                            elapsed = max(0.001, now - start_time)

                            if duration > 0:
                                progress_pct = min(99.0, (processed_seconds / duration) * 100.0)
                                remaining_seconds = max(0.0, duration - processed_seconds)
                                eta = remaining_seconds / max(0.1, speed_val)
                            else:
                                progress_pct = 50.0
                                eta = 0.0

                            current_out_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
                            throughput = current_out_size / elapsed

                            if progress_callback:
                                progress_callback(
                                    ConversionProgress(
                                        progress=100.0 if val == "end" else progress_pct,
                                        speed_bytes_sec=throughput,
                                        eta_seconds=eta,
                                        status_text=f"Converting with FFmpeg ({speed_val:.2f}x speed)",
                                        current_bytes=current_out_size,
                                        total_bytes=source_size,
                                        fps=fps_val
                                    )
                                )

            returncode = proc.wait()
            if returncode != 0:
                stderr_output = proc.stderr.read()
                raise RuntimeError(f"FFmpeg conversion failed (exit code {returncode}): {stderr_output[-400:]}")

            if progress_callback:
                final_size = os.path.getsize(target_path) if os.path.exists(target_path) else source_size
                progress_callback(
                    ConversionProgress(
                        progress=100.0,
                        speed_bytes_sec=final_size / max(0.001, time.time() - start_time),
                        eta_seconds=0.0,
                        status_text="Completed successfully",
                        current_bytes=final_size,
                        total_bytes=final_size
                    )
                )

            return True

        except Exception as ex:
            try:
                proc.kill()
            except Exception:
                pass
            raise ex
        finally:
            try:
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()
            except Exception:
                pass

