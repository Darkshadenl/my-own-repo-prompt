#!/usr/bin/env python3
"""
Repository Prompt Generator

This script scans one or more repository directories and generates a structured "repo prompt" containing
a file map, file contents, and a placeholder for user instructions. The generated prompt is printed
to the console and copied to the clipboard.

Usage:
    python generate_repo_prompt.py [/path/to/repo1 [/path/to/repo2 ...]]

If no paths are provided, the current directory is used.
"""

import os
import sys
import argparse
from pathlib import Path
import pyperclip
import pathspec
import json

try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("tiktoken not installed. Token count will not be available.", file=sys.stderr)
    print("Install with: pip install tiktoken", file=sys.stderr)

# Define set of allowed file extensions (case-insensitive)
ALLOWED_EXTENSIONS = {
    ".css",
    ".cursorrules",
    ".dev",
    ".env",
    ".gitignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mdx",
    ".py",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".svelte",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
    ".vue",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".pl",
    ".swift",
    ".cs",
    ".fs",
    ".clj",
    ".ex",
    ".exs",
    ".erl",
    ".kt",
    ".scala",
    ".lua",
    ".r",
    ".toml",
    ".dart",
    ".elm",
    ".tf",
    ".xml",
    ".graphql",
    ".ipynb",
}

# Define directories to always skip
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "target",
}

# Define mapping from file extensions to language IDs for code blocks
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".md": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".sh": "bash",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".cs": "csharp",
    ".fs": "fsharp",
    ".clj": "clojure",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".kt": "kotlin",
    ".scala": "scala",
    ".lua": "lua",
    ".r": "r",
    ".toml": "toml",
    ".dart": "dart",
    ".elm": "elm",
    ".tf": "terraform",
    ".xml": "xml",
    ".graphql": "graphql",
    ".svelte": "svelte",
    ".vue": "vue",
    ".sql": "sql",
    ".pl": "perl",
    ".ini": "ini",
    # Default for other extensions
    ".txt": "text",
    ".env": "text",
    ".gitignore": "text",
    ".cursorrules": "text",
}


def convert_to_relative_path(path, repo_root):
    """Convert an absolute path to a relative path within the repo, starting with ./"""
    try:
        rel_path = Path(path).relative_to(repo_root)
        return f"./{rel_path}"
    except ValueError:
        # This should never happen if paths are within the repo
        print(f"Error: Path {path} is not relative to {repo_root}", file=sys.stderr)
        return str(path)


def load_gitignore_spec(repo_path):
    """
    Load and parse all .gitignore files in the repository.
    Returns a pathspec object that can be used to match paths against gitignore rules.
    """
    gitignore_files = list(Path(repo_path).glob("**/.gitignore"))

    # If no gitignore files found, return a spec that matches nothing
    if not gitignore_files:
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, [])

    patterns = []

    for gitignore_file in gitignore_files:
        try:
            # Calculate relative path from repo root to gitignore directory
            gitignore_dir = gitignore_file.parent
            rel_dir = os.path.relpath(gitignore_dir, repo_path)
            rel_dir = "" if rel_dir == "." else rel_dir + "/"

            with open(gitignore_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Handle patterns specific to the gitignore's directory
                    if not line.startswith("/") and not line.startswith("!"):
                        # Convert relative patterns to be relative to the repository root
                        if rel_dir:
                            line = f"{rel_dir}{line}"

                    patterns.append(line)
        except Exception as e:
            print(f"Warning: Error processing {gitignore_file}: {e}", file=sys.stderr)

    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)


def get_filtered_paths(repo_path):
    """
    Recursively traverse the repository and return a filtered, sorted list of relative paths.
    Applies filtering based on skip directories, gitignore rules, and allowed extensions.
    """
    repo_path = Path(repo_path).resolve()

    # Load gitignore specs
    try:
        gitignore_spec = load_gitignore_spec(repo_path)
    except Exception as e:
        print(f"Warning: Failed to load gitignore rules: {e}", file=sys.stderr)
        # Create a spec that doesn't match anything
        gitignore_spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, []
        )

    filtered_paths = []

    # Walk through the repository
    for path in repo_path.rglob("*"):
        # Skip if path doesn't exist (e.g., broken symlinks)
        if not path.exists():
            continue

        # Skip if the path or any of its parents is in SKIP_DIRS
        if any(part in SKIP_DIRS for part in path.parts):
            continue

        # Get relative path from repo root for gitignore matching
        rel_path_for_gitignore = str(path.relative_to(repo_path))

        # Skip if matched by gitignore
        if gitignore_spec.match_file(rel_path_for_gitignore):
            continue

        # Get relative path with ./ prefix for our output
        rel_path = convert_to_relative_path(path, repo_path)

        # For files, check if extension is allowed
        if path.is_file():
            ext = path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

        filtered_paths.append(rel_path)

    # Sort paths - directories first, then files
    return sorted(filtered_paths, key=lambda p: (p.count("/"), p))


