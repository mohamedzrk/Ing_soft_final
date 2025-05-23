import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

FLIGHT_SERVICE_URL = os.getenv('FLIGHT_SERVICE_URL', 'http://flight-service:5000')

@app.route('/flights', methods=['GET'])
def get_flights():
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    travel_date = request.args.get('travel_date')

    if not all([origin, destination, travel_date]):
        return jsonify({'error': 'Missing parameters'}), 400

    # Redirigir la solicitud al nuevo servicio
    resp = requests.get(f"{FLIGHT_SERVICE_URL}/flights", params={
        'origin': origin,
        'destination': destination,
        'travel_date': travel_date
    })
    
    if resp.status_code == 200:
        return resp.json()
    return jsonify({'error': 'Failed to fetch flights'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
