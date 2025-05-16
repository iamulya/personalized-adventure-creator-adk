# adventure_creator/custom_tools.py
import uuid
import json
from typing import Any, Dict, List, Optional

import requests
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types as genai_types

from .config import GOOGLE_MAPS_API_KEY


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
async def generate_kml_content(pois: List[Dict[str, Any]], tool_context: ToolContext) -> str:
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
    print(f"[Tool Call: generate_kml_content] Processing {len(pois)} POIs for KML generation.")
    for poi in pois:
        name = poi.get("name", "Untitled POI")
        description_raw = poi.get("description", poi.get("address", "No description"))
        description = str(description_raw) if description_raw is not None else "No description"
        lat = poi.get("lat")
        lng = poi.get("lng")

        if lat is None or lng is None:
            print(f"Warning: Skipping POI '{name}' due to missing lat/lng.")
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

    artifact_name = f"adventure_map_{uuid.uuid4().hex[:8]}.kml"
    try:
        # AWAIT THE ASYNC CALL
        await tool_context.save_artifact(artifact_name, genai_types.Part(text=kml_string))
        print(f"[Tool Call: generate_kml_content] Saved KML to artifact: {artifact_name}")
        return f"KML file generated and saved as artifact: {artifact_name}"
    except Exception as e:
        print(f"Error saving artifact {artifact_name}: {e}")
        return f"Error saving KML artifact: {str(e)}"

generate_kml_tool = FunctionTool(generate_kml_content) # FunctionTool handles async funcs