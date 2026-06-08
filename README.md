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

The project root is intentionally simple. The user only needs these visible files:

- `run.vbs` - double-click this file to start the tool without showing a terminal window.
- `README.md` - this guide.

The application files are stored in the hidden `.pdf_to_md_internal` folder. Do not move, rename, or delete that folder.

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

On the first run, the tool checks the required Python libraries and installs anything missing from the internal requirements file.

The required libraries are:

- `pypdf`
- `python-docx`
- `python-pptx`

If the libraries are already installed, the tool starts normally.

If nothing appears immediately, wait up to a minute on the first run. Installing libraries can take a little time, especially on a slow internet connection.

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

## Troubleshooting

### The Tool Does Not Open

Wait one minute first. The first launch may be installing Python libraries in the background.

If it still does not open, check the launcher log file in the hidden internal folder:

```text
.pdf_to_md_internal\pdf_to_md_launcher.log
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

Try opening Command Prompt and running:

```bat
python -m pip install -r ".pdf_to_md_internal\requirements.txt"
```

Run that command from the project folder.

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
- the hidden `.pdf_to_md_internal` folder

The other person should extract the folder, open it, and double-click:

```text
run.vbs
```

They do not need to install the Python libraries manually. The launcher checks and installs them automatically.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
