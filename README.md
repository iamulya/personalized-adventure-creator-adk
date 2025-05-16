# Adventure Creator

This project uses the Google Agent Development Kit (ADK) to create a personalized "Adventure Layer" for Google Maps.
Users describe an adventure, and a series of agents work together to research locations, find Points of Interest (POIs),
fetch their coordinates, and finally generate a KML file that can be imported into Google My Maps.

## Features

-   **User-driven adventure planning:** Takes natural language descriptions.
-   **Multi-agent orchestration:** Uses specialized agents for research, geocoding, data formatting, and KML generation.
-   **Google Maps Integration:** Leverages Google Search and Google Maps Platform APIs (Places, Geocoding).
-   **KML Output:** Generates a KML file compatible with Google My Maps.
-   **Secure API Key Management:** API keys (for Google Maps and Gemini) are fetched from Google Cloud Secret Manager.
-   **Artifact Service:** The final KML file is delivered via ADK's ArtifactService.

## Project Structure

```
adventure_creator/
├── __init__.py        # Makes the root_agent available for ADK
├── config.py          # Handles API key configuration and secret fetching
├── custom_tools.py    # Defines FunctionTools for Maps API calls and KML generation
├── agents.py          # Defines the specialized sub-agents
└── app.py             # Defines the main orchestrator (root) agent
```

## Prerequisites

1.  **Python 3.9+**
2.  **Google Cloud SDK (`gcloud`)** installed and configured.
3.  **Google Cloud Project:**
    *   A Google Cloud Project with billing enabled.
    *   **Secret Manager API** enabled.
    *   **Places API** and **Geocoding API** (from Google Maps Platform) enabled.
4.  **API Keys stored in Secret Manager:**
    *   **Google Maps Platform API Key:** Store your Maps API key in Secret Manager.
    *   **Gemini API Key:** Store your Gemini API key (for ADK model calls) in Secret Manager.
5.  **Permissions:** The identity running the ADK application (e.g., your user account when running `gcloud auth application-default login`, or a service account if deployed) must have the `Secret Manager Secret Accessor` role (`roles/secretmanager.secretAccessor`) for the secrets created above.

## Setup and Configuration

1.  **Create Project Files:**
    You can manually create the files as described in the "Project Structure" section and copy the Python code into them.

2.  **Install Dependencies:**
    ```bash
    pip install google-adk google-cloud-secret-manager requests
    ```

3.  **Configure `config.py` or Environment Variables:**
    Open `adventure_creator/config.py` and update the placeholder values for:
    *   `GCP_PROJECT_ID`
    *   `MAPS_API_KEY_SECRET_ID` (the name/ID you gave your Maps API key secret)
    *   `GEMINI_API_KEY_SECRET_ID` (the name/ID you gave your Gemini API key secret)

    Alternatively, you can set these as environment variables before running the application:
    ```bash
    export GCP_PROJECT_ID="your-gcp-project-id"
    export MAPS_API_KEY_SECRET_ID="your-maps-secret-id"
    export GEMINI_API_KEY_SECRET_ID="your-gemini-secret-id"
    # Optional:
    # export MAPS_API_KEY_SECRET_VERSION="your-maps-secret-version" (defaults to "latest")
    # export GEMINI_API_KEY_SECRET_VERSION="your-gemini-secret-version" (defaults to "latest")
    ```

4.  **Authenticate Google Cloud CLI:**
    If you haven't already, authenticate your local environment to Google Cloud:
    ```bash
    gcloud auth application-default login
    ```
    This allows the Python client libraries to find your credentials.

## Running the Application

1.  **Navigate to the parent directory** of your `adventure_creator` project.
    For example, if your project is at `/path/to/projects/adventure_creator`, navigate to `/path/to/projects`.

2.  **Start the ADK Web UI:**
    ```bash
    adk web adventure_creator
    ```
    Or, if you are in the current directory where `adventure_creator` folder is located:
    ```bash
    adk web .
    ```


3.  **Open your browser** to `http://localhost:8000` (or the port indicated by the ADK CLI).

4.  **Select the `adventure_creator` app** from the dropdown menu in the ADK Web UI.

5.  **Enter your adventure description** in the input field, for example:
    *   "A weekend photography trip focusing on waterfalls and covered bridges in New England."
    *   "A culinary tour of famous pizzerias in New York City."
    *   "Historical landmarks and museums in Washington D.C."

6.  The agents will process your request. You should see log messages in the console where you ran `adk web`.

7.  Once completed, the root agent will inform you that a KML file has been generated and saved as an artifact. You can download this KML file from the "Artifacts" section of the ADK Web UI for the current session.

8.  **Import KML into Google My Maps:**
    *   Go to [Google My Maps](https://www.google.com/mymaps).
    *   Create a new map or open an existing one.
    *   Click "Import" under one of the layers (or create a new layer first).
    *   Upload the downloaded KML file.

## How it Works

1.  **`config.py`:** Initializes by fetching API keys from Google Cloud Secret Manager.
2.  **`AdventureMapperAgent` (`app.py`):** This is the root agent. It receives the user's query.
3.  It orchestrates the following sub-agents (`agents.py`) in sequence:
    *   **`LocationResearchAgent`**: Uses Google Search and the `search_places_text` tool (Google Maps Places API) to find relevant POIs.
    *   **`POICoordinateFetcherAgent`**: Takes the POIs and ensures each has latitude/longitude, using existing geometry or the `geocode_address` tool (Google Maps Geocoding API).
    *   **`MapDataFormatterAgent`**: Cleans and structures the POI data into a consistent list of dictionaries.
    *   **`KMLGeneratorAgent`**: Uses the `generate_kml_content` tool to create the KML string from the structured POIs.
4.  **`custom_tools.py`:**
    *   `search_places_text`: Makes an HTTP GET request to the Google Maps Places API.
    *   `geocode_address`: Makes an HTTP GET request to the Google Maps Geocoding API.
    *   `generate_kml_content`: Formats the POI data into a KML string and uses the `tool_context.save_artifact()` method to make it available for download.
5.  The final KML artifact name is reported back to the user.

## Troubleshooting

*   **API Key Errors:**
    *   Double-check that `GCP_PROJECT_ID`, `MAPS_API_KEY_SECRET_ID`, and `GEMINI_API_KEY_SECRET_ID` are correctly set (either in `config.py` or as environment variables).
    *   Verify the secret names and versions in Google Cloud Secret Manager.
    *   Ensure the identity running the script has `Secret Manager Secret Accessor` permissions.
    *   Make sure the Google Maps Platform APIs (Places, Geocoding) are enabled for your Maps API key in the Google Cloud Console.
    *   Check for billing issues on your Google Cloud project.
*   **"ModuleNotFoundError"**: Ensure you've run `pip install google-adk google-cloud-secret-manager requests`.
*   **ADK Web UI Issues**: Make sure you are running `adk web` from the correct directory (the parent of `adventure_creator`).

