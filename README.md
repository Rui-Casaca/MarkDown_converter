# Document to Markdown Converter

This tool converts PDF, Word DOCX, and PowerPoint PPTX files into clean Markdown files.

It is designed for Windows and includes a simple graphical interface. You do not need to run commands manually in normal use.

## What This Tool Does

Use this tool when you want to turn documents into `.md` Markdown files for reading, summarising, AI/RAG workflows, notes, or documentation.

Supported input files:

- PDF: `.pdf`
- Word: `.docx`
- PowerPoint: `.pptx`

The generated Markdown files use the `.md` extension.

## Files Included

The project root keeps the everyday entry points simple:

- `run.vbs` - double-click this file to start the tool without showing a terminal window.
- `README.md` - this guide.

The application itself is a Python package in the `src/doc2md` folder, and the launcher helper lives in `scripts/`. Do not move, rename, or delete those folders.

## Before You Start

Assuming you are using Windows: You need Python installed.

### Step 1 - Check If Python Is Installed

1. Open the Windows Start menu.
2. Type `cmd`.
3. Open Command Prompt.
4. Type this command and press Enter:

```bat
python --version
```

If you see a Python version, for example `Python 3.12.5`, Python is installed.

If Windows says Python is not recognised, install Python first.

### Step 2 - Install Python If Needed

1. Go to https://www.python.org/downloads/windows/
2. Download the latest Python 3 installer for Windows.
3. Run the installer.
4. On the first installer screen, tick this option:

```text
Add python.exe to PATH
```

5. Click `Install Now`.
6. When installation finishes, close the installer.
7. Restart the computer if Python is still not detected.

## How To Start The Tool

1. Open the folder that contains this project.
2. Double-click this file:

```text
run.vbs
```

3. Wait a moment.

On the first run, the tool creates a private virtual environment in a `.venv` folder next to the project and installs the application and its required Python libraries into it.

The required libraries are:

- `pypdf`
- `python-docx`
- `python-pptx`
- `pdfminer.six`

After this one-time setup, later launches reuse the same environment and start immediately, without checking or reinstalling anything. The tool only reinstalls when the application version changes.

If nothing appears immediately, wait up to a minute on the first run. Creating the environment and installing the libraries can take a little time, especially on a slow internet connection.

## How To Convert A Single File

1. Start the tool by double-clicking `run.vbs`.
2. In `Input mode`, choose `Single file`.
3. Click `Select file...`.
4. Choose a `.pdf`, `.docx`, or `.pptx` file.
5. In `Output Markdown`, check where the output `.md` file will be saved.
6. To choose a different output location, click `Save as...`.
7. Leave the default conversion options enabled unless you have a specific reason to change them.
8. Click `Convert`.
9. Wait until the progress area says the conversion is complete.

## How To Convert Multiple Files

1. Start the tool.
2. In `Input mode`, choose `Multiple files`.
3. Click `Select files...`.
4. Select one or more `.pdf`, `.docx`, or `.pptx` files.
5. Choose which formats are enabled in `Format selection`.
6. Click `Convert`.

The converted Markdown files are saved in a folder named:

```text
MarkDowns_converted
```

This folder is created next to the selected documents.

## How To Convert A Folder

1. Start the tool.
2. In `Input mode`, choose `Folder`.
3. Click `Select folder...`.
4. Choose the folder that contains the documents.
5. In `Format selection`, tick the document types you want to convert.
6. If you also want to scan folders inside the selected folder, tick `Include subfolders`.
7. Click `Convert`.

The converted Markdown files are saved in a folder named:

```text
MarkDowns_converted
```

When `Include subfolders` is enabled, the output keeps the same folder structure inside `MarkDowns_converted`.

## Recommended Settings

The default settings are usually the best choice:

- `Include document metadata`
- `Include page/slide separators`
- `Detect headings automatically`
- `Normalize whitespace`
- `Optimize Markdown for AI reading`
- `Overwrite existing Markdown files`

Untick `Overwrite existing Markdown files` if you do not want the tool to replace existing `.md` files.

## Changing the Language

The interface is available in English and Portuguese. Use the `Language` selector at the top-right corner of the window to switch between them. Your choice is remembered for the next time you open the tool.

The generated Markdown content is always written with English structural labels, regardless of the interface language.

## Troubleshooting

### The Tool Does Not Open

Wait one minute first. The first launch may be installing Python libraries in the background.

If it still does not open, check the launcher log file in the `scripts` folder:

```text
scripts\pdf_to_md_launcher.log
```

Open it with Notepad and read the last lines. They usually explain the problem.

### The Log Says Python Was Not Found

Install Python from https://www.python.org/downloads/windows/ and make sure `Add python.exe to PATH` is selected during installation.

After installing Python, try opening `run.vbs` again.

### The Log Says Packages Could Not Be Installed

This usually means one of these things:

- the computer has no internet connection;
- Python cannot access `pip`;
- antivirus or company security policy blocked the installation;
- the user does not have permission to install Python packages.

The simplest fix is to delete the `.venv` folder in the project and double-click `run.vbs` again, which rebuilds the environment from scratch.

Alternatively, open Command Prompt in the project folder and run:

```bat
python -m pip install -e .
```

### A Terminal Window Flashes Briefly

Use this file to start the tool:

```text
run.vbs
```

The `.vbs` launcher starts the `.bat` helper hidden.

If you double-click the `.bat` file directly, Windows may briefly show a terminal window.

### The Conversion Fails For One Document

Check the log area inside the application. Some PDFs, Word files, or PowerPoint files may be encrypted, corrupted, scanned as images, or protected against text extraction.

Try another document to confirm the tool itself is working.

## Sharing This Tool With Someone Else

Send the whole folder with these files:

- `run.vbs`
- `README.md`
- the `src` and `scripts` folders
- `pyproject.toml`

The other person should extract the folder, open it, and double-click:

```text
run.vbs
```

They do not need to install the Python libraries manually. The launcher builds its own environment and installs everything automatically on the first run.

## Running From Source (Developers)

This tool is packaged as a standard Python project. To run it from a clone of the repository:

```bat
python -m pip install -e .
python -m doc2md
```

Install the optional development tools with `python -m pip install -e .[dev]` and run `ruff check .` to lint.

## Building a Standalone Executable

You can package the tool as a single Windows executable that runs without a separate Python installation. This is convenient for sharing with people who do not have Python.

From the project folder, run:

```text
scripts\build_exe.bat
```

This installs the build dependencies and produces `dist\doc2md.exe`. You can then share that single file; double-clicking it starts the application directly.

To build manually instead:

```bat
python -m pip install -e .[build]
python -m PyInstaller --noconfirm --clean doc2md.spec
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
