# adventure_creator/config.py
import os
from typing import Optional
from google.cloud import secretmanager

# --- Google Cloud Secret Manager Configuration ---
# This project ID is ONLY for fetching secrets.
GCP_PROJECT_ID_FOR_SECRETS = os.environ.get("GCP_PROJECT_ID_FOR_SECRETS", "YOUR_GCP_PROJECT_ID_FOR_SECRETS")

MAPS_API_KEY_SECRET_ID = os.environ.get("MAPS_API_KEY_SECRET_ID", "YOUR_MAPS_API_KEY_SECRET_ID")
MAPS_API_KEY_SECRET_VERSION = os.environ.get("MAPS_API_KEY_SECRET_VERSION", "1")

GEMINI_API_KEY_SECRET_ID = os.environ.get("GEMINI_API_KEY_SECRET_ID", "YOUR_GEMINI_API_KEY_SECRET_ID")
GEMINI_API_KEY_SECRET_VERSION = os.environ.get("GEMINI_API_KEY_SECRET_VERSION", "1")

# --- GCS Configuration for KML Files ---
# This GCP_PROJECT_ID is for the GCS bucket. It can be the same as GCP_PROJECT_ID_FOR_SECRETS.
GCS_PROJECT_ID_FOR_BUCKET = os.environ.get("GCS_PROJECT_ID_FOR_BUCKET", "YOUR_GCS_PROJECT_ID_FOR_BUCKET")
GCS_BUCKET_NAME_FOR_KML = os.environ.get("GCS_BUCKET_NAME_FOR_KML", "YOUR_GCS_BUCKET_NAME_FOR_KML_FILES")
SIGNED_URL_EXPIRATION_SECONDS = 3600  # 1 hour

# --- Model Configuration ---
# Ensure this model name is appropriate for Google AI Studio.
# If 'gemini-2.5-flash-preview-04-17' gives issues with tool calling on Studio,
# 'gemini-1.5-flash-latest' is a more stable alternative.
MODEL_NAME = "gemini-2.5-flash-preview-04-17"
# MODEL_NAME = "gemini-1.5-flash-latest"

GOOGLE_MAPS_API_KEY: Optional[str] = None

def get_secret_from_gcp(project_id: str, secret_id: str, version_id: str = "latest") -> Optional[str]:
    if project_id == "YOUR_GCP_PROJECT_ID_FOR_SECRETS" or \
       project_id == "YOUR_GCS_PROJECT_ID_FOR_BUCKET" or \
       secret_id in ["YOUR_MAPS_API_KEY_SECRET_ID", "YOUR_GEMINI_API_KEY_SECRET_ID"]:
        print(f"Placeholder value detected for a GCP_PROJECT_ID or secret ID ('{secret_id}'). Skipping secret fetch for it.")
        return None
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    try:
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        print(f"Successfully fetched secret: {secret_id} from project {project_id}")
        return payload
    except Exception as e:
        print(f"Error fetching secret '{secret_id}' from project '{project_id}' (version: {version_id}): {e}")
        return None

def initialize_api_keys():
    global GOOGLE_MAPS_API_KEY

    # --- Ensure ADK uses Google AI Studio backend ---
    # Unset GOOGLE_GENAI_USE_VERTEXAI if it was somehow set elsewhere
    if "GOOGLE_GENAI_USE_VERTEXAI" in os.environ:
        del os.environ["GOOGLE_GENAI_USE_VERTEXAI"]
        print("Ensured ADK will attempt to use Google AI Studio backend (GOOGLE_GENAI_USE_VERTEXAI unset).")
    if "GOOGLE_CLOUD_PROJECT" in os.environ: # This might confuse the SDK if not using Vertex
        # Keep it if GCS_PROJECT_ID_FOR_BUCKET needs it for ADC with GCS client
        if os.environ["GOOGLE_CLOUD_PROJECT"] != GCS_PROJECT_ID_FOR_BUCKET:
             print(f"Note: GOOGLE_CLOUD_PROJECT is set to '{os.environ['GOOGLE_CLOUD_PROJECT']}', but GCS operations will use '{GCS_PROJECT_ID_FOR_BUCKET}'.")
        pass # Don't delete if needed for GCS ADC
    if "GOOGLE_CLOUD_LOCATION" in os.environ:
        del os.environ["GOOGLE_CLOUD_LOCATION"] # Not needed for Google AI Studio

    print("ADK configured to use Google AI Studio backend.")

    # --- Set Gemini API Key for Google AI Studio ---
    if os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY already set in environment.")
    elif GEMINI_API_KEY_SECRET_ID != "YOUR_GEMINI_API_KEY_SECRET_ID":
        print(f"Fetching Gemini API Key from Secret Manager: project='{GCP_PROJECT_ID_FOR_SECRETS}', secret='{GEMINI_API_KEY_SECRET_ID}'...")
        gemini_key = get_secret_from_gcp(GCP_PROJECT_ID_FOR_SECRETS, GEMINI_API_KEY_SECRET_ID, GEMINI_API_KEY_SECRET_VERSION)
        if gemini_key:
            os.environ["GOOGLE_API_KEY"] = gemini_key
            print("Gemini API Key (GOOGLE_API_KEY) set from Secret Manager for Google AI Studio.")
        else:
            print("Warning: Failed to fetch Gemini API Key for Google AI Studio. Model calls may fail if GOOGLE_API_KEY is not set elsewhere.")
    else:
        print("GEMINI_API_KEY_SECRET_ID is a placeholder; GOOGLE_API_KEY not set from Secret Manager.")
        print("Ensure GOOGLE_API_KEY is set in your environment for Google AI Studio backend.")

    # --- Initialize Google Maps API Key ---
    if not GOOGLE_MAPS_API_KEY:
        print(f"Fetching Google Maps API Key from Secret Manager: project='{GCP_PROJECT_ID_FOR_SECRETS}', secret='{MAPS_API_KEY_SECRET_ID}'...")
        GOOGLE_MAPS_API_KEY = get_secret_from_gcp(GCP_PROJECT_ID_FOR_SECRETS, MAPS_API_KEY_SECRET_ID, MAPS_API_KEY_SECRET_VERSION)
        if not GOOGLE_MAPS_API_KEY:
            print("Warning: Failed to fetch Google Maps API Key. Map-related tools will not function correctly.")
        else:
            print("Google Maps API Key initialized successfully.")

    if GCS_BUCKET_NAME_FOR_KML == "YOUR_GCS_BUCKET_NAME_FOR_KML_FILES" or \
       GCS_PROJECT_ID_FOR_BUCKET == "YOUR_GCS_PROJECT_ID_FOR_BUCKET":
        print("Warning: GCS_BUCKET_NAME_FOR_KML or GCS_PROJECT_ID_FOR_BUCKET not configured. KML files will use in-memory artifact service and will not generate signed URLs.")

initialize_api_keys()