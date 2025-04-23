#!/usr/bin/env python3
"""
Repository Prompt Server

This Flask server provides endpoints to:
1. Get the file structure by executing the generate_repo_prompt.py script
2. Get the content of a specified file
3. Select a starting directory
"""

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import subprocess
import os
import json

app = Flask(__name__)
# Configure CORS to allow all origins, methods, and headers
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    },
)

# Global variable to store the current directory
current_directory = os.path.dirname(os.path.abspath(__file__))


@app.route("/api/get-structure", methods=["GET"])
def get_structure():
    """
    Execute generate_repo_prompt.py and return the file structure as JSON

    Returns:
        JSON: The file structure
    """
    try:
        # Path to the script
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "generate_repo_prompt.py"
        )

        # Execute the script and capture the output, passing the current directory as an argument
        result = subprocess.run(
            ["python", script_path, current_directory],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the JSON output
        structure = json.loads(result.stdout)

        return jsonify({"structure": structure})

    except subprocess.CalledProcessError as e:
        return (
            jsonify(
                {
                    "error": "Failed to generate structure",
                    "details": str(e),
                    "stderr": e.stderr,
                }
            ),
            500,
        )

    except json.JSONDecodeError as e:
        return (
            jsonify(
                {"error": "Failed to parse structure output as JSON", "details": str(e)}
            ),
            500,
        )

    except Exception as e:
        return (
            jsonify({"error": "An unexpected error occurred", "details": str(e)}),
            500,
        )


@app.route("/api/set-directory", methods=["POST", "OPTIONS"])
@cross_origin()
def set_directory():
    """
    Set the current directory for scanning

    Request Body:
        path: The directory path to set

    Returns:
        JSON: Success/error message
    """
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        return "", 204

    global current_directory

    data = request.json
    if not data or "path" not in data:
        return jsonify({"error": "No directory path provided"}), 400

    new_directory = data["path"]

    # Basic validation
    if not os.path.isdir(new_directory):
        return jsonify({"error": f"Not a valid directory: {new_directory}"}), 400

    # Update the current directory
    current_directory = new_directory

    return jsonify(
        {"success": True, "message": f"Current directory set to: {new_directory}"}
    )


@app.route("/api/current-directory", methods=["GET"])
def get_current_directory():
    """
    Get the current directory being used for scanning

    Returns:
        JSON: Current directory path
    """
    return jsonify({"currentDirectory": current_directory})


@app.route("/api/get-file", methods=["GET"])
def get_file():
    """
    Get the content of a specified file

    Query Parameters:
        path: The path to the file

    Returns:
        JSON: The file content
    """
    file_path = request.args.get("path")

    # Basic validation
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400

    # Security check - ensure the path is within the workspace
    workspace_root = current_directory
    abs_file_path = os.path.abspath(
        os.path.join(workspace_root, file_path.lstrip("./"))
    )

    # Check if the absolute path is within the workspace
    if not os.path.commonpath([workspace_root]) == os.path.commonpath(
        [workspace_root, abs_file_path]
    ):
        return (
            jsonify({"error": "Invalid file path - outside of allowed directory"}),
            403,
        )

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return jsonify({"content": content})

    except FileNotFoundError:
        return jsonify({"error": f"File not found: {file_path}"}), 404

    except PermissionError:
        return jsonify({"error": f"Permission denied: {file_path}"}), 403

    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
