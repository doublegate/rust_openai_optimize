#!/usr/bin/env python3
'''
# =============================================================================
# rust_openai_optimizer.py - v0.3.1
# =============================================================================
# Author:
#     DoubleGate -- 2025: https://github.com/doublegate/rust_openai_optimize
#
# Purpose:
#     Optimize, debug, restructure, and add comprehensive technical comments to Rust
#     source code by leveraging OpenAI's LLM API. This script is designed to transform
#     Rust projects with thorough documentation and enhanced code quality, adhering to
#     the rigorous commenting and documentation standards found in idiomatic Rust.
#
# Detailed Explanation:
#     - The script processes multiple Rust source files—including Cargo.toml and .rs files—
#       to produce optimized code that not only compiles successfully but also provides
#       in-depth technical commentary akin to Rust's own documentation practices.
#
#     - Extensive logging, configuration management, and error handling ensure that each
#       step is traceable, robust, and maintainable. Each function is meticulously commented,
#       explaining inputs, outputs, and exceptional behavior, mirroring the transparency and
#       explicitness of Rust's coding standards.
#
# Execution Environment:
#     - The above shebang line ensures that when executed on Unix-like systems, the script is
#       run using the Python interpreter as defined in the environment, enabling cross-platform
#       compatibility.
#
# Developer Notes:
#     - The design leverages both synchronous and asynchronous methodologies to interface with
#       the OpenAI API, supporting a range of deployment scenarios.
#     - Comments throughout the codebase are enriched with detailed, technical descriptions to
#       facilitate maintenance and further development, following principles similar to Rust
#       emphasis on clarity, safety, and performance.
#
# Future Enhancements:
#     - Incorporate additional Rust-specific optimizations such as module-level documentation
#       and inline code annotations that simulate Rust's doc-comment style.
#     - Expand testing and benchmark suites inspired by Rust cargo testing framework.
#
# =============================================================================
'''
# =============================================================================
# Standard Library Imports
# =============================================================================
import os               # File system operations, environment variables.
import sys              # System-specific parameters and functions.
import subprocess       # To run external commands (e.g., cargo build).
import shutil           # High-level file operations (e.g., copying files).
import json             # JSON encoding/decoding for configuration.
from datetime import datetime  # Timestamps for backups and logs.
import time             # For delays in retry logic.
import random           # For jitter in exponential backoff.
import argparse         # For command-line argument parsing.
import logging          # Structured logging.
import asyncio          # For asynchronous API calls.
import smtplib          # (Optional) For sending email notifications.

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import openai           # OpenAI API client.
try:
    from openai.error import APIConnectionError, OpenAIError
except ImportError:
    APIConnectionError = Exception
    OpenAIError = Exception

from prompt_toolkit import PromptSession  # Interactive CLI session.
from prompt_toolkit.completion import PathCompleter  # CLI file path autocompletion.
from prompt_toolkit.key_binding import KeyBindings  # Custom key bindings.
from tqdm import tqdm   # Progress bars for lengthy operations.
from rich.console import Console  # Enhanced terminal output.

# =============================================================================
# Global Objects and Environment Checks
# =============================================================================
console = Console()

# Configure structured logging.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="rust_openai_optimizer.log",
    filemode="a"
)
logger = logging.getLogger(__name__)

# Ensure the OpenAI API key is set.
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    console.print("Error: OPENAI_API_KEY environment variable is not set. Exiting.", style="red")
    logger.error("OPENAI_API_KEY not set.")
    sys.exit(1)


# =============================================================================
# Helper Functions
# =============================================================================
def read_file(filepath):
    """
    Reads the entire contents of a file and returns it as a string.

    Parameters:
        filepath (str): The path to the file.

    Returns:
        str: Contents of the file.

    Raises:
        SystemExit: If reading fails.
    """
    try:
        with open(filepath, 'r') as file:
            data = file.read()
            logger.debug(f"Read file: {filepath}")
        return data
    except Exception as e:
        error_msg = f"Error reading file '{filepath}': {e}"
        console.print(error_msg, style="red")
        logger.error(error_msg)
        sys.exit(1)


