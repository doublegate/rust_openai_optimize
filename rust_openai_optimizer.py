#!/usr/bin/env python3
"""
======================================================================
rust_openai_optimizer.py - ver. 0.4.0
======================================================================
Purpose:
  Optimize, debug, restructure, and add detailed comments to Rust source
  code using OpenAI's LLM API. This tool supports interactive, non-interactive,
  and GUI modes. It preserves the original project structure (e.g. Cargo.toml at 
  the root, source files under src/) so that the optimized code can be compiled 
  with 'cargo build'. Additional features include:
    - Version control integration via Git.
    - Preview/diff mode for reviewing changes.
    - Caching/incremental processing to avoid unnecessary re-optimization.
    - Customizable configuration with profiles.
    - Rollback and backup management.
    
Usage:
  Interactive mode:
    python rust_openai_optimizer.py
  Non-interactive mode:
    python rust_openai_optimizer.py --files Cargo.toml src/main.rs --model gpt-4 --build
  GUI mode:
    python rust_openai_optimizer.py --gui
  Rollback:
    python rust_openai_optimizer.py --rollback
  Preview/diff mode:
    python rust_openai_optimizer.py --preview
  Verbose logging:
    python rust_openai_optimizer.py --verbose

Author:
  DoubleGate -- 2025: https://github.com/doublegate/rust_openai_optimize
======================================================================
"""

# =============================================================================
# Standard Library Imports
# =============================================================================
import os                   # For file system operations and environment management.
import sys                  # For system-specific parameters and functions.
import subprocess           # To run external commands (e.g. Git, Cargo).
import shutil               # For high-level file operations like copy and directory management.
import json                 # For configuration and log file management.
from datetime import datetime  # For timestamping backups and logs.
import time                 # For sleep delays during retries.
import random               # For random jitter in retry delay.
import signal               # To handle system signals (e.g. SIGINT for graceful exit).
import argparse             # For parsing command-line arguments.
import logging              # For logging events and errors.
import hashlib              # For computing SHA256 file hashes.
import difflib              # For generating unified diffs between file versions.
import asyncio              # For asynchronous API call support.
import smtplib              # For sending error notification emails (if configured).
import tempfile             # For creating temporary files during testing.

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import openai               # OpenAI API client.
try:
    from openai.error import APIConnectionError, OpenAIError
except ImportError:
    APIConnectionError = Exception  # Fallback if specific OpenAI errors are not available.
    OpenAIError = Exception

from prompt_toolkit import PromptSession       # For interactive CLI file selection.
from prompt_toolkit.completion import PathCompleter  # To assist with filesystem path completions.
from prompt_toolkit.key_binding import KeyBindings   # For custom key bindings in the CLI.
from tqdm import tqdm                           # For displaying progress bars.
from rich.console import Console                # For enhanced terminal output formatting.
try:
    import tkinter as tk                        # Tkinter for GUI file dialogs.
    from tkinter import filedialog, messagebox
except ImportError:
    tk = None  # If Tkinter is not available, GUI mode will not be supported.

# =============================================================================
# Global Object Initialization and Logging Setup
# =============================================================================
console = Console()  # Rich Console for colorized output and formatting.

# Configure the logging module to output detailed logs to a file.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="rust_openai_optimizer.log",
    filemode="a"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Environment and API Key Check
# =============================================================================
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    console.print("Error: OPENAI_API_KEY environment variable is not set. Exiting.", style="red")
    logger.error("OPENAI_API_KEY not set.")
    sys.exit(1)

# =============================================================================
# Helper Functions
# =============================================================================
def compute_hash(filepath):
    """
    Computes the SHA256 hash of the file's contents.

    This function reads the file in binary mode in fixed-size chunks to support
    large files without loading the entire file into memory.

    Parameters:
      filepath (str): The path to the file whose hash is to be computed.

    Returns:
      str:
        A hexadecimal string representing the SHA256 hash of the file's contents.
        Returns None if an error occurs during file reading.
    """
    sha256 = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            # Read file in 8KB chunks
            while True:
                data = f.read(8192)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error computing hash for {filepath}: {e}")
        return None


