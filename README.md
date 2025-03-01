# Interactive Rust Optimizer (OpenAI)

**A powerful Python3 script utilizing OpenAI's GPT models to optimize, debug, restructure, and thoroughly comment your Rust source code.**

---

## Overview

This powerful Python3 script leverages OpenAI's GPT models to optimize, debug, restructure, and thoroughly comment your Rust source code. In the latest update, the tool now includes:

- Advanced interactive file selection with improved keyboard shortcuts.
- Automatic, timestamped backups of selected files.
- Detailed summary report generation including model used, processed files, and compilation results.
- Robust error handling with structured logging.
- Persistent configuration saving.
- Support for command-line arguments to run in non-interactive, asynchronous, or test modes.
- Optional error notifications via email.

## Features

- **Interactive Terminal Interface:** Enhanced navigation and file selection using Prompt Toolkit with custom key bindings.
- **Automatic Backup:** Creates timestamped backups of original files before processing.
- **Detailed Activity Logging:** Maintains logs of all actions (backups, model usage, compilation results) in an `activity.log` file.
- **Configurable OpenAI Models & Persistence:** Save preferred models and selected files for future runs.
- **Recursive File Selection:** Supports deep directory navigation and quick file selection.
- **Summary Reports:** Generates a detailed report (in `OpenAI/summary_report.txt`) with processing details and compilation status.
- **Optional Compilation Check:** Choose to compile either the original or the optimized files using `cargo build`.
- **Enhanced Error Handling:** Verifies tool availability (cargo), and robustly handles API and file I/O errors.

## Installation

### Prerequisites

- Python 3.8 or newer
- An active [OpenAI API key](https://platform.openai.com/api-keys)

### Dependencies

Install required Python libraries:

```bash
pip install openai prompt_toolkit tqdm rich
```

## Setup

1. Clone the repository:

```bash
git clone <your_repository_url>
cd <repository_folder>
```

2. Set your OpenAI API Key as an environment variable:

- On **Linux/macOS**:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

- On **Windows** (PowerShell):

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

Alternatively, edit the script to set your key directly:

```python
client = openai.OpenAI(api_key="your-api-key-here")
```

## Usage

Run the script using Python:

```bash
python rust_openai_optimizer.py
```

### Interactive Commands

- `Enter`: Open directories or select Rust files (`*.rs`) or `Cargo.toml`.
- `Backspace`: Navigate up one directory.
- `d`: Finish file selection.
- `Tab`: Autocomplete filenames/directories.
- `esc/q`: Exit the program immediately.
- `?`: Display contextual help.

## Workflow

1. **Model & CLI Options:** Choose or pass the OpenAI model and other options through command-line arguments.
2. **File Selection:** Either through interactive prompts or CLI-provided file paths.
3. **Backup:** Create timestamped backups of original files.
4. **Optimization Process:** Aggregate and send source code to OpenAI using synchronous or asynchronous calls.
5. **Testing (Optional):** Run integrated unit tests using the `--test` flag.
6. **Compilation Check:** Optionally run `cargo build` on original or optimized files.
7. **Output & Reporting:** Save optimized files and generate a detailed summary report.

## What's New (v0.3.1)

- **CLI Argument Parsing:** Now supports options for model selection, file inputs, non-interactive mode, asynchronous processing (`--async-mode`), test execution (`--test`), and configuration via `--config`.
- **Asynchronous Processing:** Added async API calls for improved performance.
- **Unit & Integration Testing:** Included tests to verify file I/O and backup functionality.
- **Structured Logging:** Integrated Python's logging module for advanced, structured logging.
- **Error Notifications:** (Optional) Email notifications for critical errors are supported via configuration.
- Added formatting: reduced indentations and line lengths; removed unnecessary module(s)

## What's New (v0.2.0)

- Improved interactive CLI with refined navigation and help commands.
- Advanced backup process with timestamped directories.
- Detailed summary report generation detailing models used, files processed, and compilation outcomes.
- Persistent configuration settings for a seamless user experience.

## Planned Features

- **Git Integration:** Automatically stage and commit changes.
- **Dry-Run Mode:** Preview changes before applying.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contributions

Contributions and feature requests are welcome! Feel free to submit issues or pull requests on GitHub.