def generate_file_map(repo_path, filtered_paths):
    """Generate the file_map section of the prompt with tree structure"""
    repo_path = Path(repo_path).resolve()
    root_dir_name = repo_path.name

    lines = [f"{root_dir_name}/"]

    # Group paths by their parent directory
    paths_by_level = {}
    for path in filtered_paths:
        parts = path.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            if prefix not in paths_by_level:
                paths_by_level[prefix] = []
            if i == len(parts) - 1:
                paths_by_level[prefix].append(parts[i])

    # Track which directories are "last" at their level
    last_at_level = {}

    # Generate the tree structure
    def add_path(path, indent=""):
        parts = path.split("/")[1:]  # Skip the leading ./ part
        if not parts:  # Skip empty path
            return

        current_path = "./"
        current_indent = ""

        for i, part in enumerate(parts):
            prev_path = current_path
            current_path = (
                f"{current_path}/{part}" if current_path != "./" else f"./{part}"
            )

            # Check if we've already processed this path
            if current_path in processed_paths:
                continue

            processed_paths.add(current_path)

            # Determine if this is the last item at its level
            parent_dir = prev_path
            siblings = paths_by_level.get(parent_dir, [])
            is_last = part == siblings[-1] if siblings else False
            last_at_level[len(current_indent)] = is_last

            # Generate the correct prefix based on whether items are last in their directories
            prefix = ""
            for j in range(0, len(current_indent), 4):
                if j + 4 >= len(current_indent):  # Current level
                    if is_last:
                        prefix += "└── "
                    else:
                        prefix += "├── "
                else:  # Parent levels
                    if last_at_level.get(j, False):
                        prefix += "    "
                    else:
                        prefix += "│   "

            # Add trailing slash for directories
            display_name = part
            if Path(repo_path / current_path.lstrip("./")).is_dir():
                display_name += "/"

            lines.append(f"{prefix}{display_name}")

            current_indent += "    "

    processed_paths = set()
    for path in filtered_paths:
        add_path(path)

    # Create a dictionary structure where keys are paths
    file_map = {}
    # Add the root directory
    file_map[f"./{root_dir_name}/"] = []

    # Process each path to create a proper structure
    for path in filtered_paths:
        abs_path = repo_path / path.lstrip("./")
        if abs_path.is_dir():
            file_map[path] = []

    return file_map


def generate_file_contents(repo_path, filtered_paths):
    """Generate the file_contents section of the prompt"""
    repo_path = Path(repo_path).resolve()
    file_contents = {}

    # Process only files, not directories
    file_paths = [
        p for p in filtered_paths if Path(repo_path / p.lstrip("./")).is_file()
    ]

    for rel_path in file_paths:
        abs_path = repo_path / rel_path.lstrip("./")

        # Get language ID for code block based on file extension
        ext = abs_path.suffix.lower()
        lang_id = LANGUAGE_MAP.get(ext, "text")

        try:
            # Try to read the file with UTF-8 encoding
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Format the content block with language ID
            formatted_content = f"```{lang_id}\n{content}\n```"
            file_contents[rel_path] = formatted_content
        except UnicodeDecodeError:
            print(
                f"Warning: Skipping file {rel_path} due to encoding issues",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"Error reading {rel_path}: {e}", file=sys.stderr)

    return file_contents


def generate_user_instructions():
    """Generate the user_instructions section of the prompt"""
    placeholder = "<!-- Add your instructions for the LLM here -->"
    return placeholder


def count_tokens(text):
    """Count the number of tokens in the text using tiktoken"""
    if not TIKTOKEN_AVAILABLE:
        return None

    try:
        # Use cl100k_base encoding (used by ChatGPT and GPT-4)
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        return len(tokens)
    except Exception as e:
        print(f"Error counting tokens: {e}", file=sys.stderr)
        return None


def main():
    """Main function to handle command line arguments and generate the prompt."""
    parser = argparse.ArgumentParser(
        description="Generate a structured repository prompt for AI code assistance."
    )
    parser.add_argument(
        "repo_paths",
        nargs="*",
        default=[os.getcwd()],
        help="Paths to repository directories (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        choices=["print", "clipboard", "json"],
        default="json",
        help="Output method (default: json)",
    )
    args = parser.parse_args()

    all_file_maps = {}
    all_file_contents = {}

    # Ensure we have at least one repo path
    if not args.repo_paths:
        args.repo_paths = [os.getcwd()]

    # Process each repo
    for repo_path in args.repo_paths:
        repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(repo_path):
            print(f"Error: {repo_path} is not a valid directory.", file=sys.stderr)
            continue

        print(f"Processing {repo_path}...", file=sys.stderr)
        filtered_paths = get_filtered_paths(repo_path)

        # Get file map and contents
        repo_file_map = generate_file_map(repo_path, filtered_paths)
        repo_file_contents = generate_file_contents(repo_path, filtered_paths)

        # Merge into main dictionaries
        all_file_maps.update(repo_file_map)
        all_file_contents.update(repo_file_contents)

    # Generate user instructions section
    user_instructions = generate_user_instructions()

    # Combine all parts into the final prompt
    full_prompt = {}

    # Add file contents with metadata about type
    for path, content in all_file_contents.items():
        full_prompt[path] = {"content": content, "type": "file"}

    # Add directory structure
    for path, children in all_file_maps.items():
        if path.endswith("/"):
            full_prompt[path] = {"children": children, "type": "directory"}

    # Add user instructions
    full_prompt["user_instructions"] = {
        "content": user_instructions,
        "type": "instructions",
    }

    # Output according to the specified method
    if args.output == "print":
        print(json.dumps(full_prompt, indent=2))
    elif args.output == "clipboard":
        pyperclip.copy(json.dumps(full_prompt, indent=2))
        print("Repository prompt copied to clipboard.", file=sys.stderr)
    elif args.output == "json":
        # For API use, print only the JSON output to stdout
        print(json.dumps(full_prompt))

    # Get token count if available
    if TIKTOKEN_AVAILABLE:
        prompt_text = json.dumps(full_prompt, indent=2)
        token_count = count_tokens(prompt_text)
        print(f"\nToken count: {token_count}", file=sys.stderr)
        print(
            "Note: This is approximate and may vary slightly from the actual count.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
