"""
Comprehensive Test Suite for OmniConvert.
Verifies all engines: Images, Multimedia (FFmpeg), Documents, Data, Archives, Binary, and Telemetry.
"""

import os
import sys
import unittest
import tempfile
import shutil
import numpy as np
from PIL import Image

# Ensure project directory is in sys.path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from converter.core.registry import registry
from converter.engines.images import ImageConverter
from converter.engines.media import MediaConverter
from converter.engines.documents import DocumentConverter
from converter.engines.data import DataConverter
from converter.engines.archives import ArchiveConverter
from converter.engines.binary import BinaryConverter
from converter.core.telemetry import EmaEtaCalculator, HardwareMonitor, format_bytes, format_duration


class TestOmniConvertEngines(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="omniconvert_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_image_conversions(self):
        # Create a test PNG image
        img_path = os.path.join(self.test_dir, "test.png")
        img = Image.new("RGBA", (128, 128), color=(99, 102, 241, 255))
        img.save(img_path)

        engine = ImageConverter()

        # 1. PNG -> WEBP Lossless
        webp_path = os.path.join(self.test_dir, "test.webp")
        success = engine.convert(img_path, webp_path, {"lossless": True})
        self.assertTrue(success)
        self.assertTrue(os.path.exists(webp_path))
        self.assertGreater(os.path.getsize(webp_path), 0)

        # 2. PNG -> JPEG (tests alpha channel compositing)
        jpg_path = os.path.join(self.test_dir, "test.jpg")
        success = engine.convert(img_path, jpg_path, {"lossless": True})
        self.assertTrue(success)
        self.assertTrue(os.path.exists(jpg_path))

        # 3. PNG -> PDF
        pdf_path = os.path.join(self.test_dir, "test.pdf")
        success = engine.convert(img_path, pdf_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(pdf_path))

    def test_data_conversions(self):
        # Create a test CSV
        csv_path = os.path.join(self.test_dir, "data.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("id,name,role,score\n1,Alice,Engineer,98.5\n2,Bob,Designer,95.0\n")

        engine = DataConverter()

        # 1. CSV -> XLSX
        xlsx_path = os.path.join(self.test_dir, "data.xlsx")
        success = engine.convert(csv_path, xlsx_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(xlsx_path))

        # 2. XLSX -> JSON
        json_path = os.path.join(self.test_dir, "data.json")
        success = engine.convert(xlsx_path, json_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(json_path))

        # 3. JSON -> TSV
        tsv_path = os.path.join(self.test_dir, "data.tsv")
        success = engine.convert(json_path, tsv_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(tsv_path))

    def test_document_conversions(self):
        txt_path = os.path.join(self.test_dir, "sample.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("# OmniConvert Universal Document\n\nTesting high-fidelity rendering.\n")

        engine = DocumentConverter()

        # 1. TXT -> HTML
        html_path = os.path.join(self.test_dir, "sample.html")
        success = engine.convert(txt_path, html_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(html_path))

        # 2. HTML -> DOCX
        docx_path = os.path.join(self.test_dir, "sample.docx")
        success = engine.convert(html_path, docx_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(docx_path))

    def test_archive_conversions(self):
        # Create test files
        src_folder = os.path.join(self.test_dir, "archive_content")
        os.makedirs(src_folder)
        with open(os.path.join(src_folder, "file1.txt"), "w") as f:
            f.write("Hello Archive 1")
        with open(os.path.join(src_folder, "file2.txt"), "w") as f:
            f.write("Hello Archive 2")

        # Create initial ZIP
        zip_path = os.path.join(self.test_dir, "bundle.zip")
        shutil.make_archive(os.path.splitext(zip_path)[0], "zip", src_folder)

        engine = ArchiveConverter()

        # ZIP -> TAR.GZ
        tar_gz_path = os.path.join(self.test_dir, "bundle.gz")
        success = engine.convert(zip_path, tar_gz_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(tar_gz_path))

    def test_binary_and_checksum_conversions(self):
        bin_file = os.path.join(self.test_dir, "raw.dat")
        with open(bin_file, "wb") as f:
            f.write(b"OmniConvert Binary Stream 123456789")

        engine = BinaryConverter()

        # 1. Binary -> Base64
        b64_file = os.path.join(self.test_dir, "raw.b64")
        success = engine.convert(bin_file, b64_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(b64_file))

        # 2. Base64 -> Binary (lossless roundtrip)
        restored_bin = os.path.join(self.test_dir, "restored.dat")
        success = engine.convert(b64_file, restored_bin)
        self.assertTrue(success)
        with open(restored_bin, "rb") as f:
            self.assertEqual(f.read(), b"OmniConvert Binary Stream 123456789")

        # 3. Binary -> SHA256 checksum report
        hash_file = os.path.join(self.test_dir, "raw.sha256")
        success = engine.convert(bin_file, hash_file)
        self.assertTrue(success)
        with open(hash_file, "r") as f:
            content = f.read()
            self.assertIn("Algorithm: SHA256", content)

    def test_media_ffmpeg_conversion(self):
        # Generate a small 1-second sine wave WAV using scipy/numpy or wave module
        import wave
        import struct
        import math

        wav_path = os.path.join(self.test_dir, "sine.wav")
        sample_rate = 44100
        duration = 1.0  # second
        num_samples = int(sample_rate * duration)
        
        with wave.open(wav_path, "w") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            data = []
            for i in range(num_samples):
                val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
                data.append(struct.pack("<h", val))
            wav_file.writeframes(b"".join(data))

        engine = MediaConverter()

        # 1. WAV -> MP3
        mp3_path = os.path.join(self.test_dir, "sine.mp3")
        success = engine.convert(wav_path, mp3_path, {"lossless": True})
        self.assertTrue(success)
        self.assertTrue(os.path.exists(mp3_path))
        self.assertGreater(os.path.getsize(mp3_path), 0)

        # 2. WAV -> FLAC (Lossless)
        flac_path = os.path.join(self.test_dir, "sine.flac")
        success = engine.convert(wav_path, flac_path, {"lossless": True})
        self.assertTrue(success)
        self.assertTrue(os.path.exists(flac_path))

    def test_telemetry_and_eta(self):
        monitor = HardwareMonitor()
        snapshot = monitor.snapshot()
        self.assertIn("system_cpu_pct", snapshot)
        self.assertIn("process_ram_mb", snapshot)

        calc = EmaEtaCalculator()
        eta, speed = calc.update(500, 1000)
        self.assertGreaterEqual(eta, 0.0)
        self.assertGreaterEqual(speed, 0.0)

        # String formatting helpers
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_duration(65), "1m 05s")


if __name__ == "__main__":
    unittest.main()
