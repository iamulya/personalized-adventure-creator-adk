# adventure_creator/custom_tools.py
import uuid
import json
from typing import Any, Dict, List, Optional
import datetime

import requests
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types as genai_types
from google.cloud import storage # For generating signed URL

from .config import (
    GOOGLE_MAPS_API_KEY,
    GCS_BUCKET_NAME_FOR_KML,
    SIGNED_URL_EXPIRATION_SECONDS,
    GCS_PROJECT_ID_FOR_BUCKET # Use this for the GCS client
)

# search_places_text and geocode_address remain the same (they are synchronous)
def search_places_text(query: str, tool_context: ToolContext) -> List[Dict[str, Any]]:
    """
    Searches for places based on a text query using Google Maps Places API (Text Search).
    For example, 'waterfalls in New England' or 'covered bridges in Vermont'.
    Returns a list of places with name, address, place_id, and geometry (lat/lng if available).
    """
    if not GOOGLE_MAPS_API_KEY:
        return [{"error": "Google Maps API Key is not configured or failed to load."}]

    api_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "key": GOOGLE_MAPS_API_KEY
    }
    print(f"[Tool Call: search_places_text] Querying Places API for: {query}")
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        simplified_results = []
        for place in results:
            poi_data = {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "place_id": place.get("place_id"),
            }
            if "geometry" in place and "location" in place["geometry"]:
                poi_data["geometry"] = {
                    "location": {
                        "lat": place["geometry"]["location"]["lat"],
                        "lng": place["geometry"]["location"]["lng"],
                    }
                }
            simplified_results.append(poi_data)
        print(f"[Tool Call: search_places_text] Found {len(simplified_results)} results.")
        return simplified_results
    except requests.exceptions.RequestException as e:
        print(f"Error calling Places API: {e}")
        return [{"error": f"Places API request failed: {str(e)}"}]
    except json.JSONDecodeError:
        print("Error decoding JSON response from Places API")
        return [{"error": "Invalid JSON response from Places API"}]

google_maps_places_text_search_tool = FunctionTool(search_places_text)


def geocode_address(address: str, tool_context: ToolContext) -> Dict[str, float]:
    """
    Geocodes an address to get its latitude and longitude using Google Maps Geocoding API.
    Returns a dictionary with 'lat' and 'lng'.
    """
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API Key is not configured or failed to load."}

    api_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY
    }
    print(f"[Tool Call: geocode_address] Geocoding address: {address}")
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            coords = {"lat": location["lat"], "lng": location["lng"]}
            print(f"[Tool Call: geocode_address] Coordinates: {coords}")
            return coords
        else:
            print(f"[Tool Call: geocode_address] Geocoding failed for {address}. Response: {data.get('status')}")
            return {"error": f"Geocoding failed for {address}. Status: {data.get('status')}"}
    except requests.exceptions.RequestException as e:
        print(f"Error calling Geocoding API: {e}")
        return {"error": f"Geocoding API request failed: {str(e)}"}
    except json.JSONDecodeError:
        print("Error decoding JSON response from Geocoding API")
        return {"error": "Invalid JSON response from Geocoding API"}

google_maps_geocoding_tool = FunctionTool(geocode_address)


