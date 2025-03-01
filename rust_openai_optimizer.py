#!/usr/bin/env python3
"""
======================================================================
rust_openai_optimizer.py - ver.0.2.0
======================================================================
Purpose:
  Optimize, debug, restructure, and add detailed comments to Rust source
  code by leveraging OpenAI's LLM API. The script enables interactive file
  selection (including Cargo.toml), sends the code for processing, and writes
  the optimized files to a new output directory while preserving the original
  project structure. This ensures that 'cargo build' can compile the optimized
  project correctly.

Usage:
  - Set the OPENAI_API_KEY environment variable.
  - Run this script from the terminal.
  - Follow interactive prompts to select files, choose an OpenAI model,
    and optionally run 'cargo build' to verify the optimized project.

Author:
  DoubleGate -- 2025: https://github.com/doublegate/rust_openai_optimize

Note:
  The script contains extensive error handling and logging to ensure robustness
  in various runtime environments.
======================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================
import os              # Provides OS-level interfaces: file paths, env variables, etc.
import subprocess      # Enables execution of external commands (e.g., "cargo build")
import sys             # Provides access to system-specific parameters and functions.
import shutil          # Facilitates high-level file operations such as copying files.
import json            # For serializing and deserializing configuration data.
from datetime import datetime  # To generate timestamps for backups and logging.
import time            # Allows pausing execution (used in retry/backoff mechanisms).
import random          # Used to introduce jitter into retry delays.
import signal          # To handle termination signals gracefully.

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import openai          # Official OpenAI API client.

# -----------------------------------------------------------------------------
# Attempt to import specific error classes from the OpenAI module.
# This addresses the error where "openai.error" is not found.
# If the import fails (perhaps due to a different package version),
# we fallback to using the base Exception class.
# -----------------------------------------------------------------------------
try:
    from openai.error import APIConnectionError, OpenAIError
except ImportError:
    APIConnectionError = Exception
    OpenAIError = Exception

from prompt_toolkit import PromptSession  # Enables interactive command-line sessions.
from prompt_toolkit.completion import PathCompleter  # Provides path autocompletion in CLI.
from prompt_toolkit.key_binding import KeyBindings  # Facilitates custom key bindings.
from tqdm import tqdm  # Displays progress bars for lengthy I/O operations.
from rich.console import Console  # Provides enhanced terminal output with styling.

# =============================================================================
# Global Object Initialization and Environment Checks
# =============================================================================
console = Console()

# Ensure the OPENAI_API_KEY is set; if not, exit with a clear error message.
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    console.print("Error: OPENAI_API_KEY environment variable is not set. Exiting.", style="red")
    sys.exit(1)

# =============================================================================
# Helper Functions
# =============================================================================
def read_file(filepath):
    """
    Reads the entire contents of a file and returns it as a string.

    Parameters:
      filepath (str): The absolute or relative path to the file.

    Returns:
      str: The content of the file.

    Raises:
      SystemExit: If the file cannot be read, the error is logged and the script exits.

    Implementation Details:
      - Uses a try/except block to catch and log I/O errors.
      - Exits the script if reading fails.
    """
    try:
        with open(filepath, 'r') as file:
            return file.read()
    except Exception as e:
        console.print(f"Error reading file '{filepath}': {e}", style="red")
        log_activity(f"Error reading file '{filepath}': {e}")
        sys.exit(1)

def write_file(filepath, content):
    """
    Writes content to a file, overwriting the file if it exists.

    Parameters:
      filepath (str): The absolute or relative path where the file should be written.
      content (str): The string content to be written to the file.

    Returns:
      None

    Raises:
      SystemExit: If writing the file fails, the error is logged and the script exits.

    Implementation Details:
      - Uses a try/except block to capture and log exceptions during file writing.
    """
    try:
        with open(filepath, 'w') as file:
            file.write(content)
    except Exception as e:
        console.print(f"Error writing file '{filepath}': {e}", style="red")
        log_activity(f"Error writing file '{filepath}': {e}")
        sys.exit(1)

def clear_screen():
    """
    Clears the terminal screen.

    Behavior:
      - On Windows: Executes the 'cls' command.
      - On Unix-like systems: Executes the 'clear' command.

    Returns:
      None
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def backup_files(files, backup_dir="backups"):
    """
    Creates a timestamped backup of the specified files.

    Parameters:
      files (list): A list of file paths to be backed up.
      backup_dir (str, optional): The parent directory for backups (default "backups").

    Returns:
      str: The path to the created backup directory.

    Raises:
      SystemExit: If the backup process fails.

    Implementation Details:
      - Generates a unique timestamp.
      - Creates the backup directory if it does not exist.
      - Copies each file to the backup directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, timestamp)
    try:
        os.makedirs(backup_path, exist_ok=True)
        for file in files:
            shutil.copy(file, backup_path)
    except Exception as e:
        console.print(f"Error backing up files: {e}", style="red")
        log_activity(f"Error backing up files: {e}")
        sys.exit(1)
    return backup_path

def log_activity(activity):
    """
    Logs a message with a timestamp to 'activity.log'.

    Parameters:
      activity (str): A description of the event or error to log.

    Returns:
      None

    Implementation Details:
      - Opens 'activity.log' in append mode to preserve historical logs.
    """
    try:
        with open('activity.log', 'a') as log:
            log.write(f"{datetime.now()} - {activity}\n")
    except Exception as e:
        console.print(f"Error logging activity: {e}", style="red")

def load_config(config_path="config.json"):
    """
    Loads configuration settings from a JSON file.

    Parameters:
      config_path (str, optional): The path to the configuration file (default "config.json").

    Returns:
      dict: The configuration data, or an empty dictionary if the file is not found or cannot be parsed.

    Implementation Details:
      - Uses a try/except block to handle JSON decoding and file I/O errors.
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            console.print(f"Error loading configuration: {e}", style="red")
            log_activity(f"Error loading configuration: {e}")
            return {}
    return {}

