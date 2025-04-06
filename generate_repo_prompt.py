#!/usr/bin/env python3
"""
Repository Prompt Generator

This script scans a given repository directory and generates a structured "repo prompt" containing
a file map, file contents, and a placeholder for user instructions. The generated prompt is printed
to the console and copied to the clipboard.

Usage:
    python generate_repo_prompt.py /path/to/repo
"""

import os
import sys
import argparse
from pathlib import Path
import pyperclip
import pathspec

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

    return "<file_map>\n" + "\n".join(lines) + "\n</file_map>"


def generate_file_contents(repo_path, filtered_paths):
    """Generate the file_contents section of the prompt"""
    repo_path = Path(repo_path).resolve()
    content_blocks = []

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

            # Format the content block
            block = f"File: {rel_path}\n```{lang_id}\n{content}\n```\n"
            content_blocks.append(block)
        except UnicodeDecodeError:
            print(
                f"Warning: Skipping file {rel_path} due to encoding issues",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"Error reading {rel_path}: {e}", file=sys.stderr)

    return "<file_contents>\n" + "\n".join(content_blocks) + "\n</file_contents>"


def generate_user_instructions():
    """Generate the user_instructions section of the prompt"""
    placeholder = "<!-- Voeg hier je instructies voor de LLM toe -->"
    return f"<user_instructions>\n{placeholder}\n</user_instructions>"


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate a repository prompt for an LLM"
    )
    parser.add_argument("repo_path", help="Path to the repository to scan")
    args = parser.parse_args()

    # Validate input path
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Path {repo_path} does not exist", file=sys.stderr)
        sys.exit(1)
    if not repo_path.is_dir():
        print(f"Error: Path {repo_path} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning repository: {repo_path}")

    # Get filtered paths
    filtered_paths = get_filtered_paths(repo_path)

    if not filtered_paths:
        print("Warning: No files found after filtering", file=sys.stderr)

    # Generate prompt sections
    file_map = generate_file_map(repo_path, filtered_paths)
    file_contents = generate_file_contents(repo_path, filtered_paths)
    user_instructions = generate_user_instructions()

    # Combine sections
    prompt = f"{file_map}\n\n{file_contents}\n\n{user_instructions}"

    # Print to stdout
    print("\nGenerated Repository Prompt:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)

    # Copy to clipboard
    try:
        pyperclip.copy(prompt)
        print("\nRepository prompt has been copied to your clipboard.")
    except Exception as e:
        print(f"\nFailed to copy to clipboard: {e}", file=sys.stderr)
        print("You may need to manually copy the prompt.")

    print(
        f"\nTotal files processed: {len([p for p in filtered_paths if Path(repo_path / p.lstrip('./')).is_file()])}"
    )


if __name__ == "__main__":
    main()