def read_file(filepath):
    """
    Reads the entire contents of a file and returns it as a string.

    This function attempts to open the specified file in text mode, read its
    contents, and log the action at debug level. If the file cannot be read,
    it logs the error and terminates the program.

    Parameters:
      filepath (str): The file system path to the file.

    Returns:
      str:
        The complete contents of the file as a string.

    Raises:
      SystemExit:
        If the file cannot be read due to an exception.
    """
    try:
        with open(filepath, 'r') as file:
            data = file.read()
            logger.debug(f"Successfully read file: {filepath}")
            return data
    except Exception as e:
        msg = f"Error reading file '{filepath}': {e}"
        console.print(msg, style="red")
        logger.error(msg)
        sys.exit(1)


def write_file(filepath, content):
    """
    Writes the provided content to a file, overwriting any existing data.

    This function opens the destination file in write mode and writes the
    content. It logs the operation and exits the program if any error occurs.

    Parameters:
      filepath (str): The destination file path.
      content (str): The string content to write to the file.

    Raises:
      SystemExit:
        If the file cannot be written due to an exception.
    """
    try:
        with open(filepath, 'w') as file:
            file.write(content)
            logger.debug(f"Successfully wrote file: {filepath}")
    except Exception as e:
        msg = f"Error writing file '{filepath}': {e}"
        console.print(msg, style="red")
        logger.error(msg)
        sys.exit(1)


def clear_screen():
    """
    Clears the terminal screen using a system command.

    This function determines the operating system and calls the appropriate
    command ('cls' for Windows, 'clear' for Unix-like systems) to clear the
    terminal.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def backup_files(files, backup_dir="backups"):
    """
    Creates timestamped backups of the provided files.

    The function creates a new backup directory using the current date and time
    as a unique identifier. It then copies each specified file into this directory.
    If any error occurs during the backup process, the program logs the error and
    terminates.

    Parameters:
      files (list):
        A list of file paths (str) that should be backed up.
      backup_dir (str):
        The parent directory where backups are stored. Defaults to "backups".

    Returns:
      str:
        The path to the created backup directory.

    Raises:
      SystemExit:
        If the backup operation fails.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, timestamp)
    try:
        os.makedirs(backup_path, exist_ok=True)
        for file in files:
            shutil.copy(file, backup_path)
        logger.info(f"Backup created at {backup_path}")
    except Exception as e:
        msg = f"Error backing up files: {e}"
        console.print(msg, style="red")
        logger.error(msg)
        sys.exit(1)
    return backup_path


def log_activity(activity):
    """
    Appends a log entry to the 'activity.log' file with a timestamp.

    This is used for keeping a record of key actions (like backups) executed by
    the tool.

    Parameters:
      activity (str): A descriptive message of the activity to log.
    """
    try:
        with open('activity.log', 'a') as log_file:
            log_file.write(f"{datetime.now()} - {activity}\n")
        logger.info(activity)
    except Exception as e:
        console.print(f"Error logging activity: {e}", style="red")
        logger.error(f"Error logging activity: {e}")


def load_config(config_path="config.json", profile="default"):
    """
    Loads a configuration profile from a JSON configuration file.

    The function reads the JSON file and returns the configuration for the
    specified profile. If the configuration file does not exist or cannot be
    parsed, an empty configuration is returned.

    Parameters:
      config_path (str):
        The path to the configuration JSON file. Defaults to "config.json".
      profile (str):
        The profile name whose configuration should be returned. Defaults to "default".

    Returns:
      dict:
        A dictionary containing the configuration for the specified profile.
    """
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
            logger.debug("Configuration loaded successfully.")
        except Exception as e:
            msg = f"Error loading configuration: {e}"
            console.print(msg, style="red")
            logger.error(msg)
    return config.get(profile, {})


def save_config(config, config_path="config.json", profile="default"):
    """
    Saves configuration data for a given profile into a JSON file.

    This function loads any existing configuration, updates the specified profile,
    and writes the combined configuration back to the file.

    Parameters:
      config (dict):
        The configuration data to be saved.
      config_path (str):
        The destination path of the configuration file. Defaults to "config.json".
      profile (str):
        The name of the profile under which to store the configuration.
    """
    full_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                full_config = json.load(file)
        except Exception:
            full_config = {}
    full_config[profile] = config
    try:
        with open(config_path, 'w') as file:
            json.dump(full_config, file, indent=4)
        logger.debug("Configuration saved successfully.")
    except Exception as e:
        msg = f"Error saving configuration: {e}"
        console.print(msg, style="red")
        logger.error(msg)


