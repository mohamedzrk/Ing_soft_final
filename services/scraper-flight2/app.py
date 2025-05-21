import os
import logging
import requests
import time
from flask import Flask, request, jsonify

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

# === CONFIG RapidAPI Flights Sky ===
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "flights-sky.p.rapidapi.com").strip()
BASE_URL = f"https://{RAPIDAPI_HOST}/flights/search-one-way"
INCOMPLETE_URL = f"https://{RAPIDAPI_HOST}/flights/search-incomplete"

# Polling settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "scraper2-flights-sky running"}), 200

@app.route("/flights", methods=["GET"])
def flights():
    origin = request.args.get("origin", "").upper()
    date = request.args.get("travel_date", "")

    destination = request.args.get("destination", "").upper()
    adults = request.args.get("adults", 1)
    cabinClass = request.args.get("cabinClass", "economy")
    market = request.args.get("market", "US")
    locale = request.args.get("locale", "en-US")
    currency = request.args.get("currency", "USD")

    if not (origin and date):
        return jsonify({"error": "Missing required parameters: origin and travel_date"}), 400

    params = {
        "fromEntityId": origin,
        "departDate": date,
        "adults": adults,
        "cabinClass": cabinClass,
        "market": market,
        "locale": locale,
        "currency": currency
    }
    if destination:
        params["toEntityId"] = destination

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/113.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        json_resp = resp.json() or {}
        data = json_resp.get("data") if isinstance(json_resp, dict) else {}
    except Exception as e:
        app.logger.error(f"Initial search error: {e}")
        return jsonify({"error": "Initial search failed", "details": str(e)}), 502

    context = data.get("context") if isinstance(data, dict) else {}
    session_id = context.get("sessionId")
    retries = 0

    while context.get("status") == "incomplete" and session_id and retries < MAX_RETRIES:
        retries += 1
        time.sleep(RETRY_DELAY)
        try:
            app.logger.debug(f"Polling incomplete search, attempt {retries}, sessionId={session_id}")
            inc_resp = requests.get(INCOMPLETE_URL, headers=headers, params={"sessionId": session_id}, timeout=15)
            inc_resp.raise_for_status()
            inc_json = inc_resp.json() or {}
            new_data = inc_json.get("data") if isinstance(inc_json, dict) else {}
            if isinstance(new_data, dict):
                data = new_data
                context = data.get("context", {})
                session_id = context.get("sessionId")
        except Exception as e:
            app.logger.warning(f"Polling attempt {retries} failed: {e}")
            continue

    flights = []
    if isinstance(data, dict) and data.get("itineraries"):
        for itin in data.get("itineraries", []):
            price = itin.get("price", {}).get("raw") or itin.get("price", {}).get("formatted")
            legs = itin.get("legs", [])
            origin_id = legs[0].get("origin", {}).get("displayCode") if legs else origin
            dest_id = legs[0].get("destination", {}).get("displayCode") if legs else (destination or "Everywhere")
            travel_date = legs[0].get("departure", "").split("T")[0] if legs else date
            if price:
                flights.append({
                    "provider": "flights-sky",
                    "airline": itin.get("pricingOptionId"),
                    "origin": origin_id,
                    "destination": dest_id,
                    "travel_date": travel_date,
                    "price": price
                })
    else:
        fq = data.get("flightQuotes") if isinstance(data.get("flightQuotes"), dict) else {}
        results = fq.get("results") if isinstance(fq.get("results"), list) else []
        for item in results:
            price_info = item.get("price") if isinstance(item.get("price"), dict) else {}
            price = price_info.get("value") or price_info.get("amount") or item.get("price")
            if price is None:
                continue
            flights.append({
                "provider": "flights-sky",
                "airline": item.get("carrierIds", []),
                "origin": origin,
                "destination": destination or "Everywhere",
                "travel_date": date,
                "price": price
            })

    flights.sort(key=lambda x: x.get("price", float('inf')))
    return jsonify(flights), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4003)
