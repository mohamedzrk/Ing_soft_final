import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuración de API
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")
API_URL       = f"https://{RAPIDAPI_HOST}/flights/search-one-way"

def obtener_vuelos(origen, destino, fecha):
    params = {
        "departureId":   origen,
        "arrivalId":     destino,
        "departureDate": fecha
    }
    headers = {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

@app.route("/", methods=["GET"])
def health():
    return jsonify({"estado": "ok"}), 200

@app.route("/flights", methods=["GET"])
def vuelos():
    origen  = request.args.get("origin")
    destino = request.args.get("destination")
    fecha   = request.args.get("travel_date")

    if not all([origen, destino, fecha]):
        return jsonify({"error": "Faltan parámetros: origen, destino y fecha son obligatorios"}), 400

    try:
        respuesta = obtener_vuelos(origen, destino, fecha)
    except requests.HTTPError as e:
        return jsonify({
            "error":   f"Error en la API externa: {e}",
            "detalles": e.response.text
        }), 502
    except Exception as e:
        return jsonify({"error": f"Error inesperado: {e}"}), 500

    data = respuesta.get("data", {}).get("topFlights", [])

    vuelos = []
    for v in data:
        precio = v.get("price")
        vuelos.append({
            "provider":    "google-flights",
            "origin":      origen,
            "destination": destino,
            "travel_date": fecha,
            "price":       precio
        })

    return jsonify(vuelos), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4002)