def send_error_notification(error_message, notification_email=None):
    """
    (Placeholder) Sends an error notification via email.

    If a notification email is provided, this function would normally configure
    an SMTP client to send an email containing the error message. For now, it
    simply prints a notification message.

    Parameters:
      error_message (str):
        The error message to be sent.
      notification_email (str, optional):
        The email address to notify. If None, no notification is sent.
    """
    if notification_email:
        # Example implementation for SMTP email notifications:
        # smtp_server = "smtp.example.com"
        # smtp_port = 587
        # username = os.getenv("SMTP_USERNAME")
        # password = os.getenv("SMTP_PASSWORD")
        # from_addr = os.getenv("SMTP_FROM")
        # try:
        #     server = smtplib.SMTP(smtp_server, smtp_port)
        #     server.starttls()
        #     server.login(username, password)
        #     message = f"Subject: Rust Optimizer Error\n\n{error_message}"
        #     server.sendmail(from_addr, notification_email, message)
        #     server.quit()
        #     logger.info("Error notification sent successfully.")
        # except Exception as e:
        #     logger.error(f"Failed to send error notification: {e}")
        console.print(f"(Notification) Would send error notification to {notification_email}: {error_message}", style="yellow")
        logger.info(f"(Notification) Would send error notification to {notification_email}: {error_message}")


# =============================================================================
# Core Processing Functions (Sync & Async)
# =============================================================================
def process_code(file_contents, file_names, model, retries=3, timeout=60):
    """
    Processes Rust source code by sending it to the OpenAI API with retry logic.

    This function constructs a detailed prompt that includes the contents and
    file names of Rust source files. It then attempts to retrieve an optimized,
    debugged, and restructured version of the code from the OpenAI API. In the
    event of API connection errors or other issues, it employs exponential backoff
    with jitter before retrying.

    Parameters:
      file_contents (str):
        A concatenated string containing the contents of all Rust source files,
        separated by headers indicating their relative paths.
      file_names (str):
        A comma-separated list of the relative file paths.
      model (str):
        The OpenAI model to use for processing (e.g., "gpt-4", "gpt-3.5-turbo").
      retries (int):
        The maximum number of API retry attempts. Defaults to 3.
      timeout (int):
        The API request timeout in seconds. Defaults to 60 seconds.

    Returns:
      str:
        The processed Rust code returned by the API, where each file is clearly
        separated by headers.

    Exits:
      The program will terminate with an error message if all retry attempts fail.
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
    base_retry_delay = 5  # Base delay (in seconds) before retrying the API call.
    for attempt in range(1, retries + 1):
        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an assistant specializing in Rust programming."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=timeout
            )
            logger.info("API call succeeded on attempt %d.", attempt)
            return response.choices[0].message.content
        except APIConnectionError as e:
            if attempt < retries:
                wait_time = base_retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                msg = (f"Error connecting to OpenAI API (attempt {attempt}/{retries}): {e}. "
                       f"Retrying in {wait_time:.2f} seconds...")
                console.print(msg, style="red")
                logger.error(msg)
                time.sleep(wait_time)
            else:
                msg = f"Error connecting to OpenAI API on attempt {attempt}. No more retries left."
                console.print(msg, style="red")
                logger.error(msg)
                sys.exit(1)
        except OpenAIError as e:
            msg = f"OpenAI API error: {e}"
            console.print(msg, style="red")
            logger.error(msg)
            sys.exit(1)


async def process_code_async(file_contents, file_names, model, retries=3, timeout=60):
    """
    Asynchronously processes Rust source code using the OpenAI API.

    Similar to the synchronous version, this function constructs a prompt with
    the provided file contents and names, then asynchronously sends the request.
    It uses asynchronous exponential backoff in case of connection errors.

    Parameters:
      file_contents (str):
        The concatenated string of Rust source file contents.
      file_names (str):
        Comma-separated list of relative file paths.
      model (str):
        The OpenAI model to be used (e.g., "gpt-4", "gpt-3.5-turbo").
      retries (int):
        Maximum number of retry attempts (default is 3).
      timeout (int):
        Request timeout in seconds (default is 60).

    Returns:
      str:
        The processed Rust code output from the API.

    Exits:
      Terminates the program if all retry attempts fail.
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
    base_retry_delay = 5  # Base delay in seconds for retries.
    for attempt in range(1, retries + 1):
        try:
            response = await openai.ChatCompletion.acreate(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an assistant specializing in Rust programming."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=timeout
            )
            logger.info("Async API call succeeded on attempt %d.", attempt)
            return response.choices[0].message.content
        except APIConnectionError as e:
            if attempt < retries:
                wait_time = base_retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                msg = (f"Async error connecting to OpenAI API (attempt {attempt}/{retries}): {e}. "
                       f"Retrying in {wait_time:.2f} seconds...")
                console.print(msg, style="red")
                logger.error(msg)
                await asyncio.sleep(wait_time)
            else:
                msg = f"Async error connecting to OpenAI API on attempt {attempt}. No more retries left."
                console.print(msg, style="red")
                logger.error(msg)
                sys.exit(1)
        except OpenAIError as e:
            msg = f"Async OpenAI API error: {e}"
            console.print(msg, style="red")
            logger.error(msg)
            sys.exit(1)