def save_config(config, config_path="config.json"):
    """
    Saves configuration data to a JSON file with human-readable indentation.

    Parameters:
      config (dict): The configuration data to be saved.
      config_path (str, optional): The destination path for the config file (default "config.json").

    Returns:
      None

    Implementation Details:
      - Uses a try/except block to capture any errors during file writing.
    """
    try:
        with open(config_path, 'w') as file:
            json.dump(config, file, indent=4)
    except Exception as e:
        console.print(f"Error saving configuration: {e}", style="red")
        log_activity(f"Error saving configuration: {e}")

# =============================================================================
# Core Processing Function
# =============================================================================
def process_code(file_contents, file_names, model):
    """
    Processes concatenated Rust source files by sending them to the OpenAI API.

    Description:
      Constructs a detailed prompt instructing the AI to:
        1. Debug and remove errors.
        2. Restructure code for efficiency.
        3. Add extensive, technical code comments.
        4. Ensure cross-file compatibility (methods, functions, traits, etc.).
      The AI is also instructed to ensure that the code compiles using 'cargo build'.

    Parameters:
      file_contents (str): Concatenated contents of input files with headers.
      file_names (str): Comma-separated list of relative file paths.
      model (str): The OpenAI model to use (e.g., "gpt-4o").

    Returns:
      str: Processed Rust code, with file headers intact, as returned by the API.

    Implementation Details:
      - Implements retry logic with exponential backoff (and random jitter) for resilience.
      - Catches both connection errors and general OpenAI errors.
    """
    prompt = f"""
    You are an expert Rust developer. Given the following Rust source files, perform:

    1. Debugging and error detection/removal.
    2. Code restructuring for compactness and efficiency.
    3. Adding full, technically detailed code comments.
    4. Ensuring cross-file compatibility of methods, functions, traits, etc.

    Ensure the code compiles successfully using `cargo build`.

    Files provided:
    {file_names}

    ### Begin Rust Source Files ###
    {file_contents}
    ### End Rust Source Files ###

    Return each file clearly separated with headers:
    ## File: relative/path/to/file ##
    <processed code here>
    """

    max_retries = 3
    base_retry_delay = 5  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            # Send the prompt to the OpenAI API using the chat completions endpoint.
            # The low temperature (0.1) ensures deterministic output.
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an assistant specializing in Rust programming."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=60  # Timeout set to 60 seconds to avoid hanging requests.
            )
            # Extract and return the processed content from the API response.
            return response.choices[0].message.content

        except APIConnectionError as e:
            # Handle connection errors with retry logic.
            if attempt < max_retries:
                wait_time = base_retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                console.print(
                    f"Error connecting to OpenAI API (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {wait_time:.2f} seconds...", style="red"
                )
                time.sleep(wait_time)
            else:
                console.print(
                    f"Error connecting to OpenAI API on attempt {attempt}. No more retries left. Exiting.",
                    style="red"
                )
                sys.exit(1)
        except OpenAIError as e:
            # Handle other errors returned by the OpenAI API.
            console.print(f"OpenAI API returned an error: {e}", style="red")
            log_activity(f"OpenAI API error: {e}")
            sys.exit(1)