def write_file(filepath, content):
    """
    Writes content to a file, overwriting it if it exists.

    Parameters:
        filepath (str): The destination path.
        content (str): The content to write.

    Raises:
        SystemExit: If writing fails.
    """
    try:
        with open(filepath, 'w') as file:
            file.write(content)
            logger.debug(f"Wrote file: {filepath}")
    except Exception as e:
        error_msg = f"Error writing file '{filepath}': {e}"
        console.print(error_msg, style="red")
        logger.error(error_msg)
        sys.exit(1)


def clear_screen():
    """
    Clears the terminal screen.

    Uses 'cls' on Windows and 'clear' on Unix.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def backup_files(files, backup_dir="backups"):
    """
    Creates a timestamped backup directory and copies the specified files.

    Parameters:
        files (list): List of file paths.
        backup_dir (str, optional): Parent backup directory.

    Returns:
        str: Path to the backup directory.

    Raises:
        SystemExit: If backup fails.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, timestamp)
    try:
        os.makedirs(backup_path, exist_ok=True)
        for file in files:
            shutil.copy(file, backup_path)
        logger.debug(f"Backup created at {backup_path}")
    except Exception as e:
        error_msg = f"Error backing up files: {e}"
        console.print(error_msg, style="red")
        logger.error(error_msg)
        sys.exit(1)
    return backup_path


def log_activity(activity):
    """
    Logs an activity message with a timestamp to 'activity.log'.

    Parameters:
        activity (str): Message to log.
    """
    try:
        with open('activity.log', 'a') as log:
            log.write(f"{datetime.now()} - {activity}\n")
        logger.info(activity)
    except Exception as e:
        console.print(f"Error logging activity: {e}", style="red")
        logger.error(f"Error logging activity: {e}")


def load_config(config_path="config.json"):
    """
    Loads configuration settings from a JSON file.

    Parameters:
        config_path (str): Path to config file.

    Returns:
        dict: Configuration data.
    """
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                config = json.load(file)
                logger.debug("Configuration loaded.")
            return config
        except Exception as e:
            error_msg = f"Error loading configuration: {e}"
            console.print(error_msg, style="red")
            logger.error(error_msg)
            return {}
    return {}


def save_config(config, config_path="config.json"):
    """
    Saves configuration settings to a JSON file.

    Parameters:
        config (dict): Configuration data.
        config_path (str): Destination path.
    """
    try:
        with open(config_path, 'w') as file:
            json.dump(config, file, indent=4)
            logger.debug("Configuration saved.")
    except Exception as e:
        error_msg = f"Error saving configuration: {e}"
        console.print(error_msg, style="red")
        logger.error(error_msg)


def send_error_notification(error_message, notification_email=None):
    """
    (Placeholder) Sends an error notification via email if configured.

    Parameters:
        error_message (str): The error message to send.
        notification_email (str, optional): Destination email address.

    Notes:
        To implement, configure SMTP settings and credentials.
    """
    if notification_email:
        # Example: Uncomment and configure if you wish to send an email.
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
                #     logger.info("Error notification sent.")
                # except Exception as e:
                #     logger.error(f"Failed to send error notification: {e}")
        console.print(f"(Notification) Would send error notification to {notification_email}: {error_message}", style="yellow")
        logger.info(f"(Notification) Would send error notification to {notification_email}: {error_message}")


