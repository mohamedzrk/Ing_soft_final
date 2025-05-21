# Importa Flask y requests (cliente HTTP).
from flask import Flask, request, render_template
import requests

# Crea una instancia de la aplicación Flask.
app = Flask(__name__)
GATEWAY_URL = "http://api-gateway:3001" # URL del API Gateway

# Configura la ruta para la página principal.
@app.route('/', methods=['GET']) 
def index():   #1) Leer parámetros de la URL (origin, destination, travel_date)
    origin = request.args.get('origin')  
    destination = request.args.get('destination')
    travel_date = request.args.get('travel_date')
    flights = []
    # Si se proporcionan los parámetros de origen, destino y fecha de viaje, realiza la búsqueda de vuelos.
    # 2) Si los tres existen, preguntar al gateway
    if origin and destination and travel_date: # si los valores existen
        params = {
            'origin': origin,
            'destination': destination,
            'travel_date': travel_date
        } # Parámetros para la búsqueda de vuelos
        try:
            resp = requests.get(f"{GATEWAY_URL}/flights", params=params) # Lanza una petición GET al gateway.
            resp.raise_for_status() # Lanza una excepción si la respuesta no es exitosa.
            flights = resp.json() # Convierte la respuesta JSON en un objeto Python.
        except requests.RequestException as e: # Maneja errores de conexión o respuesta no exitosa.
            app.logger.error(f"Error fetching flights: {e}")
            

    return render_template('index.html', flights=flights,
                           origin=origin, destination=destination, travel_date=travel_date)
    #Renderiza la plantilla index.html, pasando: flights: la lista de resultados. os valores de búsqueda, para que el formulario los muestre tras el envío.

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000) #Arranca la aplicación Flask en el puerto 3000, accesible desde cualquier dirección IP.