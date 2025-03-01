# Interactive Rust Optimizer (OpenAI)

**A powerful Python3 script utilizing OpenAI's GPT models to optimize, debug, restructure, and thoroughly comment your Rust source code.**

---

## Overview

This powerful Python3 script leverages OpenAI's GPT models to optimize, debug, restructure, and thoroughly comment your Rust source code. In the latest update, the tool includes:

- Advanced interactive file selection with improved keyboard shortcuts.
- Automatic, timestamped backups of selected files.
- Detailed summary report generation including model used, processed files, and compilation results.
- Robust error handling and logging.
- Persistent user configuration for selected files and models.

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

1. **Model Selection:** Choose the OpenAI GPT model for processing.
2. **File Selection:** Navigate directories interactively and select files to optimize.
3. **Backup:** Original files are automatically backed up with a timestamp.
4. **Optimization:** Selected files are sent to OpenAI for processing.
5. **Compilation Check (Optional):** Choose to compile either the original or optimized files using `cargo build`.
6. **Output:** Optimized files and a detailed summary report are saved in the `OpenAI` directory, and activities are logged.
7. **Configuration:** Preferences such as selected models are automatically saved and loaded for convenience.

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