# =============================================================================
# Interactive File Selection Functions
# =============================================================================
def select_files():
    """
    Launches an interactive CLI for directory navigation and file selection.

    Behavior:
      - Displays current directory and lists selected files.
      - Allows navigation via 'Enter' (to open a directory or select a file),
        'Backspace' (to move up a directory), and 'd' (to finish selection).
      - Only files with the '.rs' extension or named 'Cargo.toml' are selectable.

    Returns:
      list: A list of absolute file paths selected by the user.

    Implementation Details:
      Utilizes prompt_toolkit for rich CLI features like autocompletion and custom key bindings.
    """
    session = PromptSession()
    completer = PathCompleter(expanduser=True)
    selected_files = []
    bindings = KeyBindings()

    def refresh():
        """Refreshes the CLI display with updated directory, file selection, and command help."""
        clear_screen()
        console.print(f"[bold cyan]Current Directory:[/bold cyan] {os.getcwd()}\n")
        console.print("[bold green]Selected Files:[/bold green]")
        for file in selected_files:
            console.print(f" - {file}")
        console.print(
            "\n[bold yellow]Commands:[/bold yellow]\n"
            "- Enter: Open directory or select file\n"
            "- Backspace: Go up directory\n"
            "- d: Finish selection\n"
            "- esc/q: Exit\n"
            "- ?: Help\n"
            "- Tab: Autocomplete file or directory names"
        )

    @bindings.add('enter')
    def _(event):
        """
        Handles the 'Enter' key event.
        - If input is a directory, navigates into it.
        - If input is a valid file (.rs or Cargo.toml), adds its absolute path to the selection.
        """
        buffer = event.app.current_buffer
        path = buffer.text.strip()
        if os.path.isdir(path):
            os.chdir(path)
        elif os.path.isfile(path) and (path.endswith('.rs') or os.path.basename(path) == 'Cargo.toml'):
            selected_files.append(os.path.abspath(path))
        buffer.reset()
        refresh()

    @bindings.add('backspace')
    def _(event):
        """
        Handles the 'Backspace' key event.
        Navigates up one directory level.
        """
        os.chdir('..')
        event.app.current_buffer.reset()
        refresh()

    @bindings.add('escape', eager=True)
    @bindings.add('q', eager=True)
    def _(event):
        """
        Handles the 'Escape' and 'q' key events.
        Immediately exits the program.
        """
        console.print("\nExiting program.", style="red")
        sys.exit(0)

    @bindings.add('d')
    def _(event):
        """
        Handles the 'd' key event.
        Signals completion of file selection.
        """
        event.app.exit(result="done")

    @bindings.add('?')
    def _(event):
        """
        Handles the '?' key event.
        Displays detailed help instructions for file navigation and selection.
        """
        console.print(
            "\n[bold magenta]Help:[/bold magenta]\n"
            "Navigate directories with Enter, go up with Backspace.\n"
            "Finish selection with 'd'.\n"
            "Exit with 'esc' or 'q'.\n"
            "Use 'Tab' key to autocomplete file or directory names as you type."
        )

    refresh()
    while True:
        path = session.prompt('> ', completer=completer, key_bindings=bindings)
        if path == "done":
            break

    return selected_files