# =============================================================================
# Core Processing Functions (Sync & Async)
# =============================================================================
def process_code(file_contents, file_names, model, retries=3, timeout=60):
    """
    Processes Rust source code by sending it to the OpenAI API.

    Constructs a detailed prompt for debugging, restructuring, and commenting
    the code. Uses retry logic with exponential backoff.

    Parameters:
        file_contents (str): Concatenated source file contents with headers.
        file_names (str): Comma-separated list of relative file paths.
        model (str): OpenAI model to use.
        retries (int): Number of retry attempts (default 3).
        timeout (int): Request timeout in seconds (default 60).

    Returns:
        str: Processed code as returned by the API.

    Raises:
        SystemExit: If the API call fails after retries.
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
    base_retry_delay = 5  # seconds
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
            logger.info("API call succeeded.")
            return response.choices[0].message.content
        except APIConnectionError as e:
            if attempt < retries:
                wait_time = base_retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                error_msg = (f"Error connecting to OpenAI API (attempt {attempt}/{retries}): {e}. "
                             f"Retrying in {wait_time:.2f} seconds...")
                console.print(error_msg, style="red")
                logger.error(error_msg)
                time.sleep(wait_time)
            else:
                error_msg = f"Error connecting to OpenAI API on attempt {attempt}. No more retries left."
                console.print(error_msg, style="red")
                logger.error(error_msg)
                sys.exit(1)
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {e}"
            console.print(error_msg, style="red")
            logger.error(error_msg)
            sys.exit(1)


async def process_code_async(file_contents, file_names, model, retries=3, timeout=60):
    """
    Asynchronously processes Rust source code using the OpenAI API.

    This function mirrors the synchronous version but uses async calls.
    
    Parameters:
        file_contents (str): Concatenated source file contents.
        file_names (str): Comma-separated list of relative file paths.
        model (str): OpenAI model to use.
        retries (int): Number of retry attempts.
        timeout (int): Timeout for the request.
    
    Returns:
        str: Processed code from the API.
    
    Raises:
        SystemExit: If the API call fails after retries.
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
    base_retry_delay = 5  # seconds
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
            logger.info("Async API call succeeded.")
            return response.choices[0].message.content
        except APIConnectionError as e:
            if attempt < retries:
                wait_time = base_retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                error_msg = (f"Async error connecting to OpenAI API (attempt {attempt}/{retries}): {e}. "
                             f"Retrying in {wait_time:.2f} seconds...")
                console.print(error_msg, style="red")
                logger.error(error_msg)
                await asyncio.sleep(wait_time)
            else:
                error_msg = f"Async error connecting to OpenAI API on attempt {attempt}. No more retries left."
                console.print(error_msg, style="red")
                logger.error(error_msg)
                sys.exit(1)
        except OpenAIError as e:
            error_msg = f"Async OpenAI API error: {e}"
            console.print(error_msg, style="red")
            logger.error(error_msg)
            sys.exit(1)

