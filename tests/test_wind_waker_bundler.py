import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from wind_waker_bundler import BundleEngine, main


class BundleEngineTests(unittest.TestCase):
    def test_creates_stored_archive_and_reports_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            (stage / "nested").mkdir(parents=True)
            (stage / "a.txt").write_text("alpha", encoding="utf-8")
            (stage / "nested" / "b.bin").write_bytes(b"beta")
            output = root / "bundle.zip"
            progress = []

            BundleEngine.create_bundle(
                stage, output, progress_callback=lambda *args: progress.append(args)
            )

            with ZipFile(output) as archive:
                self.assertEqual(
                    archive.namelist(), ["stage/a.txt", "stage/nested/b.bin"]
                )
                self.assertTrue(
                    all(item.compress_type == ZIP_STORED for item in archive.infolist())
                )
            self.assertEqual(progress[-1][:2], (2, 2))
            self.assertEqual(progress[-1][3], 9)

    def test_refuses_to_overwrite_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            stage.mkdir()
            (stage / "file").write_text("data", encoding="utf-8")
            output = root / "bundle.zip"
            output.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                BundleEngine.create_bundle(stage, output, replace_empty=True)

    def test_replace_empty_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            stage.mkdir()
            (stage / "file").write_text("data", encoding="utf-8")
            output = root / "bundle.zip"
            output.touch()
            BundleEngine.create_bundle(stage, output, replace_empty=True)
            self.assertGreater(output.stat().st_size, 0)

    def test_cli_requires_stage_and_output_together(self) -> None:
        self.assertEqual(main(["--stage", "somewhere"]), 2)


if __name__ == "__main__":
    unittest.main()