def select_model():
    """
    Prompts the user to select an OpenAI model from a predefined list.

    Returns:
      str: The name of the selected model (e.g., "gpt-4o").

    Implementation Details:
      - Displays a numbered list of models.
      - Validates user input and re-prompts on invalid entries.
    """
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
    console.print("[bold magenta]Select OpenAI model:[/bold magenta]")
    for idx, model in enumerate(models, 1):
        console.print(f"{idx}. {model}")
    while True:
        try:
            choice = int(input("Enter choice: "))
            return models[choice - 1]
        except (ValueError, IndexError):
            console.print("Invalid selection.", style="red")

# =============================================================================
# Summary Report Generation
# =============================================================================
def generate_summary_report(files, model, compilation_result):
    """
    Generates a detailed summary report of the optimization process and writes it to a file.

    The report includes:
      - The OpenAI model used.
      - The date and time of processing.
      - A list of all processed files.
      - The result of the compilation (success or failure).

    Parameters:
      files (list): List of file paths that were processed.
      model (str): The OpenAI model used for processing.
      compilation_result (int): The return code from 'cargo build' (0 indicates success).

    Returns:
      None

    Implementation Details:
      - The report is written to "OpenAI/summary_report.txt".
      - Uses exception handling to log and report any file I/O errors.
    """
    report_path = os.path.join("OpenAI", "summary_report.txt")
    try:
        with open(report_path, 'w') as report:
            report.write("Rust Optimization Summary Report\n")
            report.write(f"Model used: {model}\n")
            report.write(f"Date: {datetime.now()}\n\n")
            report.write("Processed Files:\n")
            for file in files:
                report.write(f" - {file}\n")
            report.write(f"\nCompilation Status: {'Success' if compilation_result == 0 else 'Failure'}\n")
    except Exception as e:
        console.print(f"Error generating summary report: {e}", style="red")
        log_activity(f"Error generating summary report: {e}")

# =============================================================================
# Cargo Availability Check
# =============================================================================
def check_cargo():
    """
    Verifies that the 'cargo' command is available in the system's PATH.

    Returns:
      None

    Raises:
      SystemExit: If the 'cargo' command is not found.

    Implementation Details:
      Utilizes shutil.which() to check for the command.
    """
    if shutil.which("cargo") is None:
        console.print("Error: 'cargo' command not found in PATH. Please install Rust and Cargo.", style="red")
        sys.exit(1)

