
## Prerequisites

1.  **Python 3.9+**
2.  **Node.js (v18.17 or later recommended for Next.js) and npm/yarn.** `npx` is part of npm.
3.  **Google Cloud SDK (`gcloud`)** installed and configured.
4.  **Google Cloud Project:**
    *   A Google Cloud Project with billing enabled.
    *   **Secret Manager API** enabled.
    *   **Places API** and **Geocoding API** (from Google Maps Platform) enabled.
5.  **API Keys stored in Secret Manager:**
    *   **Google Maps Platform API Key:** Store your Maps API key in Secret Manager.
    *   **Gemini API Key:** Store your Gemini API key (for ADK model calls) in Secret Manager.
6.  **Permissions:** The identity running the ADK application (e.g., your user account when running `gcloud auth application-default login`, or a service account if deployed) must have the `Secret Manager Secret Accessor` role (`roles/secretmanager.secretAccessor`) for the secrets created above.

## Setup and Configuration

1.  **Install Backend Dependencies:**
    Navigate to the main `adventure_creator` directory (this directory, where `requirements.txt` is located) and install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    It's highly recommended to use a Python virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

2.  **Install Frontend Dependencies:**
    Navigate into the `ui` directory and install Node.js dependencies:
    ```bash
    cd ui
    npm install  # or yarn install
    cd ..
    ```

3.  **Configure `config.py` or Environment Variables (for Backend):**
    Open `adventure_creator/config.py` and update the placeholder values for:
    *   `GCP_PROJECT_ID`
    *   `MAPS_API_KEY_SECRET_ID` (the name/ID you gave your Maps API key secret)
    *   `GEMINI_API_KEY_SECRET_ID` (the name/ID you gave your Gemini API key secret)

    Alternatively, set these as environment variables:
    ```bash
    export GCP_PROJECT_ID="your-gcp-project-id"
    export MAPS_API_KEY_SECRET_ID="your-maps-secret-id"
    export GEMINI_API_KEY_SECRET_ID="your-gemini-secret-id"
    ```

4.  **Authenticate Google Cloud CLI:**
    If you haven't already, authenticate your local environment:
    ```bash
    gcloud auth application-default login
    ```

## Running the Application

The application consists of two main parts: the ADK backend and the Next.js frontend. You'll need to run them separately in two different terminal windows.

**Terminal 1: Start the ADK Backend**

1.  Navigate to the parent directory of your `adventure_creator` project.
2.  Start the ADK Web UI, ensuring to allow origins for the Next.js frontend (which typically runs on port 3000):
    ```bash
    adk web adventure_creator --allow_origins http://localhost:3000
    ```
    The ADK backend will usually start on `http://localhost:8000`.

**Terminal 2: Start the Next.js Frontend**

1.  Navigate into the `ui` subdirectory within your `adventure_creator` project:
    ```bash
    cd path/to/your/adventure_creator/ui
    ```
2.  Start the Next.js development server:
    ```bash
    npm run dev  # or yarn dev
    ```
    This will typically open the Next.js application in your browser at `http://localhost:3000`.

**Using the Application:**

1.  Open your browser to `http://localhost:3000` (the Next.js frontend).
2.  Enter your adventure description.
3.  Click "Create Adventure Map".
4.  Observe the "Agent Journey" section for real-time updates.
5.  Once completed, the "Generated KML File" section will display the artifact name.
6.  To download the KML file, open the ADK Web UI (usually `http://localhost:8000`), find your session, and go to the "Artifacts" tab.

**Import KML into Google My Maps:**
*   Go to [Google My Maps](https://www.google.com/mymaps).
*   Create a new map or open an existing one.
*   Click "Import" under one of the layers.
*   Upload the downloaded KML file.

## How it Works

1.  **`config.py`:** Initializes by fetching API keys from Google Cloud Secret Manager.
2.  **`AdventureMapperAgent` (`app.py`):** The root ADK agent.
3.  Orchestrates sub-agents (`agents.py`).
4.  **`custom_tools.py`:** `FunctionTool` definitions for Maps APIs and KML.
5.  **Next.js UI (`ui/src/app/page.js`):**
    *   Makes a POST request to the ADK backend's `/run_sse` endpoint.
    *   Streams Server-Sent Events (SSE).
    *   Updates the UI dynamically.
6.  The KML artifact is saved by ADK and downloadable via the ADK Web UI.

## Troubleshooting

*   **CORS Errors:** Ensure ADK backend started with `--allow_origins http://localhost:3000`.
*   **API Key Errors (Backend Console):** Check `config.py`/env vars, Secret Manager, and API enablement.
*   **"ModuleNotFoundError" (Backend):** Run `pip install -r requirements.txt` in `adventure_creator`.
*   **Next.js App Fails to Start / Module Not Found (Frontend):** Run `npm install` (or `yarn install`) in `adventure_creator/ui`.
*   **ADK Web UI Issues**: Ensure running `adk web` from the correct directory.