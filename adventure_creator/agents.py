# adventure_creator/agents.py
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search, ToolContext, FunctionTool
from pydantic import BaseModel, Field as PydanticField
from typing import List, Dict, Any
import json

from .config import MODEL_NAME
from .custom_tools import (
    google_maps_places_text_search_tool,
    google_maps_geocoding_tool,
    generate_kml_tool_with_signed_url # MODIFIED: Use the new tool
)

# --- State Keys for Sequential Agent ---
STATE_KEY_RAW_POIS = "temp:raw_pois_from_location_research"
STATE_KEY_POIS_WITH_COORDS = "temp:pois_with_coordinates"
STATE_KEY_FORMATTED_POIS = "temp:formatted_pois_for_kml"
STATE_KEY_KML_RESULT = "temp:kml_generation_result"

# --- Agent for Broad Query Clarification ---
class BroadQueryInput(BaseModel):
    user_query: str = PydanticField(description="The raw user query to clarify.")

broad_query_clarifier_agent = Agent(
    name="BroadQueryClarifierAgent",
    model=MODEL_NAME,
    input_schema=BroadQueryInput,
    instruction="Input: 'user_query' string. "
                "If 'user_query' is broad, use YOUR 'google_search' tool for themes/regions/POI types. "
                "Output: A single string: either the original query (if specific) or a refined query/summary "
                "clearly stating location and POI types. This string is for the next agent. "
                "Example output: 'Search for waterfalls and hiking trails in the Black Forest, Germany.'",
    description="Clarifies broad user queries using its Google Search tool and outputs a refined string query.",
    tools=[google_search],
    sub_agents=[]
)

# --- Wrapper Agents for the Sequential Orchestrator ---
class LocationResearchWrapperInput(BaseModel):
    adventure_description: str = PydanticField(description="The refined adventure description to research POIs for.")

def research_and_store_pois_for_sequential(adventure_description: str, tool_context: ToolContext):
    if not adventure_description:
        tool_context.state[STATE_KEY_RAW_POIS] = json.dumps([])
        return "Error: No adventure description provided for POI research."
    print(f"[LocationResearchWrapper-Tool] Received adventure_description: '{adventure_description}'")
    raw_pois = google_maps_places_text_search_tool.func(query=adventure_description, tool_context=tool_context)
    tool_context.state[STATE_KEY_RAW_POIS] = json.dumps(raw_pois if raw_pois else [])
    count = len(raw_pois) if isinstance(raw_pois, list) else 0
    return f"POI research complete. Found {count} POIs. Stored in state."

research_and_store_pois_tool_for_seq = FunctionTool(research_and_store_pois_for_sequential)

location_research_agent_wrapper = Agent(
    name="LocationResearchAgentWrapper",
    model=MODEL_NAME,
    input_schema=LocationResearchWrapperInput,
    instruction=f"""Your task is to initiate POI research.
    1. You will receive an 'adventure_description' as input.
    2. Call the 'research_and_store_pois_for_sequential' tool, passing this 'adventure_description' to it.
       This tool will perform the search and store the resulting list of POIs (as a JSON string) into state key: '{STATE_KEY_RAW_POIS}'.
    3. Output the confirmation message returned by the tool.""",
    tools=[research_and_store_pois_tool_for_seq],
)

