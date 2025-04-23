# Repository Prompt Generator

This tool scans one or more repositories and generates a structured prompt for language models (LLMs) containing:
1. A file map (directory tree structure)
2. File contents (for supported file types)
3. A placeholder for user instructions

The generated prompt is printed to the console and copied to the clipboard.

## Installation

1. Ensure you have Python 3.6+ installed
2. Install the required dependencies:

```bash
pip install pyperclip pathspec tiktoken
```

Or use the requirements.txt file:

```bash
pip install -r requirements.txt
```

## Usage

Run the script with paths to the repositories you want to scan:

```bash
python generate_repo_prompt.py /path/to/repository1 [/path/to/repository2 ...]
```

You can scan a single repository:
```bash
python generate_repo_prompt.py /path/to/your/repository
```

Or multiple repositories at once:
```bash
python generate_repo_prompt.py /path/to/repo1 /path/to/repo2 /path/to/repo3
```

### Features

- Supports scanning multiple repositories at once
- Respects `.gitignore` rules (using the pathspec library to parse gitignore patterns)
- Skips common directories like `.git`, `node_modules`, etc.
- Only includes files with supported extensions
- Generates a tree-like file map similar to the `tree` command
- Copies the result to clipboard (if pyperclip is working in your environment)
- Counts tokens in the generated prompt (if tiktoken is installed)
- Provides feedback on which LLM models can handle the prompt size

### Output Format

The generated prompt has the following structure:

```
<file_map>
root_dir_name/
├── file1.ext
├── dir1/
│   ├── file2.ext
│   └── file3.ext
└── dir2/
    └── file4.ext
</file_map>

<file_contents>
File: ./file1.ext
```language
file content here
```

File: ./dir1/file2.ext
```language
file content here
```

... more files ...
</file_contents>

<user_instructions>
<!-- Voeg hier je instructies voor de LLM toe -->
</user_instructions>

## Customization

You can modify the script to change:
- The set of allowed file extensions (`ALLOWED_EXTENSIONS`)
- Directories to skip (`SKIP_DIRS`)
- Language mappings for syntax highlighting (`LANGUAGE_MAP`) 