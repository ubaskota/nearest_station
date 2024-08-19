from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache
import reverse_geocode
from lxml import etree, html
import json

from implementation import prompt_user_input_and_validate, calculateNearestStation, get_walking_direction_helper

#pip install -r requirements.txt
#python -m flask --app ./app.py run

app = Flask(__name__)

api_key = "AIzaSyA9d0laVd5VYvCGJgTKC1OxNAwJ0HOnb6o"
cache = TTLCache(maxsize=100, ttl=3600)  # 1-hour TTL
station_data = []
station_data_dc = []


@app.route('/')
def home():
	return "Hello, test test test!"


@app.route('/get-walking-directions', methods=['GET'])
def get_walking_direction_to_nearest_station():
	global station_data
	isValid, curr_lat, curr_long = prompt_user_input_and_validate()
	coordinates = (curr_lat, curr_long)
	if not isInValidState(coordinates):
		return ["The address you provided falls outside of one of the three valid states(PA, NJ and DE).\n"
		"You can catch trains for many locations from 30th Street station in Philadelphia or Washington - Union Station"]
	if (curr_lat, curr_long) in cache:
		print("Found in cache!")
		return cache[(curr_lat, curr_long)]
	if not checkIfDC(coordinates) and not station_data:
		allPossibleStations = parse_kml('static/doc.kml')

	if checkIfDC(coordinates) and not station_data_dc:
		allPossibleStations = parse_json_dc('static/Metro_Stations_Regional.geojson')
	destination_data = calculateNearestStation(isValid, curr_lat, curr_long, allPossibleStations)
	dest_lat = destination_data['features'][0]['geometry']['coordinates'][0]
	dest_long = destination_data['features'][0]['geometry']['coordinates'][1]
	finalPath = get_walking_direction_helper(curr_lat, curr_long, dest_lat, dest_long, isValid)
	cache[(curr_lat, curr_long)] = finalPath
	return finalPath



def parse_json_dc(file_path):
	global station_data_dc
	with open(file_path, 'r') as file:
		data = json.load(file)  # Use json.load() for file objects
		features = data['features']
		for feature in features:
			properties = feature['properties']
			geometry = feature['geometry']
			
			station = {
				'line_name': properties.get('LINE', ''),
				'station_name': properties.get('NAME', ''),
				'station_address': properties.get('ADDRESS', ''),
				'city': properties.get('ADDRESS', '').split(',')[1].strip() if properties.get('ADDRESS') else '',
				'zip_code': properties.get('ADDRESS', '').split(',')[-1].strip() if properties.get('ADDRESS') else '',
				'coordinates': (geometry['coordinates'][1], geometry['coordinates'][0])  # (latitude, longitude)
			}
			
			station_data_dc.append(station)
	return station_data_dc


def parse_kml(file_path):
	# Parse the KML file and extract station data
	global station_data
	tree = etree.parse(file_path)
	root = tree.getroot()
	namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
	for placemark in root.xpath('.//kml:Placemark', namespaces=namespace):
		line_name = placemark.xpath('.//kml:name', namespaces=namespace)
		# print(line_name)
		coordinates = placemark.xpath('.//kml:coordinates', namespaces=namespace)[0].text.strip().split(',')
		description_html = placemark.xpath('.//kml:description', namespaces=namespace)[0].text.strip()
		html_tree = html.fromstring(description_html)
		station_address = html_tree.xpath('//td[text()="Street_Add"]/following-sibling::td/text()')
		zip_code = html_tree.xpath('//td[text()="Zip"]/following-sibling::td/text()')
		station_city = html_tree.xpath('//td[text()="City"]/following-sibling::td/text()')
		station_name = html_tree.xpath('//td[text()="Station_Na"]/following-sibling::td/text()')
		# print(station_address)
		# print(zip_code)
		if station_address and len(coordinates) >= 2:
			station = station_address[0]
			longitude = float(coordinates[0])
			latitude = float(coordinates[1])
			station_data.append({
				'line_name': line_name[0].text,
				'station_name': station_name[0],
				'station_address': station,
				'city': station_city[0],
				'zip_code': zip_code[0],
				'coordinates': (latitude, longitude)
			})

	return station_data


def isInValidState(coordinates): #checks if the coordinates fall in one of PA, NJ or DE
	valid_states = ["Pennsylvania", "New Jersey", "Delaware", "Washington, D.C."]
	geocode_data = reverse_geocode.get(coordinates)
	print(geocode_data["state"])
	if geocode_data["state"] in valid_states:
		return True
	return False


def checkIfDC(coordinates):
	geocode_data = reverse_geocode.get(coordinates)
	if geocode_data["state"] == "Washington, D.C.":
		return True
	return False


if __name__ == '__main__':
	app.run(host='0.0.0.0')
