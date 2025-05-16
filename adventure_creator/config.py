# adventure_creator/config.py
import os
from typing import Optional
from google.cloud import secretmanager

# --- Google Cloud Secret Manager Configuration ---
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "YOUR_GCP_PROJECT_ID")

# Google Maps API Key Secret
MAPS_API_KEY_SECRET_ID = os.environ.get("MAPS_API_KEY_SECRET_ID", "YOUR_MAPS_API_KEY_SECRET_ID")
MAPS_API_KEY_SECRET_VERSION = os.environ.get("MAPS_API_KEY_SECRET_VERSION", "latest")

# Gemini API Key Secret (for ADK's model calls)
GEMINI_API_KEY_SECRET_ID = os.environ.get("GEMINI_API_KEY_SECRET_ID", "YOUR_GEMINI_API_KEY_SECRET_ID")
GEMINI_API_KEY_SECRET_VERSION = os.environ.get("GEMINI_API_KEY_SECRET_VERSION", "latest")


# Define the model to be used by agents
MODEL_NAME = "gemini-1.5-flash-latest" # Or "gemini-2.5-flash-preview-04-17" if available and preferred

# Global variables to store fetched API keys
GOOGLE_MAPS_API_KEY: Optional[str] = None
# Note: GEMINI_API_KEY will be set as an environment variable GOOGLE_API_KEY

def get_secret_from_gcp(project_id: str, secret_id: str, version_id: str = "latest") -> Optional[str]:
    """Fetches a secret from Google Cloud Secret Manager."""
    if project_id == "YOUR_GCP_PROJECT_ID" or secret_id == "YOUR_MAPS_API_KEY_SECRET_ID" or secret_id == "YOUR_GEMINI_API_KEY_SECRET_ID":
        print(f"Placeholder value detected for GCP_PROJECT_ID or secret ID ('{secret_id}'). Skipping secret fetch.")
        return None

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    try:
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        print(f"Successfully fetched secret: {secret_id}")
        return payload
    except Exception as e:
        print(f"Error fetching secret '{secret_id}' from project '{project_id}' (version: {version_id}): {e}")
        print("Please ensure:")
        print(f"1. The secret '{secret_id}' exists in project '{project_id}'.")
        print(f"2. The version '{version_id}' of the secret exists.")
        print("3. The Application Default Credentials have permission to access this secret (roles/secretmanager.secretAccessor).")
        print("   You might need to run: `gcloud auth application-default login`")
        return None

def initialize_maps_api_key():
    """Initializes the Google Maps API key by fetching it from Secret Manager."""
    global GOOGLE_MAPS_API_KEY
    if GOOGLE_MAPS_API_KEY: # Already initialized
        return

    print(f"Attempting to fetch Google Maps API Key from Secret Manager: project='{GCP_PROJECT_ID}', secret='{MAPS_API_KEY_SECRET_ID}'...")
    GOOGLE_MAPS_API_KEY = get_secret_from_gcp(GCP_PROJECT_ID, MAPS_API_KEY_SECRET_ID, MAPS_API_KEY_SECRET_VERSION)

    if not GOOGLE_MAPS_API_KEY:
        print("Warning: Failed to fetch Google Maps API Key. Map-related tools will not function correctly.")
    else:
        print("Google Maps API Key initialized successfully.")

def initialize_gemini_api_key():
    """Initializes the Gemini API key and sets it as an environment variable."""
    if os.getenv("GOOGLE_API_KEY"): # Already set, perhaps by user
        print("GOOGLE_API_KEY environment variable already set. Using existing value.")
        return

    print(f"Attempting to fetch Gemini API Key from Secret Manager: project='{GCP_PROJECT_ID}', secret='{GEMINI_API_KEY_SECRET_ID}'...")
    gemini_key = get_secret_from_gcp(GCP_PROJECT_ID, GEMINI_API_KEY_SECRET_ID, GEMINI_API_KEY_SECRET_VERSION)

    if gemini_key:
        os.environ["GOOGLE_API_KEY"] = gemini_key
        print("Gemini API Key (GOOGLE_API_KEY) initialized successfully from Secret Manager and set as environment variable.")
    else:
        print("Warning: Failed to fetch Gemini API Key. ADK model calls might fail.")
        print("Ensure GOOGLE_API_KEY is set in your environment if not using Secret Manager for it.")


# Initialize keys when this module is imported
# Gemini key should be initialized first so ADK picks it up.
initialize_gemini_api_key()
initialize_maps_api_key()