async def fetch_coords_and_store_for_sequential(tool_context: ToolContext): # MODIFIED to be async
    raw_pois_json_string = tool_context.state.get(STATE_KEY_RAW_POIS)
    if not raw_pois_json_string:
        tool_context.state[STATE_KEY_POIS_WITH_COORDS] = json.dumps({"error": "No raw POIs found in state for coordinate fetching."})
        return "Error: No raw POIs found in state for coordinate fetching."
    try:
        raw_pois = json.loads(raw_pois_json_string)
        if not isinstance(raw_pois, list):
            raise json.JSONDecodeError("Raw POIs is not a list", raw_pois_json_string,0)
    except json.JSONDecodeError as e:
        print(f"Error decoding raw_pois_json_string: {e}. Content: '{raw_pois_json_string}'")
        tool_context.state[STATE_KEY_POIS_WITH_COORDS] = json.dumps({"error": f"Invalid JSON in raw POIs state: {e}"})
        return f"Error: Invalid JSON in raw POIs state for coordinate fetching: {e}"

    results_with_coords = []
    for poi in raw_pois:
        if not isinstance(poi, dict):
            results_with_coords.append({"error": "Invalid POI format, not a dictionary.", "original_poi": poi})
            continue
        if poi.get("geometry") and isinstance(poi["geometry"], dict) and poi["geometry"].get("location"):
            loc = poi["geometry"]["location"]
            if isinstance(loc, dict) and "lat" in loc and "lng" in loc:
                results_with_coords.append({**poi, "lat": loc["lat"], "lng": loc["lng"]})
                continue
        
        address = poi.get("address")
        if address and isinstance(address, str):
            # geocode_address is sync, so no await here for google_maps_geocoding_tool.func
            coords = google_maps_geocoding_tool.func(address=address, tool_context=tool_context)
            if isinstance(coords, dict) and "error" not in coords:
                results_with_coords.append({**poi, **coords})
            else:
                error_msg = coords.get("error", "Unknown geocoding error") if isinstance(coords, dict) else "Geocoding returned non-dict"
                results_with_coords.append({**poi, "error": f"Geocoding failed: {error_msg}"})
        else:
            results_with_coords.append({**poi, "error": "Missing or invalid address for geocoding"})
            
    tool_context.state[STATE_KEY_POIS_WITH_COORDS] = json.dumps(results_with_coords)
    return f"Coordinate fetching complete. Processed {len(raw_pois)} POIs. Stored in state."

fetch_coords_and_store_tool_for_seq = FunctionTool(fetch_coords_and_store_for_sequential)

poi_coordinate_fetcher_agent_wrapper = Agent(
    name="POICoordinateFetcherWrapper",
    model=MODEL_NAME,
    instruction=f"""Your task is to ensure POIs have coordinates.
    1. The previous step stored a JSON string of raw POIs in state key: '{STATE_KEY_RAW_POIS}'.
    2. Call the 'fetch_coords_and_store_for_sequential' tool. This tool will update state key: '{STATE_KEY_POIS_WITH_COORDS}'.
    3. Output the confirmation message from the tool.""",
    tools=[fetch_coords_and_store_tool_for_seq],
)

async def format_data_and_store_for_sequential(tool_context: ToolContext):
    pois_with_coords_json_string = tool_context.state.get(STATE_KEY_POIS_WITH_COORDS)
    if not pois_with_coords_json_string:
        tool_context.state[STATE_KEY_FORMATTED_POIS] = json.dumps({"error": "No POIs with coords for formatting."})
        return "Error: No POIs with coords for formatting."
    try:
        pois_with_coords = json.loads(pois_with_coords_json_string)
        if not isinstance(pois_with_coords, list):
             raise json.JSONDecodeError("POIs with coords is not a list", pois_with_coords_json_string, 0)
    except json.JSONDecodeError as e:
        print(f"Error decoding pois_with_coords_json_string: {e}. Content: '{pois_with_coords_json_string}'")
        tool_context.state[STATE_KEY_FORMATTED_POIS] = json.dumps({"error": f"Invalid JSON in POIs with coords state: {e}"})
        return f"Error: Invalid JSON in POIs with coords state for formatting: {e}"

    formatted_data = []
    for poi in pois_with_coords:
        if not isinstance(poi, dict) or "error" in poi or poi.get("lat") is None or poi.get("lng") is None:
            continue
        try:
            lat = float(poi["lat"])
            lng = float(poi["lng"])
            formatted_data.append({
                "name": poi.get("name", "Unknown POI"),
                "description": poi.get("address", "No description available"),
                "lat": lat,
                "lng": lng,
            })
        except (ValueError, TypeError) as e:
            print(f"Skipping POI due to invalid lat/lng: {poi}. Error: {e}")
            continue

    tool_context.state[STATE_KEY_FORMATTED_POIS] = json.dumps(formatted_data)
    return f"Data formatting complete. Formatted {len(formatted_data)} POIs. Stored in state."

