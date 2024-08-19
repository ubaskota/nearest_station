from lxml import etree, html
from geopy.distance import geodesic
import requests
import json
from bs4 import BeautifulSoup
import reverse_geocode


api_key = "AIzaSyA9d0laVd5VYvCGJgTKC1OxNAwJ0HOnb6o"


def prompt_user_input_and_validate():
	url = "https://addressvalidation.googleapis.com/v1:validateAddress?key=" + api_key
	print(url)
	isValid = False
	try:
		user_input = input("Enter the address line: ")
		user_input_state_ab = input("Enter the state's abbreviation : ")
		if validate_address(user_input) != None and isValid_state_abb(user_input_state_ab):
			# Define the payload
			stateName = convert_state_abb_to_name(user_input_state_ab)
			payload = {
				"address": {
					"regionCode": "US",
					"locality": stateName,
					"addressLines": [user_input]
				}
			}
			headers = {
				"Content-Type": "application/json"
			}
			response = requests.post(url, json=payload, headers=headers)
			print(response.status_code)
			if response.status_code == 200:
				data = response.json()
				if data["result"]["verdict"]["validationGranularity"] == "PREMISE":
					print("The address is valid.")
					isValid = True
				else:
					print("The address is invalid, so the returned result may not be accurate to your need")
					isValid = False
				# print(data["result"]["geocode"])
				return (isValid, data["result"]["geocode"]["location"]["latitude"], data["result"]["geocode"]["location"]["longitude"])
			else:
				print("Request failed with status code:", response.status_code)
		else:
			print("No input provided or invalid input.")
			return (isValid, 39.9568, -75.1822) #default to 30th street station
	except requests.exceptions.RequestException as e:
		print("An error occurred while making the request:", e)
	except Exception as e:
		print("An unexpected error occurred:", e)



def validate_address(address):
	print("****************This is the length of the address*********" + str(len(address.split(" "))))
	numWords = len(address.split(" "))
	if 1 > numWords > 10:
		return None
	sanitizedAddress = ''.join(c for c in address if c.isalnum() or c.isspace() or c in [',', '.', '-', '#'])
	return sanitizedAddress



def calculateNearestStation(isValid, currLatitude, currLongitude, allPossibleStations):
	# isValid, currLatitude, currLongitude = prompt_user_input_and_validate()
	nearestStationData = None
	minDistance = float('inf')
	# print("hello")
	for station in allPossibleStations:
		distance = geodesic((currLatitude, currLongitude), station['coordinates']).miles
		if distance < minDistance:
			minDistance = distance
			nearestStationData = station
	if not isValid:
		print("Your address couldn't be validated, so the returned result may not be accurate to your need!")
	resultInGeoJson = convertResultToGeoJson(nearestStationData)
	# print(resultInGeoJson)
	return resultInGeoJson


def convertResultToGeoJson(station):
	geojson = {
		"type": "FeatureCollection",
		"features": []
	}
	print(station)
	feature = {
		"type": "Feature",
		"geometry": {
			"type": "Point",
			"coordinates": station['coordinates']  # (latitude, longitude)
		},
		"properties": {
			"line_name": station['line_name'],
			"station_name": station['station_name'],
			"station_address": station['station_address'],
			"city": station['city'],
			"zip_code": station['zip_code']
		}
	}
	geojson["features"].append(feature)

	return geojson


def compute_driving_routes():
	isValid, curr_lat, current_long = prompt_user_input_and_validate()
	destination_date = calculateNearestStation(isValid, curr_lat, current_long)
	dest_lat = destination_date['features'][0]['geometry']['coordinates'][0]
	dest_long = destination_date['features'][0]['geometry']['coordinates'][1]

	url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
	
	# Define the payload
	payload = {
		"origin": {
			"location": {
				"latLng": {
					"latitude": curr_lat,
					"longitude": current_long
				}
			}
		},
		"destination": {
			"location": {
				"latLng": {
					"latitude": dest_lat,
					"longitude": dest_long
				}
			}
		},
		"travelMode": "WALK",
		"routingPreference": "TRAFFIC_AWARE",
		"computeAlternativeRoutes": False,
		"routeModifiers": {
			"avoidTolls": False,
			"avoidHighways": False,
			"avoidFerries": False
		},
		"languageCode": "en-US",
		"units": "IMPERIAL"
	}
	
	headers = {
		"Content-Type": "application/json",
		"X-Goog-Api-Key": api_key,
		"X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
	}
	
	try:
		response = requests.post(url, json=payload, headers=headers)
		
		if response.status_code == 200:
			data = response.json()
			print(data)
		else:
			print(f"Request failed with status code: {response.status_code}")
			print(response.text)
			
	except requests.exceptions.RequestException as e:
		print("An error occurred while making the request:", e)


def get_walking_direction_helper(curr_lat, curr_long, dest_lat, dest_long, isValid):
	origin = f"{curr_lat},{curr_long}"
	destination = f"{dest_lat},{dest_long}"

	url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&mode=walking&key={api_key}"
	walkingDirections = []
	if not isValid:
		walkingDirections.append("You provided with an invalid address, so you may not receive accurate directions to your destination")
	try:
		response = requests.get(url)
		if response.status_code == 200:
			data = response.json()
			# print(data)
			steps = data["routes"][0]["legs"][0]["steps"]
			for step in steps:
			  soup = BeautifulSoup(step["html_instructions"], 'html.parser')
			  text_directions = soup.get_text(separator=' ')
			  # print(text_directions)
			  walkingDirections.append(text_directions)
			return walkingDirections
		else:
			print("Error:", response.status_code)
	except requests.exceptions.RequestException as e:
		print("An error occurred:", e)


def isValid_state_abb(stateAb):
	stateAb = stateAb.upper()
	if len(stateAb) == 2 and stateAb in ("PA", "NJ", "DE", "DC"):
		return True
	return False


def convert_state_abb_to_name(stateAb):
	stateAb = stateAb.upper()
	ab_name_dict = {"PA": "Pennsylvania", "NJ": "New Jersey", "DE": "Delaware", "DC": "District of Columbia"}
	return ab_name_dict[stateAb]
