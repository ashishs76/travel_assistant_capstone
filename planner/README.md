**What tools have been used by the project?**
1. Open-Meteo (https://github.com/open-meteo/open-meteo): Open-Meteo is an open-source weather API and offers free access for non-commercial use. No API key is required.
2. Nominatim (https://github.com/osm-search/Nominatim): Nominatim (from the Latin, 'by name') is a tool to search OpenStreetMap data by name and address (geocoding). 
It's search API is used to list POIs (Point of Interests). The current project uses the API to get 'parks' in the given place.

Implementation details:
1. **config.py** contains the URL to these services
2. **weather.py** is responsible for connecting with Open-Meteo. To test the functionality, 
go to the directory above travel_assistant and executes the following command from the terminal:
     _python -m travel_assistant.tools.weather_
3. **interests.py** is responsible for connecting with Nominatim. To test the functionality, 
go to the directory above travel_assistant and executes the following command from the terminal:
     _python -m travel_assistant.tools.interests_

**NOTE:** If while testing you face timeout issues then increase the HTTP_TIMEOUT_SECONDS value in **config.py** file

**Design decisions**
1. Why wrap OpenStreetMap under MCP and not Weather data from Opne-Meteo?
MCP is used specifically for POIs as you can easily switch the provider in the backend if the need arises.