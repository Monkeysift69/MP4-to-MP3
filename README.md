# MP4-to-MP3

A lightweight Windows desktop application for batch-converting video and audio files to MP3 with FFmpeg.

Everything runs locally on your computer. Files are not uploaded, and original media is never modified.

## Features

- Add one or many media files
- Scan complete folders and their subfolders
- Read media files contained in ZIP archives
- Convert each source into one full MP3
- Split each source into two equal MP3 halves
- Split each source into adjustable-length parts
- Choose between best, high, and compact MP3 quality
- Select a custom output folder
- Cancel a running batch
- Avoid overwriting existing output files

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer with Tkinter
- FFmpeg and FFprobe available on `PATH`

## Installation

### 1. Install Python

Download Python from [python.org](https://www.python.org/downloads/windows/).

During installation, enable **Add Python to PATH**. The standard Windows Python installer includes Tkinter.

Confirm the installation in PowerShell:

```powershell
python --version
```

### 2. Install FFmpeg

The easiest Windows installation uses WinGet:

```powershell
winget install --id Gyan.FFmpeg.Essentials --exact
```

Close and reopen PowerShell, then confirm both programs are available:

```powershell
ffmpeg -version
ffprobe -version
```

### 3. Download this application

Either download the repository as a ZIP from GitHub and extract it, or clone it:

```powershell
git clone https://github.com/Monkeysift69/MP4-to-MP3.git
cd MP4-to-MP3
```

No Python packages need to be installed. The application uses only Python's standard library.

## Running the application

Double-click:

```text
Start Media to MP3.bat
```

Alternatively, run it from PowerShell:

```powershell
python media_to_mp3.py
```

## How to use

1. Select **Add files**, **Add folder**, or **Add ZIP**.
2. Add as many sources as needed. Folder scanning includes subfolders.
3. Choose an output folder. The default is `Music\Converted MP3`.
4. Select a duration mode:
   - **Full MP3** creates one MP3 per source.
   - **Two equal halves** creates `_first_half.mp3` and `_last_half.mp3`.
   - **Fixed-length parts** creates numbered files such as `_part_001.mp3`. Enter the desired minutes per part.
5. Select the MP3 quality:
   - **Best** uses variable bitrate around 245 kbps.
   - **High** uses variable bitrate around 190 kbps.
   - **Small** uses a constant 128 kbps bitrate.
6. Select **Convert to MP3**.
7. When conversion finishes, choose whether to open the output folder.

Existing files are not overwritten. If a name is already used, the application adds a number to the new filename.

## Supported input formats

Common supported extensions include:

`MP4`, `MKV`, `MOV`, `AVI`, `WebM`, `M4V`, `WMV`, `FLV`, `MPEG`, `MPG`, `MTS`, `M2TS`, `MP3`, `M4A`, `AAC`, `WAV`, `FLAC`, `OGG`, `Opus`, and `WMA`.

Actual codec support depends on the installed FFmpeg build.

## ZIP handling

ZIP archives are extracted into a temporary folder during conversion. Temporary extracted files are automatically cleaned up afterward. The original ZIP remains unchanged.

## Troubleshooting

### FFmpeg not found

Restart the application after installing FFmpeg. Open a new PowerShell window and verify:

```powershell
ffmpeg -version
ffprobe -version
```

If either command fails, FFmpeg is not available on your system `PATH`.

### The application does not open

Run the following command from the project folder to see the error:

```powershell
python media_to_mp3.py
```

Also confirm that Tkinter is installed:

```powershell
python -c "import tkinter; print('Tkinter is ready')"
```

### A file fails to convert

Confirm that the source contains an audio stream and is playable. Some damaged files or unusual codecs may not be readable by the installed FFmpeg build.

## Privacy

All processing happens locally. The application does not use a server, analytics, or network upload.