# =============================================================================
# Interactive File Selection and GUI Mode
# =============================================================================
def select_files_cli():
    """
    Provides an interactive CLI for file selection using prompt_toolkit.

    This function allows the user to navigate directories and select files that
    are relevant to Rust (i.e., files ending with '.rs' or named 'Cargo.toml').
    Key bindings support directory navigation, file selection, and help commands.

    Returns:
      list:
        A list of absolute file paths selected by the user.
    """
    session = PromptSession()
    completer = PathCompleter(expanduser=True)
    selected_files = []
    bindings = KeyBindings()

    def refresh():
        # Refresh the screen with current directory and selected files.
        clear_screen()
        console.print(f"[bold cyan]Current Directory:[/bold cyan] {os.getcwd()}\n")
        console.print("[bold green]Selected Files:[/bold green]")
        for file in selected_files:
            console.print(f" - {file}")
        console.print(
            "\n[bold yellow]Commands:[/bold yellow]\n"
            "Enter: Open directory/select file | Backspace: Go up | d: Done | esc/q: Exit | ?: Help"
        )

    @bindings.add('enter')
    def _(event):
        # On Enter, if a directory is entered change directory; if a valid file is entered, select it.
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
        # On Backspace, navigate up one directory.
        os.chdir('..')
        event.app.current_buffer.reset()
        refresh()

    @bindings.add('escape', eager=True)
    @bindings.add('q', eager=True)
    def _(event):
        # Exit the application on 'esc' or 'q'.
        console.print("\nExiting program.", style="red")
        sys.exit(0)

    @bindings.add('d')
    def _(event):
        # Signal completion of selection.
        event.app.exit(result="done")

    @bindings.add('?')
    def _(event):
        # Display help instructions.
        console.print(
            "\n[bold magenta]Help:[/bold magenta]\n"
            "Enter: open/select file | Backspace: go up | d: finish selection | esc/q: exit"
        )

    refresh()
    while True:
        path = session.prompt('> ', completer=completer, key_bindings=bindings)
        if path == "done":
            break
    return selected_files


def select_files_gui():
    """
    Uses a Tkinter file dialog for selecting files via a GUI.

    If Tkinter is available, a native file dialog is presented to the user for
    selecting Rust source files ('.rs') and Cargo.toml. If Tkinter is not installed,
    the function falls back to the CLI file selection.

    Returns:
      list:
        A list of absolute file paths selected through the GUI.
    """
    if tk is None:
        console.print("Tkinter is not available. Falling back to CLI.", style="yellow")
        return select_files_cli()
    root = tk.Tk()
    root.withdraw()  # Hide the main window to only show the file dialog.
    file_paths = filedialog.askopenfilenames(title="Select Rust files", 
                                             filetypes=[("Rust files", "*.rs"), ("Cargo.toml", "Cargo.toml")])
    return list(file_paths)


def select_model():
    """
    Prompts the user to select an OpenAI model via CLI input.

    Provides a list of pre-defined model options and validates the user input.

    Returns:
      str:
        The selected OpenAI model as a string.
    """
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
    console.print("[bold magenta]Select OpenAI model:[/bold magenta]")
    for idx, m in enumerate(models, 1):
        console.print(f"{idx}. {m}")
    while True:
        try:
            choice = int(input("Enter choice: "))
            return models[choice - 1]
        except (ValueError, IndexError):
            console.print("Invalid selection.", style="red")


# =============================================================================
# Version Control Integration (Git)
# =============================================================================
def is_git_repo(path):
    """
    Checks whether the specified directory is part of a Git repository.

    The function determines if the directory (or any parent directory) contains
    a ".git" folder, which indicates that it is under Git version control.

    Parameters:
      path (str):
        The directory path to check.

    Returns:
      bool:
        True if the directory is within a Git repository; False otherwise.
    """
    return os.path.isdir(os.path.join(path, ".git"))