# =============================================================================
# Main Execution Function
# =============================================================================
def main():
    """
    Main function encapsulating the entire program logic.

    Responsibilities:
      - Set up signal handling for graceful termination.
      - Verify that 'cargo' is installed.
      - Load and update configuration settings.
      - Allow interactive file selection and model selection.
      - Create backups and process code via OpenAI.
      - Recreate the project directory structure in the output.
      - Optionally run 'cargo build' on the chosen project version.
      - Generate a summary report and save updated configuration.

    Returns:
      None

    Implementation Details:
      - Uses try/except blocks to catch unexpected errors.
      - Uses relative paths to preserve project structure.
    """
    # Set up SIGINT (Ctrl+C) handling for graceful termination.
    signal.signal(signal.SIGINT, lambda s, f: sys.exit("\nInterrupted by user."))

    # Verify that the 'cargo' tool is available.
    check_cargo()

    # Save the original working directory (assumed to be the project root where Cargo.toml resides).
    original_cwd = os.getcwd()

    clear_screen()
    console.print("[bold blue]Interactive Rust Optimizer (OpenAI)[/bold blue]\n")

    # Load configuration from file (if exists) or initialize an empty config.
    config = load_config()

    # Handle OpenAI model selection. If a model is preconfigured, prompt the user to keep or change it.
    if 'model' in config:
        model = config['model']
        console.print(f"Using previously configured model: [bold green]{model}[/bold green]")
        change_model = input("Change model? (y/n): ").strip().lower()
        if change_model == 'y':
            model = select_model()
            config['model'] = model
    else:
        model = select_model()
        config['model'] = model

    # Launch interactive file selection.
    files = select_files()
    if not files:
        console.print("No files selected. Exiting.", style="red")
        sys.exit(0)

    # Ask the user if selected files should be saved to configuration for future runs.
    save_files_choice = input("Save selected files to configuration? (y/n): ").strip().lower()
    if save_files_choice == 'y':
        config['selected_files'] = files

    # Create a backup of the selected files before any processing.
    backup_dir = backup_files(files)
    log_activity(f"Backed up files to {backup_dir}")

    # Prepare file contents and names for OpenAI processing.
    # Compute each file's relative path with respect to the original working directory.
    file_contents = ""
    file_names = ""
    for file_path in tqdm(files, desc="Reading Files"):
        content = read_file(file_path)
        rel_path = os.path.relpath(file_path, original_cwd)
        file_contents += f"\n\n## File: {rel_path} ##\n{content}"
        file_names += f"{rel_path}, "

    # Send the concatenated code to the OpenAI API for processing.
    processed_output = process_code(file_contents, file_names.strip(", "), model)
    
    # Split the processed output into sections based on file headers.
    outputs = processed_output.split("## File: ")[1:]

    # Write the processed (optimized) files to the "OpenAI" output directory,
    # preserving the original directory structure.
    output_dir = "OpenAI"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        console.print(f"Error creating output directory '{output_dir}': {e}", style="red")
        sys.exit(1)

    for output in tqdm(outputs, desc="Writing Files"):
        header_end = output.find(" ##")
        rel_path = output[:header_end].strip()
        code = output[header_end + 3:].strip()
        dest_file = os.path.join(output_dir, rel_path)
        try:
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            write_file(dest_file, code)
        except Exception as e:
            console.print(f"Error writing optimized file '{dest_file}': {e}", style="red")
            log_activity(f"Error writing optimized file '{dest_file}': {e}")

    # Prompt the user to optionally run 'cargo build' to verify compilation.
    console.print("\n[bold magenta]Would you like to run 'cargo build' to check compilation?[/bold magenta]")
    compile_choice = input("Compile now? (y/n): ").strip().lower()

    if compile_choice == 'y':
        console.print("\n[bold magenta]Compile using:[/bold magenta]")
        console.print("1. Original source files")
        console.print("2. Optimized OpenAI files")
        source_choice = input("Enter choice (1 or 2): ").strip()

        # Determine the appropriate directory for compilation.
        if source_choice == "1":
            cargo_toml_path = next((f for f in files if os.path.basename(f) == "Cargo.toml"), None)
            if cargo_toml_path:
                compile_dir = os.path.dirname(cargo_toml_path)
            else:
                compile_dir = original_cwd
        else:
            compile_dir = os.path.join(original_cwd, "OpenAI")

        try:
            result = subprocess.run(["cargo", "build"], cwd=compile_dir, capture_output=True, text=True)
        except Exception as e:
            console.print(f"Error during 'cargo build': {e}", style="red")
            log_activity(f"Error during 'cargo build': {e}")
            sys.exit(1)

        log_activity(f"Compilation {'success' if result.returncode == 0 else 'failure'} "
                     f"({'original' if source_choice == '1' else 'optimized'})")

        if result.returncode == 0:
            console.print("Compilation successful!", style="green")
        else:
            console.print("Compilation failed:", style="red")
            console.print(result.stderr)
    else:
        result = type('obj', (object,), {'returncode': 1})()
        console.print("Skipping compilation step.", style="yellow")

    # Generate and save a summary report of the optimization and compilation process.
    generate_summary_report(files, model, result.returncode)
    save_config(config)
    console.print("Files / Summary Report Saved in 'OpenAI' -- Configuration Saved")

# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"Unexpected error: {e}", style="red")
        log_activity(f"Unexpected error: {e}")
        sys.exit(1)
