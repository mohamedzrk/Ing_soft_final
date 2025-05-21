from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import OperationalError
import os
import time

app = Flask(__name__)

# Configuración de entorno
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "flight_cache")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

# Función con reintentos para conectar a PostgreSQL
def connect_to_db_with_retries(retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            print("✅ Conexión a PostgreSQL establecida.")
            return conn
        except OperationalError as e:
            print(f"❌ Intento {attempt} de {retries} fallido: {e}")
            time.sleep(delay)
    raise Exception("🚨 No se pudo conectar a PostgreSQL después de varios intentos.")

# Conectar a la base de datos
conn = connect_to_db_with_retries()
cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute("""
CREATE TABLE IF NOT EXISTS flights (
    id SERIAL PRIMARY KEY,
    origin VARCHAR(10),
    destination VARCHAR(10),
    travel_date DATE,
    airline VARCHAR(100),
    price FLOAT
);
""")
conn.commit()

# Ruta para guardar vuelos en caché
@app.route('/cache', methods=['POST'])
def save_to_cache():
    data = request.json
    print(f"Received data: {data}")  # Log para verificar los datos que llegan

    if isinstance(data, list):
        for flight in data:
            print(f"Saving flight: {flight}")
            # ✅ ADAPTAR CAMPOS SI LLEGAN COMO 'provider'
            if "airline" not in flight and "provider" in flight:
                flight["airline"] = flight["provider"]
            
            if "origin" not in flight or "destination" not in flight or "travel_date" not in flight or "airline" not in flight or "price" not in flight:
                return jsonify({"error": "Missing required fields"}), 400

            cursor.execute(
                "INSERT INTO flights (origin, destination, travel_date, airline, price) VALUES (%s, %s, %s, %s, %s)",
                (flight["origin"], flight["destination"], flight["travel_date"], flight["airline"], flight["price"])
            )
    else:
        print(f"Saving single flight: {data}")
        # ✅ ADAPTAR CAMPOS SI LLEGAN COMO 'provider'
        if "airline" not in data and "provider" in data:
            data["airline"] = data["provider"]

        if "origin" not in data or "destination" not in data or "travel_date" not in data or "airline" not in data or "price" not in data:
            return jsonify({"error": "Missing required fields"}), 400

        cursor.execute(
            "INSERT INTO flights (origin, destination, travel_date, airline, price) VALUES (%s, %s, %s, %s, %s)",
            (data["origin"], data["destination"], data["travel_date"], data["airline"], data["price"])
        )
    conn.commit()
    return jsonify({"status": "inserted"}), 201


# Ruta para obtener vuelos desde la caché
@app.route('/cache', methods=['GET'])
def get_from_cache():
    origin = request.args.get('origin')
    destination = request.args.get('destination')
    travel_date = request.args.get('travel_date')

    query = "SELECT * FROM flights WHERE 1=1"
    params = []

    if origin:
        query += " AND origin = %s"
        params.append(origin)
    if destination:
        query += " AND destination = %s"
        params.append(destination)
    if travel_date:
        query += " AND travel_date = %s"
        params.append(travel_date)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    flights = [
        {
            "id": row[0],
            "origin": row[1],
            "destination": row[2],
            "travel_date": row[3].isoformat(),
            "airline": row[4],
            "price": row[5]
        }
        for row in rows
    ]
    return jsonify(flights), 200

# Ruta para ver todos los vuelos almacenados (para pruebas)
@app.route('/all', methods=['GET'])
def get_all():
    cursor.execute("SELECT * FROM flights")
    rows = cursor.fetchall()
    flights = [
    {
        "id": row[0],
        "origin": row[1],
        "destination": row[2],
        "travel_date": row[3].isoformat(),
        "airline": row[4] if row[4] else "Unknown Airline",  # Maneja NULL o valores vacíos
        "price": row[5] if row[5] is not None else "Price Not Available"  # Maneja NULL
    }
    for row in rows
]
    return jsonify(flights), 200

# Ruta raíz opcional para verificar que el servicio está vivo
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "flight_cache with PostgreSQL running"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4004)