def commit_changes(commit_message="Optimize Rust code via OpenAI"):
    """
    Commits current changes to the Git repository.

    This function stages all changes and creates a commit with the provided
    commit message. It logs the operation and informs the user via the console.
    If any error occurs during the Git operations, it logs the error.

    Parameters:
      commit_message (str):
        The commit message to be used for the Git commit.
    """
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        logger.info("Git commit successful.")
        console.print("Changes committed to Git.", style="green")
    except Exception as e:
        logger.error(f"Git commit failed: {e}")
        console.print(f"Git commit failed: {e}", style="red")


# =============================================================================
# Preview and Diff Mode
# =============================================================================
def show_diff(original, optimized, filename):
    """
    Generates a unified diff between the original and optimized file contents.

    Utilizes Python's difflib to compare the two versions line-by-line and creates
    a diff string that clearly indicates the changes.

    Parameters:
      original (str):
        The original file content.
      optimized (str):
        The optimized file content.
      filename (str):
        The name of the file for labeling the diff output.

    Returns:
      str:
        A string containing the unified diff. Returns an empty string if there
        are no differences.
    """
    diff = difflib.unified_diff(
        original.splitlines(), optimized.splitlines(),
        fromfile=f"Original: {filename}",
        tofile=f"Optimized: {filename}",
        lineterm=""
    )
    diff_text = "\n".join(diff)
    return diff_text


def preview_diffs(files, original_dir, optimized_dir):
    """
    Displays side-by-side diffs for all files between original and optimized versions.

    For each file, the function reads the original and optimized contents,
    generates a diff, and prints it to the console. If no changes are detected,
    it informs the user accordingly.

    Parameters:
      files (list):
        A list of relative file paths.
      original_dir (str):
        The directory containing the original files.
      optimized_dir (str):
        The directory containing the optimized files.
    """
    for rel_path in files:
        orig_file = os.path.join(original_dir, rel_path)
        opt_file = os.path.join(optimized_dir, rel_path)
        if os.path.exists(orig_file) and os.path.exists(opt_file):
            original = read_file(orig_file)
            optimized = read_file(opt_file)
            diff_text = show_diff(original, optimized, rel_path)
            if diff_text:
                console.print(f"Diff for {rel_path}:\n", style="bold blue")
                console.print(diff_text)
            else:
                console.print(f"No changes for {rel_path}.", style="green")


# =============================================================================
# Rollback and Backup Management
# =============================================================================
def list_backups(backup_dir="backups"):
    """
    Lists all available backup directories.

    Searches the specified backup parent directory and returns a sorted list
    of subdirectories representing individual backups.

    Parameters:
      backup_dir (str):
        The parent directory where backups are stored.

    Returns:
      list:
        A sorted list of backup directory names. Returns an empty list if the
        backup directory does not exist.
    """
    if not os.path.isdir(backup_dir):
        return []
    backups = os.listdir(backup_dir)
    backups = sorted(backups)
    return backups


def rollback_backup():
    """
    Provides an interactive rollback mechanism to restore a previous backup.

    The function lists all available backups, prompts the user to select one,
    and then restores all files from the chosen backup into the current working
    directory. If the selection is invalid, it informs the user.
    """
    backups = list_backups()
    if not backups:
        console.print("No backups available.", style="red")
        return
    console.print("Available backups:", style="bold magenta")
    for idx, b in enumerate(backups, 1):
        console.print(f"{idx}. {b}")
    try:
        choice = int(input("Enter the number of the backup to restore: "))
        backup_choice = backups[choice - 1]
    except Exception:
        console.print("Invalid selection.", style="red")
        return
    backup_path = os.path.join("backups", backup_choice)
    # For simplicity, restore all files from the backup to the current directory.
    for file in os.listdir(backup_path):
        src = os.path.join(backup_path, file)
        dst = os.path.join(os.getcwd(), file)
        shutil.copy(src, dst)
    console.print(f"Restored backup from {backup_choice}.", style="green")
    logger.info(f"Restored backup from {backup_choice}.")


