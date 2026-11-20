from __future__ import annotations

import json
import queue
import shutil
import subprocess
import tempfile
import threading
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv",
    ".flv", ".mpeg", ".mpg", ".mts", ".m2ts", ".mp3", ".m4a",
    ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma",
}


class MediaToMp3App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Media to MP3")
        self.geometry("900x650")
        self.minsize(760, 540)

        self.inputs: list[Path] = []
        self.events: queue.Queue[tuple] = queue.Queue()
        self.cancel_event = threading.Event()
        self.current_process: subprocess.Popen | None = None
        self.worker: threading.Thread | None = None

        self.output_dir = tk.StringVar(value=str(Path.home() / "Music" / "Converted MP3"))
        self.split_mode = tk.StringVar(value="Full MP3")
        self.chunk_minutes = tk.StringVar(value="30")
        self.quality = tk.StringVar(value="High (VBR ~190 kbps)")
        self.status = tk.StringVar(value="Add files, folders, or ZIP archives to begin.")

        self._build_ui()
        self.after(100, self._drain_events)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Media to MP3", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Batch convert videos, audio files, folders, and ZIP archives locally.",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self, padding=(16, 4, 16, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        buttons = ttk.Frame(body)
        buttons.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(buttons, text="Add files", command=self._add_files).pack(side="left")
        ttk.Button(buttons, text="Add folder", command=self._add_folder).pack(side="left", padx=6)
        ttk.Button(buttons, text="Add ZIP", command=self._add_zip).pack(side="left")
        ttk.Button(buttons, text="Remove selected", command=self._remove_selected).pack(side="right")
        ttk.Button(buttons, text="Clear", command=self._clear_inputs).pack(side="right", padx=6)

        list_frame = ttk.Frame(body)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.input_list = tk.Listbox(list_frame, selectmode="extended")
        self.input_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.input_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.input_list.configure(yscrollcommand=scrollbar.set)

        options = ttk.LabelFrame(body, text="Conversion options", padding=10)
        options.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        options.columnconfigure(1, weight=1)

        ttk.Label(options, text="Output folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(options, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew")
        ttk.Button(options, text="Browse", command=self._choose_output).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(options, text="Duration").grid(row=1, column=0, sticky="w", pady=(9, 0))
        split_box = ttk.Combobox(
            options,
            textvariable=self.split_mode,
            values=("Full MP3", "Two equal halves", "Fixed-length parts"),
            state="readonly",
            width=23,
        )
        split_box.grid(row=1, column=1, sticky="w", pady=(9, 0))
        split_box.bind("<<ComboboxSelected>>", lambda _event: self._sync_chunk_state())

        chunk_frame = ttk.Frame(options)
        chunk_frame.grid(row=1, column=2, sticky="e", pady=(9, 0))
        ttk.Label(chunk_frame, text="Minutes per part").pack(side="left", padx=(0, 6))
        self.chunk_entry = ttk.Entry(chunk_frame, textvariable=self.chunk_minutes, width=7, state="disabled")
        self.chunk_entry.pack(side="left")

        ttk.Label(options, text="Quality").grid(row=2, column=0, sticky="w", pady=(9, 0))
        ttk.Combobox(
            options,
            textvariable=self.quality,
            values=("Best (VBR ~245 kbps)", "High (VBR ~190 kbps)", "Small (128 kbps)"),
            state="readonly",
            width=23,
        ).grid(row=2, column=1, sticky="w", pady=(9, 0))

        footer = ttk.Frame(self, padding=(16, 4, 16, 16))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 7))
        ttk.Label(footer, textvariable=self.status).grid(row=1, column=0, sticky="w")
        self.cancel_button = ttk.Button(footer, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_button.grid(row=1, column=1, sticky="e", padx=(8, 0))
        self.convert_button = ttk.Button(footer, text="Convert to MP3", command=self._start)
        self.convert_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _sync_chunk_state(self) -> None:
        state = "normal" if self.split_mode.get() == "Fixed-length parts" else "disabled"
        self.chunk_entry.configure(state=state)

    def _add_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Choose media files",
            filetypes=(("Media files", " ".join(f"*{ext}" for ext in sorted(MEDIA_EXTENSIONS))), ("All files", "*.*")),
        )
        self._add_paths(Path(item) for item in selected)

    def _add_folder(self) -> None:
        selected = filedialog.askdirectory(title="Choose a folder")
        if selected:
            self._add_paths([Path(selected)])

    def _add_zip(self) -> None:
        selected = filedialog.askopenfilenames(title="Choose ZIP archives", filetypes=(("ZIP archives", "*.zip"),))
        self._add_paths(Path(item) for item in selected)

    def _add_paths(self, paths) -> None:
        known = {str(path.resolve()).lower() for path in self.inputs}
        for path in paths:
            key = str(path.resolve()).lower()
            if path.exists() and key not in known:
                self.inputs.append(path)
                self.input_list.insert("end", str(path))
                known.add(key)
        self.status.set(f"{len(self.inputs)} input item(s) selected.")

    def _remove_selected(self) -> None:
        for index in reversed(self.input_list.curselection()):
            self.input_list.delete(index)
            del self.inputs[index]
        self.status.set(f"{len(self.inputs)} input item(s) selected.")

    def _clear_inputs(self) -> None:
        self.inputs.clear()
        self.input_list.delete(0, "end")
        self.status.set("Add files, folders, or ZIP archives to begin.")

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if selected:
            self.output_dir.set(selected)

    def _start(self) -> None:
        if not self.inputs:
            messagebox.showwarning("No input", "Add at least one file, folder, or ZIP archive.")
            return
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            messagebox.showerror("FFmpeg not found", "Install FFmpeg and make sure ffmpeg and ffprobe are on PATH.")
            return

        chunk_seconds = None
        if self.split_mode.get() == "Fixed-length parts":
            try:
                minutes = float(self.chunk_minutes.get())
                if minutes <= 0:
                    raise ValueError
                chunk_seconds = minutes * 60
            except ValueError:
                messagebox.showwarning("Invalid duration", "Minutes per part must be a number greater than zero.")
                return

        output = Path(self.output_dir.get()).expanduser()
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            messagebox.showerror("Output folder error", str(error))
            return

        self.cancel_event.clear()
        self.convert_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(value=0, maximum=1)
        self.status.set("Scanning input items…")
        self.worker = threading.Thread(
            target=self._convert_all,
            args=(list(self.inputs), output, self.split_mode.get(), chunk_seconds, self.quality.get()),
            daemon=True,
        )
        self.worker.start()

    def _cancel(self) -> None:
        self.cancel_event.set()
        process = self.current_process
        if process and process.poll() is None:
            process.terminate()
        self.status.set("Cancelling…")

    def _convert_all(self, inputs: list[Path], output: Path, split_mode: str, chunk_seconds: float | None, quality: str) -> None:
        failures: list[str] = []
        converted = 0
        with tempfile.TemporaryDirectory(prefix="media_to_mp3_") as temporary:
            files = self._discover_media(inputs, Path(temporary), failures)
            self.events.put(("maximum", max(len(files), 1)))
            for index, source in enumerate(files, start=1):
                if self.cancel_event.is_set():
                    break
                self.events.put(("status", f"Converting {index}/{len(files)}: {source.name}"))
                try:
                    self._convert_one(source, output, split_mode, chunk_seconds, quality)
                    converted += 1
                except Exception as error:
                    failures.append(f"{source}: {error}")
                self.events.put(("progress", index))
        self.events.put(("done", converted, failures, self.cancel_event.is_set(), str(output)))

    def _discover_media(self, inputs: list[Path], temporary: Path, failures: list[str]) -> list[Path]:
        found: list[Path] = []
        seen: set[str] = set()
        for item_index, item in enumerate(inputs):
            if self.cancel_event.is_set():
                break
            candidates: list[Path]
            if item.is_dir():
                candidates = [path for path in item.rglob("*") if path.is_file()]
            elif item.suffix.lower() == ".zip":
                extract_to = temporary / f"zip_{item_index}"
                try:
                    with zipfile.ZipFile(item) as archive:
                        safe_members = []
                        root = extract_to.resolve()
                        for member in archive.infolist():
                            target = (extract_to / member.filename).resolve()
                            if target == root or root in target.parents:
                                safe_members.append(member)
                        archive.extractall(extract_to, safe_members)
                    candidates = [path for path in extract_to.rglob("*") if path.is_file()]
                except (OSError, zipfile.BadZipFile) as error:
                    failures.append(f"{item}: cannot open ZIP ({error})")
                    continue
            else:
                candidates = [item]

            for candidate in candidates:
                if candidate.suffix.lower() not in MEDIA_EXTENSIONS:
                    continue
                key = str(candidate.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(candidate)
        return found

    def _duration(self, source: Path) -> float:
        command = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(source),
        ]
        result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffprobe could not read this file")
        return float(json.loads(result.stdout)["format"]["duration"])

    def _convert_one(self, source: Path, output: Path, split_mode: str, chunk_seconds: float | None, quality: str) -> None:
        quality_args = {
            "Best (VBR ~245 kbps)": ["-q:a", "0"],
            "High (VBR ~190 kbps)": ["-q:a", "2"],
            "Small (128 kbps)": ["-b:a", "128k"],
        }[quality]
        base = self._unique_base(output, source.stem)

        if split_mode == "Full MP3":
            jobs = [(0.0, None, output / f"{base}.mp3")]
        elif split_mode == "Two equal halves":
            half = self._duration(source) / 2
            jobs = [
                (0.0, half, output / f"{base}_first_half.mp3"),
                (half, None, output / f"{base}_last_half.mp3"),
            ]
        else:
            duration = self._duration(source)
            assert chunk_seconds is not None
            jobs = []
            start = 0.0
            part = 1
            while start < duration:
                jobs.append((start, min(chunk_seconds, duration - start), output / f"{base}_part_{part:03d}.mp3"))
                start += chunk_seconds
                part += 1

        for start, length, destination in jobs:
            if self.cancel_event.is_set():
                return
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
            if start:
                command += ["-ss", f"{start:.6f}"]
            command += ["-i", str(source)]
            if length is not None:
                command += ["-t", f"{length:.6f}"]
            command += [
                "-map", "0:a:0", "-af", "aresample=async=1:first_pts=0",
                "-c:a", "libmp3lame", *quality_args, str(destination),
            ]
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _, error = self.current_process.communicate()
            return_code = self.current_process.returncode
            self.current_process = None
            if return_code != 0 and not self.cancel_event.is_set():
                destination.unlink(missing_ok=True)
                raise RuntimeError(error.strip() or "FFmpeg conversion failed")

    @staticmethod
    def _unique_base(output: Path, stem: str) -> str:
        candidate = stem
        number = 2
        while any(output.glob(f"{candidate}*.mp3")):
            candidate = f"{stem}_{number}"
            number += 1
        return candidate

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "status":
                    self.status.set(event[1])
                elif event[0] == "maximum":
                    self.progress.configure(maximum=event[1])
                elif event[0] == "progress":
                    self.progress.configure(value=event[1])
                elif event[0] == "done":
                    self._finish(*event[1:])
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _finish(self, converted: int, failures: list[str], cancelled: bool, output: str) -> None:
        self.convert_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        if cancelled:
            self.status.set(f"Cancelled. {converted} file(s) completed.")
            return
        self.status.set(f"Done. {converted} file(s) converted; {len(failures)} failed.")
        if failures:
            details = "\n\n".join(failures[:8])
            if len(failures) > 8:
                details += f"\n\n…and {len(failures) - 8} more."
            messagebox.showwarning("Conversion finished with errors", details)
        else:
            if messagebox.askyesno("Conversion complete", f"Converted {converted} file(s).\n\nOpen the output folder?"):
                subprocess.Popen(["explorer", output])


if __name__ == "__main__":
    MediaToMp3App().mainloop()
