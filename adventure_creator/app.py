# adventure_creator/app.py
from google.adk.agents import Agent
from .config import MODEL_NAME # Import MODEL_NAME, API key is initialized in config
from .agents import (
    location_research_agent,
    poi_coordinate_fetcher_agent,
    map_data_formatter_agent,
    kml_generator_agent
)

# AdventureMapperAgent (Root Agent)
adventure_mapper_agent = Agent(
    name="AdventureMapperAgent",
    model=MODEL_NAME,
    instruction=f"""You are an Adventure Map Creator. Your goal is to take a user's description of an adventure
and coordinate a team of specialized agents to produce a KML file that the user can import into Google My Maps.

Strictly follow these steps and use the specified agents:
1.  Receive the user's adventure description.
2.  Call the '{location_research_agent.name}' with the user's description. This agent will return a list of POIs, each potentially with name, address, place_id, and geometry (lat/lng).
3.  Take the list of POIs from '{location_research_agent.name}'. Call the '{poi_coordinate_fetcher_agent.name}' with this list. This agent will ensure each POI has 'lat' and 'lng' coordinates, using existing geometry if available or geocoding if not. It returns a list of POIs with name, address, lat, and lng.
4.  Take the list of POIs with coordinates from '{poi_coordinate_fetcher_agent.name}'. Call the '{map_data_formatter_agent.name}' with this list. This agent will structure the data into a list of dictionaries, each with 'name', 'description' (using address), 'lat', and 'lng'.
5.  Take the structured POI data from '{map_data_formatter_agent.name}'. Call the '{kml_generator_agent.name}' with this structured list. This agent will use a tool to generate KML and save it as an artifact, then return a confirmation message with the artifact name.
6.  Finally, present the confirmation message (including the artifact name) from '{kml_generator_agent.name}' to the user.

Example of data passed between agents (conceptual, actual data structure might vary slightly based on API responses):
- User to AdventureMapperAgent: "Weekend photography trip for waterfalls and covered bridges in New England."
- AdventureMapperAgent to LocationResearchAgent: User's description.
- LocationResearchAgent to AdventureMapperAgent: 
- AdventureMapperAgent to POICoordinateFetcherAgent: The list above.
- POICoordinateFetcherAgent to AdventureMapperAgent: 
- AdventureMapperAgent to MapDataFormatterAgent: The list above.
- MapDataFormatterAgent to AdventureMapperAgent:  (Note: description is the address)
- AdventureMapperAgent to KMLGeneratorAgent: The structured list above.
- KMLGeneratorAgent to AdventureMapperAgent: "KML file generated and saved as artifact: adventure_map_xxxx.kml"
- AdventureMapperAgent to User: "I've created your adventure map! It's saved as 'adventure_map_xxxx.kml'. You can download it from the artifacts section."

Ensure the output from one agent is correctly formatted and used as the input for the next.
Your available sub-agents (tools) are: {location_research_agent.name}, {poi_coordinate_fetcher_agent.name}, {map_data_formatter_agent.name}, and {kml_generator_agent.name}.
Do not attempt to perform the tasks of the sub-agents yourself. Delegate to them.
If a sub-agent returns an error or empty data, try to inform the user or adjust the plan if possible. For example, if no POIs are found, inform the user.
If the Google Maps API Key or Gemini API Key is not configured (check logs from config.py), inform the user that map-related or core AI features cannot be used.
""",
    description="Creates custom 'Adventure Layers' for Google Maps based on user descriptions by orchestrating sub-agents.",
    sub_agents=[
        location_research_agent,
        poi_coordinate_fetcher_agent,
        map_data_formatter_agent,
        kml_generator_agent
    ]
)

# This is the root agent for the application
root_agent = adventure_mapper_agent
