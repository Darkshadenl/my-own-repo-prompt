
# Goal 3


**Goal:** Create a Svelte UI (matching the provided image) that displays a file/folder structure fetched by running a local Python script (`generate_repo_prompt.py`), allows selecting items, copies the script's output to the clipboard, and displays the content of selected files by requesting it from a local Flask server.

**Phase 1: Backend (Flask Server)**

1.  **Setup:**
    *   Create a new file `repo_prompt_server.py` in the workspace root (`/Users/quintenmeijboom/Documents/Repos/repoPrompt/`).
    *   Install required Python packages:
        ```bash
        pip install Flask Flask-Cors
        ```
2.  **Modify `generate_repo_prompt.py`:**
    *   **Action:** Ensure this script prints *only* a valid JSON string representing the directory structure to its standard output when executed. Any other print statements or errors should be removed or redirected to standard error (`stderr`) if needed for debugging.
3.  **Implement `repo_prompt_server.py`:**
    *   Import necessary modules: `Flask`, `jsonify`, `request`, `subprocess`, `os`, `Flask-Cors`.
    *   Initialize Flask app: `app = Flask(__name__)`.
    *   Enable CORS: `CORS(app)` (to allow requests from the Vite dev server).
    *   **Endpoint 1: Get File Structure**
        *   Route: `GET /api/get-structure`
        *   Logic:
            *   Define the path to `generate_repo_prompt.py`.
            *   Use `subprocess.run(['python', path_to_script], capture_output=True, text=True, check=True)` to execute the script.
            *   Use a `try...except` block around the subprocess call to catch potential execution errors (`subprocess.CalledProcessError`).
            *   If successful, return the captured `stdout` (which should be the JSON string) using `jsonify({"structure": result.stdout})`.
            *   If error, return an appropriate error response, e.g., `jsonify({"error": "Failed to generate structure", "details": str(e)}), 500`.
    *   **Endpoint 2: Get File Content**
        *   Route: `GET /api/get-file`
        *   Logic:
            *   Get the `path` query parameter: `file_path = request.args.get('path')`.
            *   **Security:** Validate `file_path`. Ensure it's not empty and ideally, check that it's a relative path within an allowed directory (e.g., the workspace root) to prevent access to arbitrary system files. Get the absolute path and verify it's within the project's intended scope. `os.path.abspath` and `os.path.commonpath` might be useful. If invalid, return a 400 or 403 error.
            *   Use a `try...except` block to handle file reading.
            *   Read file content: `with open(validated_path, 'r', encoding='utf-8') as f: content = f.read()`.
            *   If successful, return `jsonify({"content": content})`.
            *   If `FileNotFoundError`, return `jsonify({"error": "File not found"}), 404`.
            *   If other I/O error, return `jsonify({"error": "Failed to read file"}), 500`.
    *   Add standard Flask run block: `if __name__ == '__main__': app.run(debug=True)` (debug mode is fine for local development).

**Phase 2: Frontend (Svelte)**

1.  **Project Setup:**
    *   Navigate to `./repo_prompt_frontend`.
    *   Ensure dependencies are installed: `yarn install` (or `npm install`).
2.  **Clean `App.svelte`:**
    *   Remove all existing content inside `<script>`, `<main>`, and `<style>`.
    *   Import `FileExplorer` component: `import FileExplorer from './lib/FileExplorer.svelte';`.
    *   Render it: `<FileExplorer />`.
3.  **Create Components (`./repo_prompt_frontend/src/lib/`):**
    *   **`FileExplorer.svelte`:**
        *   **Script:**
            *   Import `onMount` from `svelte`.
            *   Import child components (`FolderItem`, `FileItem`, `FileViewer`).
            *   Define state variables: `fileStructure = null`, `selectedItems = new Set()`, `expandedFolders = new Set()`, `currentFileContent = null`, `currentFileName = null`, `isLoadingStructure = false`, `isLoadingFile = false`, `errorMessage = null`, `clipboardMessage = null`.
            *   `fetchStructureAsync`: Async function. Sets loading state. Fetches `http://localhost:5000/api/get-structure`. Handles errors (network, server). On success, gets JSON string (`response.text()`), copies to clipboard using `navigator.clipboard.writeText()`, sets `clipboardMessage`, parses JSON, updates `fileStructure`, clears loading/errors.
            *   `fetchFileContentAsync(filePath)`: Async function. Sets loading state. Encodes `filePath`. Fetches `http://localhost:5000/api/get-file?path=...`. Handles errors. On success, updates `currentFileContent`, `currentFileName`, clears loading/errors.
            *   Event handlers: `handleToggleSelect(itemPath, isSelected)`, `handleToggleExpand(folderPath)`, `handleSelectAll(folderData)`, `handleViewFile(filePath)`. These will update the respective `Set`s and trigger `fetchFileContentAsync`.
            *   `onMount(fetchStructureAsync)`: Load structure when component mounts.
        *   **Template:**
            *   Display loading indicator (`{#if isLoadingStructure}`).
            *   Display error message (`{#if errorMessage}`).
            *   Display clipboard message (`{#if clipboardMessage}`).
            *   Render the file tree recursively using `#each`, `FolderItem`, and `FileItem` components, passing necessary props (data, level, selected/expanded state).
            *   Render `FileViewer` passing `currentFileName` and `currentFileContent`. Add loading indicator (`isLoadingFile`).
            *   Structure into two main panes (tree view | file viewer).
    *   **`FolderItem.svelte`:**
        *   Props: `folder`, `level`, `isSelected`, `isExpanded`.
        *   Use `createEventDispatcher`.
        *   Display indentation, icon, name, expand toggle, checkbox.
        *   Dispatch `toggleExpand`, `toggleSelect` (passing path and new state), `viewFile` (if clicking name should also select/view), `selectAllChildren` events on user interaction.
        *   Conditionally render children (`{#if isExpanded}`).
    *   **`FileItem.svelte`:**
        *   Props: `file`, `level`, `isSelected`.
        *   Use `createEventDispatcher`.
        *   Display indentation, icon, name, checkbox.
        *   Dispatch `toggleSelect` and `viewFile` events on user interaction.
    *   **`FileViewer.svelte`:**
        *   Props: `fileName`, `fileContent`.
        *   Display placeholder text or the `fileContent` (likely within `<pre>` tags for formatting).
4.  **Styling (`app.css` or component styles):**
    *   Implement the two-pane layout (e.g., using CSS Grid or Flexbox).
    *   Style tree items: indentation, icons (consider simple Unicode characters or SVGs), hover effects, selected states.
    *   Style the file viewer pane.
    *   Ensure styles match the target image.

**Phase 3: Running the Application**

1.  **Terminal 1:** `cd /Users/quintenmeijboom/Documents/Repos/repoPrompt && python repo_prompt_server.py`
2.  **Terminal 2:** `cd /Users/quintenmeijboom/Documents/Repos/repoPrompt/repo_prompt_frontend && yarn dev`
3.  **Browser:** Open the URL provided by Vite (e.g., `http://localhost:5173`).

This plan provides a step-by-step guide. We'll need to implement the actual Svelte components and the Flask server based on these specifications. Let me know when you're ready to start coding!
