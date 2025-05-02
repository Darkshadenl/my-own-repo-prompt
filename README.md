# Repository Prompt Generator

A powerful tool to generate structured prompts for Large Language Models (LLMs) by analyzing your codebase. Perfect for getting high-quality, context-aware responses from AI assistants.

## Features

- 📁 Recursive repository scanning
- 🎯 Smart file filtering based on extensions
- 🚫 Gitignore-aware file exclusion
- 📊 Token count estimation (with tiktoken)
- 🎨 Syntax highlighting in generated prompts
- 🔧 Customizable folder exclusions
- 📝 Custom user instructions support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/repo-prompt.git
cd repo-prompt
```

2. Install dependencies:
```bash
pip install pyperclip pathspec tiktoken
```

## Usage

Basic usage:
```bash
python generate_repo_prompt.py [/path/to/repo1 [/path/to/repo2 ...]]
```

### Command Line Arguments

- Repository paths (optional): One or more paths to repositories
  - Default: Current directory
- `--output` or `-o`: Output method
  - Choices: `print`, `clipboard`, `json` (default)
- `--ignore-folders`: Additional folders to ignore
  - Example: `--ignore-folders tests cache temp`
- `--user-instructions`: Custom instructions for the LLM
  - Example: `--user-instructions "Please analyze the code structure"`

### Examples

1. Process current directory:
```bash
python generate_repo_prompt.py
```

2. Process specific repository with custom ignored folders:
```bash
python generate_repo_prompt.py /path/to/repo --ignore-folders tests cache
```

3. Process multiple repositories with custom instructions:
```bash
python generate_repo_prompt.py /path/to/repo1 /path/to/repo2 --user-instructions "Analyze the differences between these codebases"
```

4. Output to clipboard instead of JSON:
```bash
python generate_repo_prompt.py -o clipboard
```

## Output Format

The tool generates a structured JSON output containing:
- File map (directory structure)
- File contents (with syntax highlighting)
- User instructions

For detailed information about the architecture and internal workings, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 