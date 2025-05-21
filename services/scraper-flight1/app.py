import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# === CONFIG ===
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY",  "a9e9833266msh6e1ebe861609386p12da89jsnb0b6f6f4636b")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "google-flights4.p.rapidapi.com")
BASE_URL      = f"https://{RAPIDAPI_HOST}/flights/search-one-way"


def buscar_precio_ida(departure_id: str, arrival_id: str, departure_date: str):
    params = {
        "departureId":   departure_id,
        "arrivalId":     arrival_id,
        "departureDate": departure_date,
        "adults":        "1",
        "hl":            "en",
        "gl":            "US",
        "currency":      "USD"
    }
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    resp = requests.get(BASE_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()  # Levanta una excepción si hay un error
    return resp.json()


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/flights", methods=["GET"])
def flights_endpoint():
    origin      = request.args.get("origin")
    destination = request.args.get("destination")
    travel_date = request.args.get("travel_date")  

    if not all([origin, destination, travel_date]):
        return jsonify({"error": "Missing parameters"}), 400

    try:
        raw = buscar_precio_ida(origin, destination, travel_date)
    except requests.HTTPError as e:
        return jsonify({
            "error":   f"Upstream API error: {e}",
            "details": e.response.text
        }), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500

    # Extrae la lista
    flights = raw.get("data", {}).get("otherFlights", [])
    if not isinstance(flights, list):
        return jsonify({
            "error":    "Could not extract flights array from upstream",
            "upstream": raw
        }), 502

    # Normalización, dedupe, sort y limit
    normalized = []
    seen = set()
    for f in flights:
        price   = f.get("price")
        # extrae aerolínea
        carrier = None
        if isinstance(f.get("airline"), list) and f["airline"]:
            carrier = f["airline"][0].get("airlineName")
        carrier = carrier or f.get("airlineCode") or "Unknown"

        key = (carrier, price)
        if key in seen:
            continue
        seen.add(key)

        normalized.append({
            "provider":    "google-flights",
            "airline":     carrier,
            "origin":      origin,
            "destination": destination,
            "travel_date": travel_date,
            "price":       price
        })



    # ordena y limita a 10
    normalized.sort(key=lambda x: x["price"])
    top10 = normalized[:10]

    return jsonify(top10), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4002)
