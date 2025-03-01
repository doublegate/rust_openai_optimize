import openai
import os
import subprocess
import sys
import shutil
import json
from datetime import datetime
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.key_binding import KeyBindings
from tqdm import tqdm
from rich.console import Console

# Rich console for enhanced output
console = Console()

# Set your OpenAI API key
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Helper functions
def read_file(filepath):
    with open(filepath, 'r') as file:
        return file.read()

def write_file(filepath, content):
    with open(filepath, 'w') as file:
        file.write(content)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def backup_files(files, backup_dir="backups"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, timestamp)
    os.makedirs(backup_path, exist_ok=True)
    for file in files:
        shutil.copy(file, backup_path)
    return backup_path

def log_activity(activity):
    with open('activity.log', 'a') as log:
        log.write(f"{datetime.now()} - {activity}\n")

# Function to process code via OpenAI
def process_code(file_contents, file_names, model):
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
    ## File: filename.rs ##
    <processed code here>
    """

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an assistant specializing in Rust programming."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    return response.choices[0].message.content

# Interactive file selection
def select_files():
    session = PromptSession()
    completer = PathCompleter(expanduser=True)
    selected_files = []

    bindings = KeyBindings()

    def refresh():
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
        os.chdir('..')
        event.app.current_buffer.reset()
        refresh()

    @bindings.add('escape', eager=True)
    @bindings.add('q', eager=True)
    def _(event):
        console.print("\nExiting program.", style="red")
        sys.exit(0)

    @bindings.add('d')
    def _(event):
        event.app.exit(result="done")

    @bindings.add('?')
    def _(event):
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

# Model selection
def select_model():
    models = ["gpt-4-turbo", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]
    console.print("[bold magenta]Select OpenAI model:[/bold magenta]")
    for idx, model in enumerate(models, 1):
        console.print(f"{idx}. {model}")
    while True:
        try:
            choice = int(input("Enter choice: "))
            return models[choice - 1]
        except (ValueError, IndexError):
            console.print("Invalid selection.", style="red")

# Generate summary report
def generate_summary_report(files, model, compilation_result):
    report_path = os.path.join("OpenAI", "summary_report.txt")
    with open(report_path, 'w') as report:
        report.write("Rust Optimization Summary Report\n")
        report.write(f"Model used: {model}\n")
        report.write(f"Date: {datetime.now()}\n\n")
        report.write("Processed Files:\n")
        for file in files:
            report.write(f" - {file}\n")
        report.write(f"\nCompilation Status: {'Success' if compilation_result == 0 else 'Failure'}\n")

# Main script
if __name__ == "__main__":
    clear_screen()
    console.print("[bold blue]Interactive Rust Optimizer (OpenAI)[/bold blue]\n")

    model = select_model()
    files = select_files()

    if not files:
        console.print("No files selected. Exiting.", style="red")
        sys.exit(0)

    backup_dir = backup_files(files)
    log_activity(f"Backed up files to {backup_dir}")

    file_contents = ""
    file_names = ""

    for file_path in tqdm(files, desc="Reading Files"):
        content = read_file(file_path)
        file_name = os.path.basename(file_path)
        file_contents += f"\n\n## File: {file_name} ##\n{content}"
        file_names += f"{file_name}, "

    processed_output = process_code(file_contents, file_names.strip(", "), model)
    outputs = processed_output.split("## File: ")[1:]

    output_dir = "OpenAI"
    os.makedirs(output_dir, exist_ok=True)

    for output in tqdm(outputs, desc="Writing Files"):
        header_end = output.find(" ##")
        filename = output[:header_end].strip()
        code = output[header_end+3:].strip()
        write_file(os.path.join(output_dir, filename), code)

    result = subprocess.run(["cargo", "build"], cwd=output_dir, capture_output=True, text=True)
    log_activity(f"Compilation {'success' if result.returncode == 0 else 'failure'}")

    if result.returncode == 0:
        console.print("Compilation successful!", style="green")
    else:
        console.print("Compilation failed:", style="red")
        console.print(result.stderr)
        
    # Generate 'Summary Report'
    generate_summary_report(files, model, result.returncode)

    console.print("Files saved in 'OpenAI'.")