format_data_and_store_tool_for_seq = FunctionTool(format_data_and_store_for_sequential) # FunctionTool handles async

map_data_formatter_agent_wrapper = Agent(
    name="MapDataFormatterWrapper",
    model=MODEL_NAME,
    instruction=f"""Your task is to format POI data for KML generation.
    1. The previous step stored a JSON string of POIs with coordinates in state key: '{STATE_KEY_POIS_WITH_COORDS}'.
    2. Call the 'format_data_and_store_for_sequential' tool. This tool will update state key: '{STATE_KEY_FORMATTED_POIS}'.
    3. Output the confirmation message from the tool.""",
    tools=[format_data_and_store_tool_for_seq],
)
# MODIFIED: This function is now async
async def generate_kml_and_store_result_for_sequential_gcs(tool_context: ToolContext):
    formatted_pois_json_string = tool_context.state.get(STATE_KEY_FORMATTED_POIS)
    if not formatted_pois_json_string:
        final_result = "Error: No formatted POI data found in state for KML generation."
        tool_context.state[STATE_KEY_KML_RESULT] = final_result
        return final_result
    try:
        formatted_pois = json.loads(formatted_pois_json_string)
        if not isinstance(formatted_pois, list):
            raise json.JSONDecodeError("Formatted POIs is not a list", formatted_pois_json_string, 0)
    except json.JSONDecodeError as e:
        print(f"Error decoding formatted_pois_json_string: {e}. Content: '{formatted_pois_json_string}'")
        final_result = f"Error: Invalid JSON in formatted POIs state for KML generation: {e}"
        tool_context.state[STATE_KEY_KML_RESULT] = final_result
        return final_result

    # Call the new async tool that handles GCS and signed URLs
    kml_confirmation_or_url = await generate_kml_tool_with_signed_url.func(pois=formatted_pois, tool_context=tool_context)
    tool_context.state[STATE_KEY_KML_RESULT] = kml_confirmation_or_url
    return kml_confirmation_or_url

generate_kml_and_store_result_tool_for_seq_gcs = FunctionTool(generate_kml_and_store_result_for_sequential_gcs)

kml_generator_agent_wrapper = Agent(
    name="KMLGeneratorAgentWrapper",
    model=MODEL_NAME,
    instruction=f"""Your task is to generate the KML file and provide the final confirmation or download URL.
    1. The previous step stored a JSON string of formatted POI data in state key: '{STATE_KEY_FORMATTED_POIS}'.
    2. Call the 'generate_kml_and_store_result_for_sequential_gcs' tool. This tool will:
       a. Read the formatted POIs JSON string.
       b. Generate KML, attempt to save it to Google Cloud Storage, and generate a signed URL.
       c. If GCS operations succeed, it returns a message with the signed URL.
       d. If GCS fails or is not configured, it saves to ADK artifacts and returns a message with the ADK artifact name.
       e. Store this final message (URL or artifact name) into state key: '{STATE_KEY_KML_RESULT}'.
       f. Return this same final message.
    3. Your final output MUST be the exact message returned by the tool.
    Example tool call: generate_kml_and_store_result_for_sequential_gcs()""",
    tools=[generate_kml_and_store_result_tool_for_seq_gcs], # Use the new GCS-aware tool
)

adventure_map_sequential_orchestrator = SequentialAgent(
    name="AdventureMapSequentialOrchestrator",
    description="Orchestrates KML generation, saving to GCS with signed URL if possible.",
    sub_agents=[
        location_research_agent_wrapper,
        poi_coordinate_fetcher_agent_wrapper,
        map_data_formatter_agent_wrapper,
        kml_generator_agent_wrapper, # This now uses the GCS-aware tool internally
    ]
)