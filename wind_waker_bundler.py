#!/usr/bin/env python3
"""Create uncompressed Zip64 Wind Waker mod bundles via CLI or GUI."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional
from zipfile import ZIP_STORED, ZipFile

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

ProgressCallback = Callable[[int, int, Path, int], None]
LogCallback = Callable[[str], None]


class BundleEngine:
    """Core logic for creating uncompressed Zip64 archives."""

    @staticmethod
    def scan_files(stage_dir: Path) -> list[Path]:
        """Return all regular files below *stage_dir* in deterministic order."""
        if not stage_dir.is_dir():
            raise FileNotFoundError(f"Stage directory does not exist: {stage_dir}")
        files = sorted(path for path in stage_dir.rglob("*") if path.is_file())
        if not files:
            raise ValueError(f"No files found in directory: {stage_dir}")
        return files

    @staticmethod
    def create_bundle(
        stage_dir: Path,
        output_file: Path,
        replace_empty: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ) -> None:
        """Create an uncompressed archive with the stage folder at its root."""
        stage = stage_dir.resolve()
        output = output_file.resolve()

        if log_callback:
            log_callback(f"Scanning folder: {stage}")
        files = BundleEngine.scan_files(stage)

        # Never let an output inside the source tree archive itself.
        files = [path for path in files if path.resolve() != output]
        if not files:
            raise ValueError(f"No input files found in directory: {stage}")

        total_files = len(files)
        total_bytes = sum(path.stat().st_size for path in files)
        if log_callback:
            log_callback(
                f"Found {total_files} files ({total_bytes / (1024 * 1024):.2f} MB total)."
            )

        if output.exists():
            if not replace_empty or output.stat().st_size != 0:
                raise FileExistsError(f"Refusing to overwrite existing file: {output}")
            output.unlink()
        output.parent.mkdir(parents=True, exist_ok=True)

        if log_callback:
            log_callback(f"Writing uncompressed Zip64 archive to: {output}")
        processed_bytes = 0
        try:
            with ZipFile(output, "x", compression=ZIP_STORED, allowZip64=True) as archive:
                for index, file_path in enumerate(files, start=1):
                    relative_path = file_path.relative_to(stage)
                    archive.write(
                        file_path,
                        arcname=(Path(stage.name) / relative_path).as_posix(),
                    )
                    processed_bytes += file_path.stat().st_size
                    if progress_callback:
                        progress_callback(
                            index, total_files, relative_path, processed_bytes
                        )
        except Exception:
            output.unlink(missing_ok=True)
            raise

        if log_callback:
            log_callback(f"Successfully created bundle: {output}")


if HAS_TKINTER:

    class BundlerGUI:
        """Tkinter interface for :class:`BundleEngine`."""

        def __init__(self, default_stage: str) -> None:
            self.root = tk.Tk()
            self.root.title("Wind Waker Mod Bundler (Link + Linkle)")
            self.root.geometry("640x520")
            self.root.minsize(550, 450)
            self.default_stage = default_stage
            self.is_running = False
            self._configure_styles()
            self._build_ui()

        def _configure_styles(self) -> None:
            style = ttk.Style()
            style.theme_use("clam")
            self.bg_color = "#1e1e2e"
            self.fg_color = "#cdd6f4"
            self.accent_color = "#89b4fa"
            self.card_bg = "#313244"
            self.root.configure(bg=self.bg_color)
            style.configure("TFrame", background=self.bg_color)
            style.configure("Card.TFrame", background=self.card_bg, relief="flat")
            style.configure(
                "TLabel", background=self.bg_color, foreground=self.fg_color,
                font=("Segoe UI", 10)
            )
            style.configure(
                "Card.TLabel", background=self.card_bg, foreground=self.fg_color,
                font=("Segoe UI", 10)
            )
            style.configure(
                "Title.TLabel", background=self.bg_color,
                foreground=self.accent_color, font=("Segoe UI", 14, "bold")
            )
            style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
            style.configure(
                "Accent.TButton", background=self.accent_color, foreground="#11111b"
            )

        def _build_ui(self) -> None:
            main = ttk.Frame(self.root, padding="15")
            main.pack(fill=tk.BOTH, expand=True)
            ttk.Label(
                main, text="Wind Waker Mod Bundle Creator", style="Title.TLabel"
            ).pack(anchor="w", pady=(0, 5))
            ttk.Label(
                main,
                text="Packages Link + Linkle mod files into an uncompressed Zip64 archive.",
                font=("Segoe UI", 9, "italic"),
            ).pack(anchor="w", pady=(0, 15))

            card = ttk.Frame(main, style="Card.TFrame", padding="12")
            card.pack(fill=tk.X, pady=(0, 15))
            ttk.Label(card, text="Source Folder (Stage):", style="Card.TLabel").grid(
                row=0, column=0, sticky="w", pady=4
            )
            self.stage_var = tk.StringVar(value=self.default_stage)
            ttk.Entry(card, textvariable=self.stage_var, width=45).grid(
                row=0, column=1, padx=8, pady=4, sticky="ew"
            )
            ttk.Button(card, text="Browse...", command=self._browse_stage).grid(
                row=0, column=2, pady=4
            )
            ttk.Label(card, text="Output Zip File:", style="Card.TLabel").grid(
                row=1, column=0, sticky="w", pady=4
            )
            default_output = str(Path(self.default_stage).parent / "wind_waker_bundle.zip")
            self.output_var = tk.StringVar(value=default_output)
            ttk.Entry(card, textvariable=self.output_var, width=45).grid(
                row=1, column=1, padx=8, pady=4, sticky="ew"
            )
            ttk.Button(card, text="Browse...", command=self._browse_output).grid(
                row=1, column=2, pady=4
            )
            card.columnconfigure(1, weight=1)

            self.progress_label = ttk.Label(main, text="Ready to create bundle.")
            self.progress_label.pack(anchor="w", pady=(5, 2))
            self.progress_bar = ttk.Progressbar(main, mode="determinate", maximum=100)
            self.progress_bar.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(main, text="Activity Log:").pack(anchor="w", pady=(5, 2))
            self.log_text = tk.Text(
                main, height=10, bg="#11111b", fg="#a6adc8",
                font=("Consolas", 9), relief="flat"
            )
            self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            buttons = ttk.Frame(main)
            buttons.pack(fill=tk.X)
            self.build_btn = ttk.Button(
                buttons, text="Build Zip64 Bundle", style="Accent.TButton",
                command=self._start_build
            )
            self.build_btn.pack(side=tk.RIGHT, padx=5)
            ttk.Button(buttons, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)

        def _browse_stage(self) -> None:
            folder = filedialog.askdirectory(initialdir=self.stage_var.get())
            if folder:
                self.stage_var.set(folder)

        def _browse_output(self) -> None:
            path = filedialog.asksaveasfilename(
                defaultextension=".zip",
                filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")],
                initialfile="wind_waker_bundle.zip",
            )
            if path:
                self.output_var.set(path)

        def log(self, message: str) -> None:
            self.root.after(0, self._append_log, message)

        def _append_log(self, message: str) -> None:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)

        def _update_progress(
            self, index: int, total: int, current_file: Path, processed_bytes: int
        ) -> None:
            del processed_bytes
            self.root.after(
                0, self._apply_progress, (index / total) * 100,
                f"[{index}/{total}] Adding: {current_file}"
            )

        def _apply_progress(self, percent: float, text: str) -> None:
            self.progress_bar["value"] = percent
            self.progress_label.config(text=text)

        def _start_build(self) -> None:
            if self.is_running:
                return
            stage = Path(self.stage_var.get().strip())
            output = Path(self.output_var.get().strip())
            if not stage.is_dir():
                messagebox.showerror("Error", f"Source folder does not exist:\n{stage}")
                return
            if output.exists() and not messagebox.askyesno(
                "Overwrite Warning", f"File exists:\n{output}\n\nOverwrite it?"
            ):
                return
            if output.exists():
                try:
                    output.unlink()
                except OSError as error:
                    messagebox.showerror("Error", f"Could not remove existing file:\n{error}")
                    return
            self.is_running = True
            self.build_btn.config(state=tk.DISABLED)
            self.progress_bar["value"] = 0
            self.log_text.delete("1.0", tk.END)
            threading.Thread(
                target=self._run_build_worker, args=(stage, output), daemon=True
            ).start()

        def _run_build_worker(self, stage: Path, output: Path) -> None:
            try:
                started = time.time()
                BundleEngine.create_bundle(
                    stage, output, replace_empty=True,
                    progress_callback=self._update_progress, log_callback=self.log
                )
                self.log(f"Done in {time.time() - started:.2f} seconds!")
                self.root.after(
                    0, messagebox.showinfo, "Success",
                    f"Bundle created successfully!\n\n{output}"
                )
            except Exception as error:
                self.log(f"ERROR: {error}")
                self.root.after(0, messagebox.showerror, "Build Failed", str(error))
            finally:
                self.is_running = False
                self.root.after(0, lambda: self.build_btn.config(state=tk.NORMAL))

        def run(self) -> None:
            self.root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Zip64-compatible, uncompressed Link + Linkle bundle."
    )
    parser.add_argument("--stage", type=Path, help="Source folder containing mod files")
    parser.add_argument("--output", type=Path, help="Destination .zip file")
    parser.add_argument(
        "--replace-empty", action="store_true",
        help="replace only a pre-existing zero-byte incomplete archive"
    )
    parser.add_argument("--gui", action="store_true", help="open the graphical interface")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if (args.stage is None) != (args.output is None):
        print("Error: --stage and --output must be specified together.", file=sys.stderr)
        return 2
    if args.stage is not None and args.output is not None and not args.gui:
        try:
            BundleEngine.create_bundle(
                args.stage, args.output, replace_empty=args.replace_empty,
                progress_callback=lambda index, total, path, _: print(
                    f"[{index}/{total}] {path}", flush=True
                ),
                log_callback=print,
            )
            return 0
        except Exception as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
    if HAS_TKINTER:
        default_stage = str(args.stage) if args.stage else os.getcwd()
        BundlerGUI(default_stage).run()
        return 0
    print(
        "GUI mode unavailable (Tkinter not found). Specify --stage and --output.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