# MODIFIED: Make this function async and await save_artifact
async def generate_kml_content_and_signed_url(pois: List[Dict[str, Any]], tool_context: ToolContext) -> str:
    """
    Generates KML content string from a list of Points of Interest (POIs).
    Each POI should be a dictionary with 'name', 'description', 'lat', and 'lng'.
    The generated KML string is then saved as an artifact.
    """
    kml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '  <Document>'
    ]
    print(f"[Tool Call: generate_kml_content_and_signed_url] Processing {len(pois)} POIs.")
    for poi in pois:
        name = poi.get("name", "Untitled POI")
        description_raw = poi.get("description", poi.get("address", "No description"))
        description = str(description_raw) if description_raw is not None else "No description"
        lat = poi.get("lat")
        lng = poi.get("lng")

        if lat is None or lng is None:
            print(f"Warning: Skipping POI '{name}' due to missing lat/lng for KML.")
            continue

        name = name.replace('&', '&').replace('<', '<').replace('>', '>')
        description = description.replace('&', '&').replace('<', '<').replace('>', '>')

        kml_parts.append(f"""
    <Placemark>
      <name>{name}</name>
      <description>{description}</description>
      <Point>
        <coordinates>{lng},{lat},0</coordinates>
      </Point>
    </Placemark>""")
    kml_parts.extend(['  </Document>', '</kml>'])
    kml_string = "\n".join(kml_parts)

    session_id = tool_context._invocation_context.session.id # type: ignore
    # user_id = tool_context._invocation_context.user_id # type: ignore
    # app_name = tool_context._invocation_context.app_name # type: ignore

    gcs_object_name = f"kml_files/{session_id}/adventure_map_{uuid.uuid4().hex[:8]}.kml"
    adk_artifact_filename = f"adventure_map_{uuid.uuid4().hex[:8]}.kml" # For fallback

    if GCS_BUCKET_NAME_FOR_KML != "YOUR_GCS_BUCKET_NAME_FOR_KML_FILES" and \
       GCS_PROJECT_ID_FOR_BUCKET != "YOUR_GCS_PROJECT_ID_FOR_BUCKET":
        try:
            print(f"Attempting to save KML to GCS bucket '{GCS_BUCKET_NAME_FOR_KML}' in project '{GCS_PROJECT_ID_FOR_BUCKET}' as object '{gcs_object_name}'")
            # Explicitly pass project to storage.Client if GCS_PROJECT_ID_FOR_BUCKET is set
            # Otherwise, it relies on ADC's default project.
            storage_client = storage.Client(project=GCS_PROJECT_ID_FOR_BUCKET)
            bucket = storage_client.bucket(GCS_BUCKET_NAME_FOR_KML)
            blob = bucket.blob(gcs_object_name)
            blob.upload_from_string(kml_string, content_type='application/vnd.google-earth.kml+xml')
            print(f"KML successfully uploaded to GCS: gs://{GCS_BUCKET_NAME_FOR_KML}/{gcs_object_name}")

            target_sa_email="adk-agents@genai-setup.iam.gserviceaccount.com"

            from google import auth
            principal_credentials, _ = auth.default(
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )

            from google.auth import impersonated_credentials
            impersonated_target_credentials = impersonated_credentials.Credentials(
                    source_credentials=principal_credentials,
                    target_principal=target_sa_email,
                    target_scopes=['https://www.googleapis.com/auth/devstorage.read_write'], # Or more specific GCS scopes
                    lifetime=120 # How long the impersonated credentials should be valid
                )

            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(seconds=SIGNED_URL_EXPIRATION_SECONDS),
                method="GET", 
                credentials=impersonated_target_credentials, # Pass the impersonated credentials object
            )

            print(f"Generated signed URL: {signed_url}")
            return f"KML file generated and saved to Google Cloud Storage. Download (link expires in {SIGNED_URL_EXPIRATION_SECONDS // 60} mins): {signed_url}"
        except Exception as e:
            print(f"Error during GCS KML storage or signed URL generation: {e}")
            print("Falling back to ADK in-memory artifact service.")
            await tool_context.save_artifact(adk_artifact_filename, genai_types.Part(text=kml_string))
            return f"Error saving to GCS. KML file saved to ADK artifacts as: {adk_artifact_filename}. GCS Error: {str(e)}"
    else:
        print("GCS bucket/project not configured. Saving KML to ADK in-memory artifact service.")
        await tool_context.save_artifact(adk_artifact_filename, genai_types.Part(text=kml_string))
        return f"KML file generated and saved as ADK artifact: {adk_artifact_filename}."

generate_kml_tool_with_signed_url = FunctionTool(generate_kml_content_and_signed_url)