# =============================================================================
# Interactive File Selection and Model Choice Functions
# =============================================================================
def select_files():
    """
    Launches an interactive CLI for navigating directories and selecting files.

    Only files ending with '.rs' or named 'Cargo.toml' are selectable.

    Returns:
        list: List of absolute file paths selected.
    """
    session = PromptSession()
    completer = PathCompleter(expanduser=True)
    selected_files = []
    bindings = KeyBindings()

    def refresh():
        """Refreshes the display with current directory, file selections, and command help."""
        clear_screen()
        console.print(f"[bold cyan]Current Directory:[/bold cyan] {os.getcwd()}\n")
        console.print("[bold green]Selected Files:[/bold green]")
        for file in selected_files:
            console.print(f" - {file}")
        console.print(
            "\n[bold yellow]Commands:[/bold yellow]\n"
            "Enter: Open directory or select file\n"
            "Backspace: Go up directory\n"
            "d: Finish selection\n"
            "esc/q: Exit\n"
            "?: Help\n"
            "Tab: Autocomplete"
        )

    @bindings.add('enter')
    def _(event):
        """
        On Enter:
          - If the path is a directory, navigate into it.
          - If it's a valid file, add its absolute path to the selection.
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
        """On Backspace: move up one directory."""
        os.chdir('..')
        event.app.current_buffer.reset()
        refresh()

    @bindings.add('escape', eager=True)
    @bindings.add('q', eager=True)
    def _(event):
        """On Escape or q: exit immediately."""
        console.print("\nExiting program.", style="red")
        sys.exit(0)

    @bindings.add('d')
    def _(event):
        """On d: finish selection."""
        event.app.exit(result="done")

    @bindings.add('?')
    def _(event):
        """On ?: display help."""
        console.print(
            "\n[bold magenta]Help:[/bold magenta]\n"
            "Use Enter to open/select, Backspace to go up, d to finish, and esc/q to exit."
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
        str: The selected model name.
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
# Summary Report Generation
# =============================================================================
def generate_summary_report(files, model, compilation_result):
    """
    Generates a summary report of the optimization process and writes it to a file.

    The report includes:
      - The OpenAI model used.
      - Date and time.
      - List of processed files.
      - Compilation status.

    Parameters:
      files (list): Processed file paths.
      model (str): The OpenAI model used.
      compilation_result (int): Return code from cargo build.
    """
    report_path = os.path.join("OpenAI", "summary_report.txt")
    try:
        with open(report_path, 'w') as report:
            report.write("Rust Optimization Summary Report\n")
            report.write(f"Model used: {model}\n")
            report.write(f"Date: {datetime.now()}\n\n")
            report.write("Processed Files:\n")
            for f in files:
                report.write(f" - {f}\n")
            report.write(f"\nCompilation Status: {'Success' if compilation_result == 0 else 'Failure'}\n")
        logger.info("Summary report generated.")
    except Exception as e:
        error_msg = f"Error generating summary report: {e}"
        console.print(error_msg, style="red")
        logger.error(error_msg)
        log_activity(error_msg)


def check_cargo():
    """
    Checks if the 'cargo' command is available in PATH.

    Raises:
        SystemExit: If cargo is not found.
    """
    if shutil.which("cargo") is None:
        error_msg = "Error: 'cargo' command not found. Please install Rust and Cargo."
        console.print(error_msg, style="red")
        logger.error(error_msg)
        sys.exit(1)


# =============================================================================
# Unit and Integration Testing
# =============================================================================
def run_tests():
    """