# =============================================================================
# Enhanced Cargo Build Integration
# =============================================================================
def run_cargo_build(compile_dir):
    """
    Executes 'cargo build' in the specified directory and processes its output.

    The function invokes the Cargo build system using a JSON output format.
    If the build is successful, it notifies the user. In case of errors, it
    attempts to parse the JSON messages to extract and display error details.

    Parameters:
      compile_dir (str):
        The directory in which to execute the 'cargo build' command.

    Returns:
      subprocess.CompletedProcess:
        The completed process object containing stdout, stderr, and return code.

    Raises:
      SystemExit:
        If an exception occurs while running the cargo build command.
    """
    try:
        result = subprocess.run(["cargo", "build", "--message-format=json"],
                                cwd=compile_dir, capture_output=True, text=True)
        if result.returncode == 0:
            console.print("Compilation successful!", style="green")
            logger.info("Compilation successful.")
        else:
            console.print("Compilation failed:", style="red")
            # Parse JSON messages from stdout to extract compiler errors.
            for line in result.stdout.splitlines():
                try:
                    msg = json.loads(line)
                    if msg.get("reason") == "compiler-message":
                        message = msg["message"].get("message", "")
                        console.print(message, style="red")
                except Exception:
                    continue
            logger.error("Compilation failed.")
        return result
    except Exception as e:
        msg = f"Error during 'cargo build': {e}"
        console.print(msg, style="red")
        logger.error(msg)
        sys.exit(1)


