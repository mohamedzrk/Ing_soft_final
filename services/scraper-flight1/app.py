import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuración de API
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY",  "a9e9833266msh6e1ebe861609386p12da89jsnb0b6f6f4636b")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "google-flights4.p.rapidapi.com")
API_URL       = f"https://{RAPIDAPI_HOST}/flights/search-one-way"

def obtener_vuelos(origen, destino, fecha):
    params = {
        "departureId": origen,
        "arrivalId": destino,
        "departureDate": fecha,
        "adults": "1",
        "hl": "en",
        "gl": "US",
        "currency": "USD"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/flights", methods=["GET"])
def vuelos():
    origen  = request.args.get("origin")
    destino = request.args.get("destination")
    fecha   = request.args.get("travel_date")

    if not all([origen, destino, fecha]):
        return jsonify({"error": "Missing parameters"}), 400

    try:
        respuesta = obtener_vuelos(origen, destino, fecha)
    except requests.HTTPError as e:
        return jsonify({
            "error": f"Upstream API error: {e}",
            "details": e.response.text
        }), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500

    data = respuesta.get("data", {}).get("otherFlights", [])
    if not isinstance(data, list):
        return jsonify({
            "error": "Could not extract flights array from upstream",
            "upstream": respuesta
        }), 502

    vuelos = []
    vistos = set()
    for v in data:
        precio = v.get("price")
        aerol = v.get("airline") or []
        aerol = aerol[0].get("airlineName") if aerol else v.get("airlineCode", "Unknown")

        clave = (aerol, precio)
        if clave in vistos:
            continue
        vistos.add(clave)

        vuelos.append({
            "provider": "google-flights",
            "airline": aerol,
            "origin": origen,
            "destination": destino,
            "travel_date": fecha,
            "price": precio
        })

    vuelos.sort(key=lambda x: x["price"])
    return jsonify(vuelos[:10]), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4002)
