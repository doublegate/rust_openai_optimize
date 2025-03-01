# Interactive Rust Optimizer (OpenAI)

**A powerful Python3 script utilizing OpenAI's GPT models to optimize, debug, restructure, and thoroughly comment your Rust source code.**

---

## Overview

This script leverages OpenAI's advanced language models to significantly enhance Rust code projects by:

- **Detecting and removing errors and bugs.**
- **Restructuring code for efficiency and compactness.**
- **Adding detailed technical comments throughout the code.**
- **Ensuring compatibility across multiple Rust source files.**
- **Verifying successful compilation with `cargo build`.**
- **Generating a comprehensive summary report after processing.**

## Features

- **Interactive Terminal Interface:** Navigate and select files intuitively using keyboard shortcuts.
- **Automatic Backup:** Creates timestamped backups of original files before processing.
- **Detailed Activity Logging:** Maintains logs of all actions, including backups, model usage, and compilation results.
- **Configurable OpenAI Models:** Easily select between available GPT models.
- **Recursive File Selection:** Supports deep directory navigation and file selection.
- **Summary Reports:** Automatically generates a summary report detailing processed files, compilation results, and more.
- **Enhanced Terminal Output:** Utilizes the `rich` library for improved readability and user experience.
- **Optional Compilation Step:** Choose whether to run `cargo build` before exiting.
- **Source Code Flexibility:** Choose between compiling original files or the newly optimized files.
- **Configuration Files:** Automatically saves and loads user preferences, including the selected OpenAI model.

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

## Planned Features

- **Git Integration:** Automatically stage and commit changes.
- **Dry-Run Mode:** Preview changes before applying.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contributions

Contributions and feature requests are welcome! Feel free to submit issues or pull requests on GitHub.