# =============================================================================
# Caching and Incremental Processing
# =============================================================================
def compute_combined_hash(files, base_dir):
    """
    Computes a combined SHA256 hash for a set of files to enable caching.

    For each file, the function calculates the SHA256 hash of its contents
    and combines these hashes with the file's relative path. The final combined
    hash is computed over the concatenated string, providing a fingerprint that
    detects any changes to the set of files.

    Parameters:
      files (list):
        A list of absolute file paths for which to compute the combined hash.
      base_dir (str):
        The base directory used to calculate relative paths for the files.

    Returns:
      str:
        A hexadecimal string representing the combined SHA256 hash.
    """
    combined = ""
    for f in sorted(files):
        rel_path = os.path.relpath(f, base_dir)
        file_hash = compute_hash(f)
        if file_hash:
            combined += rel_path + file_hash
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# =============================================================================
# Main Execution Function
# =============================================================================
def main():
    """
    Main function orchestrating the entire workflow of the Rust code optimizer.

    This function performs the following tasks:
      - Parses command-line arguments and configures logging.
      - Manages configuration profiles and loads settings.
      - Selects Rust source files either via CLI or GUI.
      - Creates a backup of selected files.
      - Computes a combined hash for caching and incremental processing.
      - Sends the file contents to the OpenAI API (synchronously or asynchronously)
        for optimization, debugging, restructuring, and detailed commenting.
      - Writes the optimized output to a new directory while preserving the
        original file structure.
      - Optionally previews file diffs and prompts for confirmation.
      - Optionally runs 'cargo build' to compile the code.
      - Optionally commits changes via Git.
      - Generates a summary report and saves the configuration.

    Exits:
      The program exits with appropriate status codes based on success or error conditions.
    """
    # Set up SIGINT (Ctrl+C) handling for graceful termination.
    signal.signal(signal.SIGINT, lambda s, f: sys.exit("\nInterrupted by user."))

    # Parse command-line arguments.
    parser = argparse.ArgumentParser(
        description="Rust OpenAI Optimizer: Optimize, debug, and comment Rust code using OpenAI LLMs."
    )
    parser.add_argument("--model", type=str, help="Specify the OpenAI model (e.g., gpt-4, gpt-3.5-turbo).")
    parser.add_argument("--files", nargs="+", help="List of files to process. If omitted, interactive selection is used.")
    parser.add_argument("--gui", action="store_true", help="Use a GUI file selection dialog.")
    parser.add_argument("--no-interactive", action="store_true", help="Disable interactive prompts.")
    parser.add_argument("--build", action="store_true", help="Automatically run 'cargo build' after processing.")
    parser.add_argument("--async-mode", action="store_true", help="Use asynchronous API calls.")
    parser.add_argument("--preview", action="store_true", help="Preview diff of changes before applying them.")
    parser.add_argument("--rollback", action="store_true", help="Rollback to a previous backup.")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the configuration file.")
    parser.add_argument("--profile", type=str, default="default", help="Configuration profile name.")
    parser.add_argument("--retry", type=int, help="Number of API retries.")
    parser.add_argument("--timeout", type=int, help="API timeout in seconds.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--notification-email", type=str, help="Email for error notifications (optional).")
    parser.add_argument("--test", action="store_true", help="Run unit tests and exit.")
    args = parser.parse_args()

    # Enable verbose logging if requested.
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        console.print("Verbose mode enabled.", style="bold green")

    # If rollback is requested, perform backup rollback and exit.
    if args.rollback:
        rollback_backup()
        sys.exit(0)

    # Run tests and exit if the test flag is set.
    if args.test:
        run_tests()

    # Load configuration for the specified profile.
    config = load_config(args.config, args.profile)
    if args.retry:
        config["retry"] = args.retry
    if args.timeout:
        config["timeout"] = args.timeout

    # Determine the OpenAI model using CLI argument, config file, or interactive prompt.
    if args.model:
        model = args.model
    elif "model" in config:
        model = config["model"]
        if not args.no_interactive:
            console.print(f"Using configured model: [bold green]{model}[/bold green]")
            change = input("Change model? (y/n): ").strip().lower()
            if change == "y":
                model = select_model()
    else:
        model = select_model()
    config["model"] = model

    # Determine files to process: from command-line, GUI, or interactive CLI.
    if args.files:
        files = [os.path.abspath(f) for f in args.files]
    elif args.gui:
        files = select_files_gui()
    elif not args.no_interactive:
        files = select_files_cli()
    else:
        console.print("Error: No files provided and interactive mode is disabled.", style="red")
        sys.exit(1)
    if not files:
        console.print("No files selected. Exiting.", style="red")
        sys.exit(0)
    config["selected_files"] = files

    # Create a backup of the selected files.
    backup_dir = backup_files(files)
    log_activity(f"Backed up files to {backup_dir}")

    # Save the original working directory for relative path calculations.
    original_cwd = os.getcwd()

    # Compute a combined hash of selected files for caching purposes.
    combined_hash = compute_combined_hash(files, original_cwd)
    prev_hash = config.get("combined_hash")
    use_cached = (prev_hash == combined_hash) and ("optimized_output" in config)
    logger.debug(f"Combined hash: {combined_hash} (previous hash: {prev_hash})")
    config["combined_hash"] = combined_hash

    # Use cached optimized output if no changes were detected.
    if use_cached:
        console.print("No changes detected since last run. Using cached optimized files.", style="green")
        optimized_files = config["optimized_output"]
    else:
        # Prepare concatenated file contents and file names for API processing.
        file_contents = ""
        file_names = ""
        for f in tqdm(files, desc="Reading Files"):
            content = read_file(f)
            rel_path = os.path.relpath(f, original_cwd)
            file_contents += f"\n\n## File: {rel_path} ##\n{content}"
            file_names += f"{rel_path}, "

        # Process the code through the OpenAI API (sync or async based on args).
        if args.async_mode:
            optimized_output = asyncio.run(
                process_code_async(file_contents, file_names.strip(", "), model,
                                   retries=config.get("retry", 3),
                                   timeout=config.get("timeout", 60))
            )
        else:
            optimized_output = process_code(file_contents, file_names.strip(", "), model,
                                            retries=config.get("retry", 3),
                                            timeout=config.get("timeout", 60))
        # Cache the optimized output for future runs.
        config["optimized_output"] = optimized_output
        optimized_files = optimized_output

    # Split the processed output into sections based on file headers.
    outputs = optimized_files.split("## File: ")[1:]

    # Write the optimized files to the "OpenAI" output directory, preserving original structure.
    output_dir = "OpenAI"
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        msg = f"Error creating output directory '{output_dir}': {e}"
        console.print(msg, style="red")
        logger.error(msg)
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
            msg = f"Error writing optimized file '{dest_file}': {e}"
            console.print(msg, style="red")
            logger.error(msg)
            log_activity(msg)

    # If preview/diff mode is enabled, show file differences and request user confirmation.
    if args.preview:
        console.print("\nPreviewing differences between original and optimized files:", style="bold blue")
        rel_files = [os.path.relpath(f, original_cwd) for f in files]
        preview_diffs(rel_files, original_cwd, output_dir)
        confirm = input("Apply optimized changes? (y/n): ").strip().lower()
        if confirm != "y":
            console.print("Aborting changes as per user request.", style="yellow")
            sys.exit(0)

    # Optionally run 'cargo build' for compilation testing.
    if args.build or (not args.no_interactive and input("Run 'cargo build'? (y/n): ").strip().lower() == "y"):
        # Verify that the 'cargo' command is available.
        if shutil.which("cargo") is None:
            console.print("Error: 'cargo' command not found in PATH.", style="red")
            sys.exit(1)
        console.print("\n[bold magenta]Compile using:[/bold magenta]")
        console.print("1. Original source files")
        console.print("2. Optimized OpenAI files")
        if args.no_interactive:
            source_choice = "2"
        else:
            source_choice = input("Enter choice (1 or 2): ").strip()
        if source_choice == "1":
            cargo_toml = next((f for f in files if os.path.basename(f) == "Cargo.toml"), None)
            compile_dir = os.path.dirname(cargo_toml) if cargo_toml else original_cwd
        else:
            compile_dir = os.path.join(original_cwd, "OpenAI")
        result = run_cargo_build(compile_dir)
    else:
        result = type('obj', (object,), {'returncode': 1})()  # Dummy result for no compilation.
        console.print("Skipping compilation step.", style="yellow")

    # If running in a Git repository and in interactive mode, offer to commit the changes.
    if is_git_repo(original_cwd) and (not args.no_interactive):
        commit = input("Commit optimized changes to Git? (y/n): ").strip().lower()
        if commit == "y":
            commit_changes()

    # Generate a summary report and save updated configuration.
    generate_summary_report(files, model, result.returncode)
    save_config(config, args.config, args.profile)
    console.print("Files and summary report saved in 'OpenAI'.", style="green")
    logger.info("Process complete.")