# Define CLI arguments for controlling behavior and configuration.
    Runs basic tests for file I/O and backup functionality.

    This function tests:
      - Writing and reading a temporary file.
      - Creating a backup of that file.
    
    Exits with code 0 if all tests pass.
    """
    import tempfile

    console.print("Running tests...", style="bold blue")
    logger.info("Starting tests.")

    # Test write and read.
    try:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            test_content = "Test content"
            tmp.write(test_content)
            tmp_path = tmp.name
        read_back = read_file(tmp_path)
        assert read_back == test_content, "Read content does not match written content."
        os.remove(tmp_path)
        logger.info("File I/O test passed.")
    except Exception as e:
        logger.error(f"File I/O test failed: {e}")
        console.print(f"File I/O test failed: {e}", style="red")
        sys.exit(1)

    # Test backup_files.
    try:
        with tempfile.NamedTemporaryFile("w+", delete=False) as tmp:
            tmp.write("Backup test")
            tmp_path = tmp.name
        backup_path = backup_files([tmp_path])
        backup_file = os.path.join(backup_path, os.path.basename(tmp_path))
        assert os.path.exists(backup_file), "Backup file not found."
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
# Main Execution Function
# =============================================================================
def main():
    """
    Orchestrates the complete Rust source code optimization workflow via OpenAI.
    
    This function performs the following high-level steps:
      1. Parse and validate CLI arguments.
      2. Load and update persistent configuration.
      3. Determine and confirm OpenAI model selection.
      4. File selection for processing.
      5. Backup original files.
      6. Aggregate source code.
      7. Process code with the OpenAI API.
      8. Distribute processed code into individual files.
      9. Optionally compile the code.
      10. Generate summary report and persist configuration.
    """
    # -------------------------------------------------------------------------
    # Step 1: Command-Line Argument Parsing and Configuration Loading
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Rust OpenAI Optimizer: Optimize, debug, and comment Rust code using OpenAI LLMs."
    )
    # Define CLI arguments for controlling behavior and configuration.
    parser.add_argument("--model", type=str, help="Specify the OpenAI model (e.g., gpt-4, gpt-3.5-turbo).")
    parser.add_argument("--files", nargs="+", help="List of files to process. If omitted, interactive selection is used.")
    parser.add_argument("--no-interactive", action="store_true", help="Disable interactive prompts for file selection.")
    parser.add_argument("--build", action="store_true", help="Automatically run 'cargo build' after processing.")
    parser.add_argument("--async-mode", action="store_true", help="Use asynchronous API calls to improve processing speed.")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the configuration file for persistent settings.")
    parser.add_argument("--test", action="store_true", help="Run unit tests to verify application functionality and exit.")
    parser.add_argument("--retry", type=int, default=3, help="Number of API retry attempts in case of transient failures (default: 3).")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout duration in seconds for the OpenAI API call (default: 60).")
    parser.add_argument("--notification-email", type=str, help="Email address to receive error notifications, if configured.")

    args = parser.parse_args()

    # Immediately run tests and exit if the test flag is provided.
    if args.test:
        run_tests()

    # Load configuration and override with CLI values.
    config = load_config(args.config)
    if args.retry:
        config["retry"] = args.retry
    if args.timeout:
        config["timeout"] = args.timeout

    # -------------------------------------------------------------------------
    # Step 2: Determine and Confirm OpenAI Model Selection
    # -------------------------------------------------------------------------
    # Prioritize the model provided via CLI, then the saved config, and finally reach out
    # to the user for interactive selection if needed.
    if args.model:
        model = args.model
    elif "model" in config:
        model = config["model"]
        if not args.no_interactive:
            console.print(f"Using previously configured model: [bold green]{model}[/bold green]")
            change = input("Change model? (y/n): ").strip().lower()
            if change == "y":
                model = select_model()
    else:
        model = select_model()
    config["model"] = model

    # -------------------------------------------------------------------------
    # Step 3: File Selection for Processing
    # -------------------------------------------------------------------------
    # Files can be provided directly via CLI or selected interactively.
    if args.files:
        files = [os.path.abspath(f) for f in args.files]
    elif args.no_interactive:
        console.print("Error: No files provided and interactive mode is disabled.", style="red")
        sys.exit(1)
    else:
        files = select_files()

    if not files:
        console.print("No files selected. Exiting.", style="red")
        sys.exit(0)
    config["selected_files"] = files

    # -------------------------------------------------------------------------
    # Step 4: Backup Original Files Before Modification
    # -------------------------------------------------------------------------
    # A backup is crucial to ensure that the source files are preserved in their original state.
    backup_dir = backup_files(files)
    log_activity(f"Backed up files to {backup_dir}")

    # Save the present working directory (typically the project's root) for constructing relative paths.
    original_cwd = os.getcwd()

    # -------------------------------------------------------------------------
    # Step 5: Aggregate Source Code Contents and Filenames
    # -------------------------------------------------------------------------
    # Read each file's content and append a standardized header for identification.
    file_contents = ""
    file_names = ""
    for f in tqdm(files, desc="Reading Files"):
        content = read_file(f)
        rel_path = os.path.relpath(f, original_cwd)
    # Append header in a format resembling Rust module documentation.
        file_contents += f"\n\n## File: {rel_path} ##\n{content}"
        file_names += f"{rel_path}, "

    # -------------------------------------------------------------------------
    # Step 6: Process Files with the OpenAI API (Sync vs Async)
    # -------------------------------------------------------------------------
    # Send the prepared source code to the OpenAI API with enhanced error handling.
    if args.async_mode:
        processed_output = asyncio.run(
            process_code_async(
                file_contents,
                file_names.strip(", "),
                model,
                retries=config.get("retry", 3),
                timeout=config.get("timeout", 60)
            )
        )
    else:
        processed_output = process_code(
            file_contents,
            file_names.strip(", "),
            model,
            retries=config.get("retry", 3),
            timeout=config.get("timeout", 60)
        )
    logger.info("Processing complete using the OpenAI API.")

    # -------------------------------------------------------------------------
    # Step 7: Distribute Processed Code into Individual Files
    # -------------------------------------------------------------------------
    # The API returns a string with headers delineating each file's content.
    outputs = processed_output.split("## File: ")[1:]
    output_dir = "OpenAI"  # Output directory for the modified files.
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        error_msg = f"Error creating output directory '{output_dir}': {e}"
        console.print(error_msg, style="red")
        logger.error(error_msg)
        sys.exit(1)

    # Iterate over each file segment in the output.
    for output in tqdm(outputs, desc="Writing Files"):
        header_end = output.find(" ##")
        rel_path = output[:header_end].strip()
        code = output[header_end + 3:].strip()
        dest_file = os.path.join(output_dir, rel_path)
        try:
    # Ensure that the directory for the current file is created.
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            write_file(dest_file, code)
        except Exception as e:
            error_msg = f"Error writing optimized file '{dest_file}': {e}"
            console.print(error_msg, style="red")
            logger.error(error_msg)
            log_activity(error_msg)

    # -------------------------------------------------------------------------
    # Step 8: Optional Compilation Using 'cargo build'
    # -------------------------------------------------------------------------
    # Prompt the user (or automatically proceed in non-interactive mode) to compile
    # the original or optimized source files using Rust's build system.
    if args.build or (not args.no_interactive and input("Run 'cargo build'? (y/n): ").strip().lower() == "y"):
        check_cargo()  # Validates the installation of Cargo.
        console.print("\n[bold magenta]Compile using:[/bold magenta]")
        console.print("1. Original source files")
        console.print("2. Optimized OpenAI files")
        source_choice = "2" if args.no_interactive else input("Enter choice (1 or 2): ").strip()
        if source_choice == "1":
            cargo_toml = next((f for f in files if os.path.basename(f) == "Cargo.toml"), None)
            compile_dir = os.path.dirname(cargo_toml) if cargo_toml else original_cwd
        else:
            compile_dir = os.path.join(original_cwd, "OpenAI")
        try:
    # Invoke Cargo build and capture the output.
            result = subprocess.run(
                ["cargo", "build"],
                cwd=compile_dir,
                capture_output=True,
                text=True
            )
        except Exception as e:
            error_msg = f"Error during 'cargo build': {e}"
            console.print(error_msg, style="red")
            logger.error(error_msg)
            log_activity(error_msg)
            sys.exit(1)
        log_activity(f"Compilation {'success' if result.returncode == 0 else 'failure'} "
                     f"({'original' if source_choice == '1' else 'optimized'})")
        if result.returncode == 0:
            console.print("Compilation successful!", style="green")
        else:
            console.print("Compilation failed:", style="red")
            console.print(result.stderr)
    else:
    # If compilation is skipped, create a dummy result object for reporting.
        result = type('obj', (object,), {'returncode': 1})()
        console.print("Skipping compilation step.", style="yellow")

    # -------------------------------------------------------------------------
    # Step 9: Generate Summary Report and Save Updated Configuration
    # -------------------------------------------------------------------------
    # Create a summary report detailing the process (including the OpenAI model used,
    # timestamp, file list, and compilation outcome) and update the configuration file.
    generate_summary_report(files, model, result.returncode)
    save_config(config, args.config)
    console.print("Files / Summary Report Saved in 'OpenAI' -- Configuration Saved", style="green")


# =============================================================================
# Entry Point
# =============================================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        console.print(error_msg, style="red")
        logger.exception("Unexpected error")
        send_error_notification(error_msg, notification_email=os.getenv("NOTIFICATION_EMAIL"))
        sys.exit(1)

# end of script - rust_openai_optimizer.py