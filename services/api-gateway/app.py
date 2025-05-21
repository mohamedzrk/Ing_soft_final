import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

CACHE_URL    = os.getenv('CACHE_URL',    'http://flight-cache:4004')
SEARCH_URL   = os.getenv('SEARCH_URL',   'http://search-flight:4000')
SCRAPER1_URL = os.getenv('SCRAPER1_URL', 'http://scraper-flight1:4002')
SCRAPER2_URL = os.getenv('SCRAPER2_URL', 'http://scraper-flight2:4003')

SERVICE_ENDPOINTS = [
    f"{SEARCH_URL}/flights",
    f"{SCRAPER1_URL}/flights",
    f"{SCRAPER2_URL}/flights"
]

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/113.0.0.0 Safari/537.36'
    )
}

@app.route('/flights', methods=['GET'])
def get_flights():
    origin      = request.args.get('origin')
    destination = request.args.get('destination')
    travel_date = request.args.get('travel_date')

    if not all([origin, destination, travel_date]):
        return jsonify({'error': 'Missing parameters'}), 400

    # 1) Intentar caché
    cache_resp = requests.get(
        f"{CACHE_URL}/cache",
        params={'origin': origin, 'destination': destination, 'travel_date': travel_date},
        headers=HEADERS,
        timeout=5
    )
    if cache_resp.ok and cache_resp.json():
        app.logger.info('Cache HIT')
        return jsonify(cache_resp.json())

    app.logger.info('Cache MISS')

    # 2) Llamadas concurrentes a search, scraper1 y scraper2
    flights = []
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                lambda url: requests.get(
                    url,
                    params={'origin': origin, 'destination': destination, 'travel_date': travel_date},
                    headers=HEADERS,
                    timeout=30
                ), url
            )
            for url in SERVICE_ENDPOINTS
        ]
        for fut in as_completed(futures):
            try:
                resp = fut.result()
                if resp.ok:
                    flights.extend(resp.json())
            except Exception as e:
                app.logger.error(f"Error contacting service: {e}")

    # 3) Guardar en caché
    try:
        requests.post(
            f"{CACHE_URL}/cache",
            json=flights,
            headers=HEADERS,
            timeout=5
        ).raise_for_status()
    except Exception as e:
        app.logger.warning(f"Failed to save cache: {e}")

    # 4) Ordenar por precio y responder
    flights.sort(key=lambda x: x.get('price', float('inf')))
    return jsonify(flights), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001)