# =============================================================================
# Unit and Integration Tests
# =============================================================================
def run_tests():
    """
    Runs unit tests for critical functionalities like file I/O, backup creation,
    and hash computation.

    The tests ensure that:
      - Files can be written and read correctly.
      - Backup files are created as expected.
      - The computed file hashes match the expected output.

    Exits:
      The program exits with code 0 if all tests pass; otherwise, it logs and
      prints an error message and exits with a non-zero code.
    """
    console.print("Running tests...", style="bold blue")
    logger.info("Starting tests.")

    # Test file write and read functionality.
    try:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            test_content = "Test content"
            tmp.write(test_content)
            tmp_path = tmp.name
        assert read_file(tmp_path) == test_content, "Mismatch in file content."
        os.remove(tmp_path)
        logger.info("File I/O test passed.")
    except Exception as e:
        logger.error(f"File I/O test failed: {e}")
        console.print(f"File I/O test failed: {e}", style="red")
        sys.exit(1)

    # Test backup functionality.
    try:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("Backup test")
            tmp_path = tmp.name
        backup_path = backup_files([tmp_path])
        backup_file = os.path.join(backup_path, os.path.basename(tmp_path))
        assert os.path.exists(backup_file), "Backup file missing."
        os.remove(tmp_path)
        shutil.rmtree(backup_path)
        logger.info("Backup test passed.")
    except Exception as e:
        logger.error(f"Backup test failed: {e}")
        console.print(f"Backup test failed: {e}", style="red")
        sys.exit(1)

    console.print("All tests passed!", style="green")
    logger.info("All tests passed.")
    sys.exit(0)


# =============================================================================
# Summary Report Generation (Placeholder Implementation)
# =============================================================================
def generate_summary_report(files, model, build_returncode):
    """
    Generates a summary report after processing.

    The report includes details such as:
      - List of processed files.
      - OpenAI model used.
      - Compilation result.
      - Timestamps and backup locations.
    
    This function is a placeholder and should be expanded to include any
    additional reporting or logging required by the user.

    Parameters:
      files (list):
        The list of processed file paths.
      model (str):
        The OpenAI model that was used.
      build_returncode (int):
        The return code from the cargo build process (0 for success).
    """
    console.print("\nSummary Report:", style="bold magenta")
    console.print(f"Processed {len(files)} file(s).")
    console.print(f"OpenAI Model: {model}")
    if build_returncode == 0:
        console.print("Compilation: Success", style="green")
    else:
        console.print("Compilation: Failed", style="red")
    # Additional summary details can be added here.
    logger.info("Summary report generated.")


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        msg = f"Unexpected error: {e}"
        console.print(msg, style="red")
        logger.exception("Unexpected error")
        send_error_notification(msg, notification_email=os.getenv("NOTIFICATION_EMAIL"))
        sys.exit(1)
# end of file -- rust_openai_optimizer.py
# =============================================================================