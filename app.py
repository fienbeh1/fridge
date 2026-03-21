# Refrigerador - Sistema de Inventario del Hogar
# Autor: Orson & Maritza
from __future__ import annotations
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Iterable
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://frigoninja:FrigoPass123@cluster0.89joi35.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("MONGO_DB", "frigoninja")
LOCAL_MONGO = os.environ.get("LOCAL_MONGO", "mongodb://localhost:27017")

client: MongoClient[dict] | None = None
col: Collection[dict] | None = None
consumo_col: Collection[dict] | None = None

app = Flask(__name__)
CORS(app)

def get_collection() -> Collection[dict]:
    global client, col
    if col is None:
        try:
            client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=30000
            )
            client.admin.command('ping')
            col = client[DB_NAME]["items"]
        except Exception as e:
            print(f"Atlas failed ({e}), trying local...")
            client = MongoClient(LOCAL_MONGO)
            client.admin.command('ping')
            col = client[DB_NAME]["items"]
    return col

def get_consumo_collection() -> Collection[dict]:
    global client, consumo_col
    if consumo_col is None:
        try:
            client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            client.admin.command('ping')
            consumo_col = client[DB_NAME]["consumo"]
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            client = MongoClient(LOCAL_MONGO)
            consumo_col = client[DB_NAME]["consumo"]
    return consumo_col

# ============ API ENDPOINTS ============

@app.route("/api/health", methods=["GET"])
def health():
    try:
        col = get_collection()
        count = col.count_documents({})
        return {"status": "ok", "items": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

@app.route("/api/items", methods=["GET"])
def get_items():
    try:
        col = get_collection()
        categoria = request.args.get("categoria", "todos")
        
        if categoria == "todos":
            query = {}
        else:
            query = {"categoria": categoria}
        
        rows = list(col.find(query, {"nombre": 1, "cantidad": 1, "unidad": 1, "categoria": 1, "kcal": 1, "proteinas": 1, "grasas": 1, "carbohidratos": 1}).sort([("cantidad", 1), ("nombre", 1)]).limit(500))
        
        items = []
        for row in rows:
            items.append({
                "id": str(row["_id"]),
                "nombre": row.get("nombre", ""),
                "cantidad": row.get("cantidad", 1),
                "unidad": row.get("unidad", "pza"),
                "categoria": row.get("categoria", "refri"),
                "kcal": row.get("kcal", 0),
                "proteinas": row.get("proteinas", 0),
                "grasas": row.get("grasas", 0),
                "carbohidratos": row.get("carbohidratos", 0),
                "notas": row.get("notas", ""),
            })
        
        return jsonify(items)
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/items/en-cero", methods=["GET"])
def items_en_cero():
    col = get_collection()
    rows = list(col.find({"cantidad": {"$lte": 0}}).sort("nombre", 1))
    
    items = []
    for row in rows:
        items.append({
            "id": str(row["_id"]),
            "nombre": row.get("nombre", ""),
            "cantidad": row.get("cantidad", 0),
            "unidad": row.get("unidad", "pza"),
            "categoria": row.get("categoria", "refri"),
            "notas": row.get("notas", ""),
        })
    
    return jsonify(items)

@app.route("/api/items", methods=["POST"])
def add_item():
    col = get_collection()
    data = request.get_json(force=True)
    
    doc = {
        "nombre": data.get("nombre", "").strip(),
        "cantidad": data.get("cantidad", 1),
        "unidad": data.get("unidad", "pza"),
        "categoria": data.get("categoria", "refri"),
        "kcal": data.get("kcal", 0),
        "proteinas": data.get("proteinas", 0),
        "grasas": data.get("grasas", 0),
        "carbohidratos": data.get("carbohidratos", 0),
        "notas": data.get("notas", ""),
        "creado_en": datetime.now(timezone.utc),
    }
    
    result = col.insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id)}, 201

@app.route("/api/items/<item_id>", methods=["PUT"])
def update_item(item_id):
    from bson import ObjectId
    col = get_collection()
    data = request.get_json(force=True)
    
    update = {}
    for key in ["nombre", "cantidad", "unidad", "categoria", "kcal", "proteinas", "grasas", "carbohidratos", "notas"]:
        if key in data:
            update[key] = data[key]
    
    col.update_one({"_id": ObjectId(item_id)}, {"$set": update})
    return {"ok": True}

@app.route("/api/items/<item_id>/+1", methods=["POST"])
def item_plus_one(item_id):
    from bson import ObjectId
    col = get_collection()
    item = col.find_one({"_id": ObjectId(item_id)})
    if not item:
        return {"error": "No encontrado"}, 404
    
    nueva_cantidad = item.get("cantidad", 0) + 1
    col.update_one({"_id": ObjectId(item_id)}, {"$set": {"cantidad": nueva_cantidad}})
    return {"ok": True, "cantidad": nueva_cantidad}

@app.route("/api/items/<item_id>/-1", methods=["POST"])
def item_minus_one(item_id):
    from bson import ObjectId
    col = get_collection()
    item = col.find_one({"_id": ObjectId(item_id)})
    if not item:
        return {"error": "No encontrado"}, 404
    
    nueva_cantidad = max(0, item.get("cantidad", 1) - 1)
    col.update_one({"_id": ObjectId(item_id)}, {"$set": {"cantidad": nueva_cantidad}})
    return {"ok": True, "cantidad": nueva_cantidad}

@app.route("/api/items/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    from bson import ObjectId
    col = get_collection()
    col.delete_one({"_id": ObjectId(item_id)})
    return {"ok": True}

@app.route("/api/consumo", methods=["POST"])
def add_consumo():
    consumo_col = get_consumo_collection()
    data = request.get_json(force=True)
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    doc = {
        "fecha": hoy,
        "alimento": data.get("alimento", ""),
        "cantidad": data.get("cantidad", 100),
        "kcal": data.get("kcal", 0),
        "proteinas": data.get("proteinas", 0),
        "carbohidratos": data.get("carbohidratos", 0),
        "grasas": data.get("grasas", 0),
        "persona": data.get("persona", "orson"),
        "hora": data.get("hora", "comida"),
        "creado_en": datetime.now(timezone.utc),
    }
    
    consumo_col.insert_one(doc)
    return {"ok": True}

@app.route("/api/consumo/hoy", methods=["GET"])
def consumo_hoy():
    consumo_col = get_consumo_collection()
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = list(consumo_col.find({"fecha": hoy}))
    
    totals = {"orson": {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0},
              "maritza": {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}
    
    for row in rows:
        p = row.get("persona", "orson")
        if p in totals:
            totals[p]["kcal"] += row.get("kcal", 0)
            totals[p]["proteinas"] += row.get("proteinas", 0)
            totals[p]["carbohidratos"] += row.get("carbohidratos", 0)
            totals[p]["grasas"] += row.get("grasas", 0)
    
    return jsonify(totals)

@app.route("/api/kcal-info")
def kcal_info():
    def calcular_tmb(peso, altura, edad, sexo):
        if sexo == "hombre":
            return 88.362 + (13.397 * peso) + (4.799 * altura) - (5.677 * edad)
        return 447.593 + (9.247 * peso) + (3.098 * altura) - (4.330 * edad)
    
    return jsonify({
        "orson": {"tmb": calcular_tmb(70, 167, 40, "hombre"), "get": calcular_tmb(70, 167, 40, "hombre") * 1.2, "factor": 1.2},
        "maritza": {"tmb": calcular_tmb(60, 157, 68, "mujer"), "get": calcular_tmb(60, 157, 68, "mujer") * 1.55, "factor": 1.55}
    })

@app.route("/api/seed", methods=["POST"])
def seed_data():
    try:
        col = get_collection()
        col.delete_many({})
        
        ahora = datetime.now(timezone.utc)
        
        items = [
            {"nombre": "Manzana", "cantidad": 6, "unidad": "pzas", "categoria": "refri", "kcal": 52, "proteinas": 0.3, "grasas": 0.2, "carbohidratos": 14},
            {"nombre": "Plátano", "cantidad": 8, "unidad": "pzas", "categoria": "refri", "kcal": 89, "proteinas": 1.1, "grasas": 0.3, "carbohidratos": 23},
            {"nombre": "Naranja", "cantidad": 5, "unidad": "pzas", "categoria": "refri", "kcal": 47, "proteinas": 0.9, "grasas": 0.1, "carbohidratos": 12},
            {"nombre": "Aguacate", "cantidad": 2, "unidad": "pzas", "categoria": "refri", "kcal": 160, "proteinas": 2, "grasas": 15, "carbohidratos": 9},
            {"nombre": "Limón", "cantidad": 10, "unidad": "pzas", "categoria": "refri", "kcal": 29, "proteinas": 1.1, "grasas": 0.3, "carbohidratos": 9},
            {"nombre": "Uvas", "cantidad": 1, "unidad": "bandeja", "categoria": "refri", "kcal": 69, "proteinas": 0.7, "grasas": 0.2, "carbohidratos": 18},
            {"nombre": "Fresas", "cantidad": 1, "unidad": "caja", "categoria": "refri", "kcal": 32, "proteinas": 0.7, "grasas": 0.3, "carbohidratos": 8},
            {"nombre": "Lechuga", "cantidad": 1, "unidad": "cabeza", "categoria": "refri", "kcal": 15, "proteinas": 1.4, "grasas": 0.2, "carbohidratos": 3},
            {"nombre": "Jitomate", "cantidad": 5, "unidad": "pzas", "categoria": "refri", "kcal": 18, "proteinas": 0.9, "grasas": 0.2, "carbohidratos": 4},
            {"nombre": "Cebolla", "cantidad": 3, "unidad": "pzas", "categoria": "refri", "kcal": 40, "proteinas": 1.1, "grasas": 0.1, "carbohidratos": 9},
            {"nombre": "Pepino", "cantidad": 2, "unidad": "pzas", "categoria": "refri", "kcal": 15, "proteinas": 0.7, "grasas": 0.1, "carbohidratos": 3.6},
            {"nombre": "Chile", "cantidad": 4, "unidad": "pzas", "categoria": "refri", "kcal": 20, "proteinas": 1, "grasas": 0.2, "carbohidratos": 4},
            {"nombre": "Zanahoria", "cantidad": 5, "unidad": "pzas", "categoria": "refri", "kcal": 41, "proteinas": 0.9, "grasas": 0.2, "carbohidratos": 10},
            {"nombre": "Calabacita", "cantidad": 3, "unidad": "pzas", "categoria": "refri", "kcal": 17, "proteinas": 1.2, "grasas": 0.3, "carbohidratos": 3},
            {"nombre": "Brócoli", "cantidad": 1, "unidad": "manojo", "categoria": "refri", "kcal": 34, "proteinas": 2.8, "grasas": 0.4, "carbohidratos": 7},
            {"nombre": "Huevos", "cantidad": 24, "unidad": "pzas", "categoria": "refri", "kcal": 155, "proteinas": 13, "grasas": 11, "carbohidratos": 1.1},
            {"nombre": "Pollo", "cantidad": 1, "unidad": "kg", "categoria": "refri", "kcal": 165, "proteinas": 31, "grasas": 3.6, "carbohidratos": 0},
            {"nombre": "Res molida", "cantidad": 0.5, "unidad": "kg", "categoria": "refri", "kcal": 250, "proteinas": 26, "grasas": 15, "carbohidratos": 0},
            {"nombre": "Jamón", "cantidad": 0.4, "unidad": "kg", "categoria": "refri", "kcal": 145, "proteinas": 21, "grasas": 6, "carbohidratos": 1.5},
            {"nombre": "Leche", "cantidad": 2, "unidad": "L", "categoria": "refri", "kcal": 42, "proteinas": 3.4, "grasas": 1, "carbohidratos": 5},
            {"nombre": "Yogur", "cantidad": 4, "unidad": "pzas", "categoria": "refri", "kcal": 61, "proteinas": 3.5, "grasas": 3.3, "carbohidratos": 4.7},
            {"nombre": "Queso", "cantidad": 0.3, "unidad": "kg", "categoria": "refri", "kcal": 350, "proteinas": 25, "grasas": 28, "carbohidratos": 1},
            {"nombre": "Mantequilla", "cantidad": 1, "unidad": "barra", "categoria": "refri", "kcal": 717, "proteinas": 1, "grasas": 81, "carbohidratos": 0.1},
            {"nombre": "Crema", "cantidad": 1, "unidad": "litro", "categoria": "refri", "kcal": 210, "proteinas": 2.9, "grasas": 21, "carbohidratos": 3.6},
            {"nombre": "Jugo de naranja", "cantidad": 2, "unidad": "L", "categoria": "refri", "kcal": 45, "proteinas": 0.7, "grasas": 0.2, "carbohidratos": 10},
            {"nombre": "Coca-Cola", "cantidad": 2, "unidad": "L", "categoria": "refri", "kcal": 42, "proteinas": 0, "grasas": 0, "carbohidratos": 11},
            {"nombre": "Papel de baño", "cantidad": 12, "unidad": "rollos", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Servilletas", "cantidad": 2, "unidad": "paquetes", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Jabón de trastes", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Jabón líquido ropa", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Cloro", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Suavizante", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Detergente", "cantidad": 1, "unidad": "bolsa", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Bolsa basura", "cantidad": 3, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Bolsas de plástico", "cantidad": 1, "unidad": "paquete", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Esponjas", "cantidad": 3, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Trapeador", "cantidad": 1, "unidad": "pza", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Focos", "cantidad": 4, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Pilas AA", "cantidad": 8, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Pilas AAA", "cantidad": 4, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Velas", "cantidad": 6, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Limpiador multiusos", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Desinfectante", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Alcohol", "cantidad": 1, "unidad": "botella", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Algodón", "cantidad": 1, "unidad": "paquete", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Cinta adhesiva", "cantidad": 2, "unidad": "pzas", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Croquetas perro", "cantidad": 0, "unidad": "kg", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Arena gato", "cantidad": 0, "unidad": "kg", "categoria": "alacena", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Tortillas harina", "cantidad": 1, "unidad": "paquete", "categoria": "despensa", "kcal": 304, "proteinas": 8, "grasas": 8, "carbohidratos": 50},
            {"nombre": "Tortillas maíz", "cantidad": 1, "unidad": "kg", "categoria": "despensa", "kcal": 218, "proteinas": 5.7, "grasas": 2.8, "carbohidratos": 45},
            {"nombre": "Pan Bimbo", "cantidad": 1, "unidad": "paquete", "categoria": "despensa", "kcal": 260, "proteinas": 9, "grasas": 3, "carbohidratos": 48},
            {"nombre": "Galletas", "cantidad": 3, "unidad": "paquetes", "categoria": "despensa", "kcal": 440, "proteinas": 7, "grasas": 14, "carbohidratos": 70},
            {"nombre": "Arroz", "cantidad": 2, "unidad": "kg", "categoria": "despensa", "kcal": 360, "proteinas": 7, "grasas": 0.6, "carbohidratos": 79},
            {"nombre": "Frijoles", "cantidad": 1, "unidad": "kg", "categoria": "despensa", "kcal": 78, "proteinas": 5, "grasas": 0.4, "carbohidratos": 14},
            {"nombre": "Pasta", "cantidad": 5, "unidad": "paquetes", "categoria": "despensa", "kcal": 360, "proteinas": 12, "grasas": 1.5, "carbohidratos": 75},
            {"nombre": "Avena", "cantidad": 1, "unidad": "kg", "categoria": "despensa", "kcal": 389, "proteinas": 17, "grasas": 7, "carbohidratos": 66},
            {"nombre": "Harina", "cantidad": 1, "unidad": "kg", "categoria": "despensa", "kcal": 364, "proteinas": 10, "grasas": 1, "carbohidratos": 76},
            {"nombre": "Azúcar", "cantidad": 1, "unidad": "kg", "categoria": "despensa", "kcal": 387, "proteinas": 0, "grasas": 0, "carbohidratos": 100},
            {"nombre": "Sal", "cantidad": 1, "unidad": "kg", "categoria": "despensa", "kcal": 0, "proteinas": 0, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Aceite vegetal", "cantidad": 1, "unidad": "L", "categoria": "despensa", "kcal": 884, "proteinas": 0, "grasas": 100, "carbohidratos": 0},
            {"nombre": "Aceite oliva", "cantidad": 1, "unidad": "L", "categoria": "despensa", "kcal": 884, "proteinas": 0, "grasas": 100, "carbohidratos": 0},
            {"nombre": "Catsup", "cantidad": 1, "unidad": "botella", "categoria": "despensa", "kcal": 112, "proteinas": 1.7, "grasas": 0.1, "carbohidratos": 27},
            {"nombre": "Mayonesa", "cantidad": 1, "unidad": "botella", "categoria": "despensa", "kcal": 680, "proteinas": 1, "grasas": 75, "carbohidratos": 1},
            {"nombre": "Mostaza", "cantidad": 1, "unidad": "botella", "categoria": "despensa", "kcal": 66, "proteinas": 4, "grasas": 4, "carbohidratos": 5},
            {"nombre": "Salsa soy", "cantidad": 1, "unidad": "botella", "categoria": "despensa", "kcal": 60, "proteinas": 8, "grasas": 0, "carbohidratos": 6},
            {"nombre": "Salsa Valentina", "cantidad": 1, "unidad": "botella", "categoria": "despensa", "kcal": 10, "proteinas": 0, "grasas": 0, "carbohidratos": 2},
            {"nombre": "Chile seco", "cantidad": 1, "unidad": "bolsa", "categoria": "despensa", "kcal": 20, "proteinas": 1, "grasas": 0.5, "carbohidratos": 4},
            {"nombre": "Atún", "cantidad": 3, "unidad": "latas", "categoria": "despensa", "kcal": 132, "proteinas": 29, "grasas": 1, "carbohidratos": 0},
            {"nombre": "Verduras enlatadas", "cantidad": 2, "unidad": "latas", "categoria": "despensa", "kcal": 25, "proteinas": 1, "grasas": 0.2, "carbohidratos": 5},
            {"nombre": "Frijoles enlatados", "cantidad": 4, "unidad": "latas", "categoria": "despensa", "kcal": 78, "proteinas": 5, "grasas": 0.4, "carbohidratos": 14},
            {"nombre": "Elote enlatado", "cantidad": 2, "unidad": "latas", "categoria": "despensa", "kcal": 93, "proteinas": 3, "grasas": 1, "carbohidratos": 19},
            {"nombre": "Café", "cantidad": 2, "unidad": "paquetes", "categoria": "despensa", "kcal": 2, "proteinas": 0.3, "grasas": 0, "carbohidratos": 0},
            {"nombre": "Azúcar glass", "cantidad": 0, "unidad": "kg", "categoria": "despensa", "kcal": 387, "proteinas": 0, "grasas": 0, "carbohidratos": 100},
            {"nombre": "Miel", "cantidad": 0, "unidad": "botella", "categoria": "despensa", "kcal": 304, "proteinas": 0.3, "grasas": 0, "carbohidratos": 82},
            {"nombre": "Mermelada", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 250, "proteinas": 0.3, "grasas": 0.2, "carbohidratos": 65},
            {"nombre": "Leche condensada", "cantidad": 2, "unidad": "latas", "categoria": "despensa", "kcal": 321, "proteinas": 8, "grasas": 9, "carbohidratos": 54},
            {"nombre": "Leche evaporada", "cantidad": 2, "unidad": "latas", "categoria": "despensa", "kcal": 140, "proteinas": 7, "grasas": 8, "carbohidratos": 11},
            {"nombre": "Pimienta", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 251, "proteinas": 10, "grasas": 3, "carbohidratos": 64},
            {"nombre": "Comino", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 375, "proteinas": 18, "grasas": 22, "carbohidratos": 21},
            {"nombre": "Orégano", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 265, "proteinas": 9, "grasas": 4, "carbohidratos": 49},
            {"nombre": "Canela", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 247, "proteinas": 4, "grasas": 1, "carbohidratos": 81},
            {"nombre": "Ajo en polvo", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 331, "proteinas": 17, "grasas": 0.7, "carbohidratos": 73},
            {"nombre": "Chile en polvo", "cantidad": 1, "unidad": "frasco", "categoria": "despensa", "kcal": 318, "proteinas": 12, "grasas": 13, "carbohidratos": 50},
            {"nombre": "Cacahuates", "cantidad": 2, "unidad": "paquetes", "categoria": "despensa", "kcal": 567, "proteinas": 26, "grasas": 49, "carbohidratos": 16},
            {"nombre": "Palomitas", "cantidad": 3, "unidad": "bolsas", "categoria": "despensa", "kcal": 375, "proteinas": 10, "grasas": 18, "carbohidratos": 48},
            {"nombre": "Chocolate", "cantidad": 3, "unidad": "barras", "categoria": "despensa", "kcal": 546, "proteinas": 5, "grasas": 31, "carbohidratos": 59},
        ]
        
        for item in items:
            item["creado_en"] = ahora
        
        col.insert_many(items)
        return {"ok": True, "inserted": len(items)}
    except Exception as e:
        return {"error": str(e)}, 500

# ============ HTML TEMPLATE ============

TEMPLATE = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Inventario del Hogar - Orson y Maritza</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    :root {
      --refri: #3498db;
      --alacena: #9b59b6;
      --despensa: #e67e22;
      --danger: #e74c3c;
      --success: #27ae60;
      --bg: #f5f6fa;
      --card: #ffffff;
      --text: #2c3e50;
      --soft: #7f8c8d;
      --border: #dfe6e9;
    }
    
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding-bottom: 100px;
    }
    
    header {
      background: linear-gradient(135deg, var(--refri), #2980b9);
      color: white;
      padding: 1.5rem;
      text-align: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    header h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.3rem; }
    header p { font-size: 0.85rem; opacity: 0.9; }
    
    .tabs {
      display: flex;
      padding: 1rem;
      gap: 0.5rem;
      overflow-x: auto;
      background: white;
      box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .tab {
      padding: 0.7rem 1.2rem;
      border: none;
      border-radius: 2rem;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    
    .tab.refri { background: rgba(52,152,219,0.15); color: var(--refri); }
    .tab.refri.active { background: var(--refri); color: white; }
    
    .tab.alacena { background: rgba(155,89,182,0.15); color: var(--alacena); }
    .tab.alacena.active { background: var(--alacena); color: white; }
    
    .tab.despensa { background: rgba(230,126,34,0.15); color: var(--despensa); }
    .tab.despensa.active { background: var(--despensa); color: white; }
    
    .tab.cero { background: rgba(231,76,60,0.15); color: var(--danger); }
    .tab.cero.active { background: var(--danger); color: white; }
    
    .tab.calorias { background: rgba(39,174,96,0.15); color: var(--success); }
    .tab.calorias.active { background: var(--success); color: white; }
    
    main { padding: 1rem; max-width: 800px; margin: 0 auto; }
    
    .section { display: none; }
    .section.active { display: block; }
    
    .agotados {
      background: linear-gradient(135deg, #e74c3c, #c0392b);
      color: white;
      border-radius: 1rem;
      padding: 1rem;
      margin-bottom: 1rem;
      text-align: center;
    }
    
    .agotados h3 { margin-bottom: 0.5rem; }
    .agotados p { font-size: 0.9rem; opacity: 0.9; }
    
    .item-card {
      background: var(--card);
      border-radius: 0.8rem;
      padding: 1rem;
      margin-bottom: 0.7rem;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    
    .item-card.zero {
      background: rgba(231,76,60,0.08);
      border: 2px solid rgba(231,76,60,0.3);
    }
    
    .item-info { flex: 1; }
    .item-info h4 { font-size: 1rem; margin-bottom: 0.2rem; }
    .item-info span { font-size: 0.8rem; color: var(--soft); }
    
    .item-cantidad {
      font-size: 1.3rem;
      font-weight: 700;
      min-width: 50px;
      text-align: center;
    }
    
    .item-cantidad span { font-size: 0.7rem; color: var(--soft); }
    
    .btn-group { display: flex; gap: 0.4rem; }
    
    .btn {
      border: none;
      border-radius: 0.5rem;
      font-size: 1.2rem;
      width: 44px;
      height: 44px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
      font-weight: 600;
    }
    
    .btn:hover { transform: scale(1.1); }
    .btn:active { transform: scale(0.95); }
    
    .btn-minus { background: rgba(231,76,60,0.15); color: var(--danger); }
    .btn-plus { background: rgba(39,174,96,0.15); color: var(--success); }
    .btn-delete { background: rgba(0,0,0,0.1); color: var(--soft); }
    .btn-edit { background: rgba(52,152,219,0.15); color: var(--refri); }
    .btn-comer { background: var(--success); color: white; }
    
    .add-form {
      background: var(--card);
      border-radius: 1rem;
      padding: 1rem;
      margin-top: 1rem;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }
    
    .add-form h3 { margin-bottom: 1rem; color: var(--text); }
    
    .form-row {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.7rem;
      flex-wrap: wrap;
    }
    
    .form-row input, .form-row select {
      flex: 1;
      min-width: 120px;
      padding: 0.7rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      font-size: 0.9rem;
    }
    
    .btn-add {
      width: 100%;
      padding: 0.8rem;
      background: var(--success);
      color: white;
      border: none;
      border-radius: 0.5rem;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
    }
    
    /* Calorias section */
    .kcal-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    
    .kcal-card {
      background: var(--card);
      border-radius: 1rem;
      padding: 1rem;
      text-align: center;
    }
    
    .kcal-card h4 { margin-bottom: 0.5rem; }
    .kcal-card .get { font-size: 2rem; font-weight: 700; }
    .kcal-card .consumido { font-size: 1rem; color: var(--soft); }
    
    .kcal-card.orson { border-top: 4px solid var(--refri); }
    .kcal-card.maritza { border-top: 4px solid var(--alacena); }
    
    .kcal-bar {
      height: 8px;
      background: rgba(0,0,0,0.1);
      border-radius: 4px;
      margin: 0.5rem 0;
      overflow: hidden;
    }
    
    .kcal-bar-fill {
      height: 100%;
      border-radius: 4px;
      transition: width 0.3s;
    }
    
    .kcal-bar-fill.orson { background: linear-gradient(90deg, var(--refri), #3498db); }
    .kcal-bar-fill.maritza { background: linear-gradient(90deg, var(--alacena), #9b59b6); }
    
    .btn-consumir {
      background: var(--success);
      color: white;
      border: none;
      padding: 1rem;
      border-radius: 0.8rem;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      margin-bottom: 0.5rem;
    }
    
    .input-consumo {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }
    
    .input-consumo input, .input-consumo select {
      padding: 0.6rem;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      font-size: 0.9rem;
    }
    
    .empty-state {
      text-align: center;
      padding: 3rem;
      color: var(--soft);
    }
    
    .empty-state .icon { font-size: 3rem; margin-bottom: 1rem; }
  </style>
</head>
<body>
  <header>
    <h1>🏠 Inventario del Hogar</h1>
    <p>Orson y Maritza</p>
  </header>
  
  <div class="tabs">
    <button class="tab refri active" onclick="showSection('refri')">🧊 Refrigerador</button>
    <button class="tab alacena" onclick="showSection('alacena')">🧹 Alacena</button>
    <button class="tab despensa" onclick="showSection('despensa')">🥫 Despensa</button>
    <button class="tab cero" onclick="showSection('cero')">⚠️ Por Comprar <span id="contador-cero">(0)</span></button>
    <button class="tab calorias" onclick="showSection('calorias')">🔥 Calorías</button>
  </div>
  
  <main>
    <!-- REFRIGERADOR -->
    <section id="sec-refri" class="section active">
      <div id="lista-refri"></div>
      <div class="add-form">
        <h3>+ Agregar al Refrigerador</h3>
        <div class="form-row">
          <input type="text" id="add-nombre-refri" placeholder="Nombre del artículo">
          <input type="number" id="add-cantidad-refri" placeholder="Cantidad" value="1" min="0" step="0.5">
        </div>
        <div class="form-row">
          <input type="text" id="add-ud-refri" placeholder="Unidad (pzas, kg, L...)" value="pzas">
          <select id="add-categoria-refri">
            <option value="refri">Frutas/Verduras</option>
            <option value="refri-carne">Carnes/Pollos</option>
            <option value="refri-lacteo">Lácteos</option>
            <option value="refri-bebida">Bebidas</option>
          </select>
        </div>
        <button class="btn-add" onclick="agregarItem('refri')">Agregar</button>
      </div>
    </section>
    
    <!-- ALACENA -->
    <section id="sec-alacena" class="section">
      <div id="lista-alacena"></div>
      <div class="add-form">
        <h3>+ Agregar a Alacena</h3>
        <div class="form-row">
          <input type="text" id="add-nombre-alacena" placeholder="Nombre del artículo">
          <input type="number" id="add-cantidad-alacena" placeholder="Cantidad" value="1" min="0" step="1">
        </div>
        <div class="form-row">
          <input type="text" id="add-ud-alacena" placeholder="Unidad (rollos, botellas...)" value="pzas">
          <select id="add-categoria-alacena">
            <option value="alacena-limpieza">Limpieza</option>
            <option value="alacena-hogar">Hogar</option>
            <option value="alacena-mascota">Mascotas</option>
            <option value="alacena">Otro</option>
          </select>
        </div>
        <button class="btn-add" onclick="agregarItem('alacena')">Agregar</button>
      </div>
    </section>
    
    <!-- DESPENSA -->
    <section id="sec-despensa" class="section">
      <div id="lista-despensa"></div>
      <div class="add-form">
        <h3>+ Agregar a Despensa</h3>
        <div class="form-row">
          <input type="text" id="add-nombre-despensa" placeholder="Nombre del artículo">
          <input type="number" id="add-cantidad-despensa" placeholder="Cantidad" value="1" min="0" step="1">
        </div>
        <div class="form-row">
          <input type="text" id="add-ud-despensa" placeholder="Unidad (kg, paquetes, latas...)" value="pzas">
          <select id="add-categoria-despensa">
            <option value="despensa">Granos/Básicos</option>
            <option value="despensa-salsa">Salsas/Condimentos</option>
            <option value="despensa-enlatado">Enlatados</option>
            <option value="despensa-snack">Snacks</option>
          </select>
        </div>
        <button class="btn-add" onclick="agregarItem('despensa')">Agregar</button>
      </div>
    </section>
    
    <!-- POR COMPRAR -->
    <section id="sec-cero" class="section">
      <div class="agotados">
        <h3>🛒 Artículos por Comprar</h3>
        <p id="msg-cero">Cargando...</p>
      </div>
      <div id="lista-cero"></div>
    </section>
    
    <!-- CALORÍAS -->
    <section id="sec-calorias" class="section">
      <div class="kcal-grid">
        <div class="kcal-card orson">
          <h4>Orson</h4>
          <div class="get" id="get-orson">--</div>
          <div class="consumido">Consumidas: <span id="kcal-orson">0</span> kcal</div>
          <div class="kcal-bar"><div class="kcal-bar-fill orson" id="barra-orson" style="width:0%"></div></div>
        </div>
        <div class="kcal-card maritza">
          <h4>Maritza</h4>
          <div class="get" id="get-maritza">--</div>
          <div class="consumido">Consumidas: <span id="kcal-maritza">0</span> kcal</div>
          <div class="kcal-bar"><div class="kcal-bar-fill maritza" id="barra-maritza" style="width:0%"></div></div>
        </div>
      </div>
      
      <div class="add-form">
        <h3>+ Registrar Consumo</h3>
        <div class="input-consumo">
          <input type="text" id="cons-alimento" placeholder="Alimento">
          <input type="number" id="cons-kcal" placeholder="Kcal" value="100">
          <select id="cons-persona">
            <option value="orson">Orson</option>
            <option value="maritza">Maritza</option>
          </select>
        </div>
        <button class="btn-consumir" onclick="registrarConsumo()">Registrar</button>
      </div>
    </section>
  </main>
  
  <script>
    let getOrson = 1920;
    let getMaritza = 1851;
    
    async function loadData() {
      await Promise.all([
        loadItems('refri'),
        loadItems('alacena'),
        loadItems('despensa'),
        loadItemsCero(),
        loadKcalInfo()
      ]);
    }
    
    async function loadItems(tipo) {
      try {
        const res = await fetch('/api/items?categoria=' + tipo);
        const items = await res.json();
        renderItems(tipo, items);
      } catch (e) { console.error(e); }
    }
    
    async function loadItemsCero() {
      try {
        const res = await fetch('/api/items/en-cero');
        const items = await res.json();
        document.getElementById('contador-cero').textContent = '(' + items.length + ')';
        document.getElementById('msg-cero').textContent = items.length === 0 ? '¡Todo bien! No hay artículos agotados.' : 'Tienes ' + items.length + ' artículo(s) por comprar';
        renderItemsCero(items);
      } catch (e) { console.error(e); }
    }
    
    function renderItems(tipo, items) {
      const lista = document.getElementById('lista-' + tipo);
      if (!items || items.length === 0) {
        lista.innerHTML = '<div class="empty-state"><div class="icon">📦</div><p>No hay artículos</p></div>';
        return;
      }
      
      const colorMap = { refri: 'var(--refri)', alacena: 'var(--alacena)', despensa: 'var(--despensa)' };
      
      lista.innerHTML = items.map(item => {
        const isZero = item.cantidad <= 0;
        return '<div class="item-card' + (isZero ? ' zero' : '') + '">' +
          '<div class="item-info">' +
            '<h4 style="color:' + colorMap[tipo] + '">' + item.nombre + '</h4>' +
            '<span>' + item.unidad + '</span>' +
          '</div>' +
          '<div class="item-cantidad" style="color:' + (isZero ? 'var(--danger)' : 'var(--text)') + '">' +
            item.cantidad +
            '<br><span>' + item.unidad + '</span>' +
          '</div>' +
          '<div class="btn-group">' +
            '<button class="btn btn-minus" onclick="menos1(\'' + item.id + '\', \'' + tipo + '\')">−</button>' +
            '<button class="btn btn-plus" onclick="mas1(\'' + item.id + '\', \'' + tipo + '\')">+</button>' +
            '<button class="btn btn-delete" onclick="borrar(\'' + item.id + '\', \'' + tipo + '\')">🗑</button>' +
          '</div>' +
        '</div>';
      }).join('');
    }
    
    function renderItemsCero(items) {
      const lista = document.getElementById('lista-cero');
      if (!items || items.length === 0) {
        lista.innerHTML = '<div class="empty-state"><div class="icon">✅</div><p>¡Inventario completo!</p></div>';
        return;
      }
      
      lista.innerHTML = items.map(item => {
        const color = item.categoria === 'alacena' ? 'var(--alacena)' : (item.categoria === 'despensa' ? 'var(--despensa)' : 'var(--refri)');
        return '<div class="item-card zero">' +
          '<div class="item-info">' +
            '<h4 style="color:' + color + '">' + item.nombre + '</h4>' +
            '<span>' + item.unidad + '</span>' +
          '</div>' +
          '<div class="item-cantidad" style="color:var(--danger)">0</div>' +
          '<div class="btn-group">' +
            '<button class="btn btn-plus" style="background:var(--success);color:white;" onclick="comprar(\'' + item.id + '\')">✓ Comprado</button>' +
          '</div>' +
        '</div>';
      }).join('');
    }
    
    async function mas1(id, tipo) {
      await fetch('/api/items/' + id + '/+1', { method: 'POST' });
      loadItems(tipo);
      loadItemsCero();
    }
    
    async function menos1(id, tipo) {
      await fetch('/api/items/' + id + '/-1', { method: 'POST' });
      loadItems(tipo);
      loadItemsCero();
    }
    
    async function comprar(id) {
      await fetch('/api/items/' + id + '/+1', { method: 'POST' });
      loadItemsCero();
      loadItems('refri');
      loadItems('alacena');
      loadItems('despensa');
    }
    
    async function borrar(id, tipo) {
      if (!confirm('¿Borrar este artículo?')) return;
      await fetch('/api/items/' + id, { method: 'DELETE' });
      loadItems(tipo);
      loadItemsCero();
    }
    
    async function agregarItem(tipo) {
      const nombre = document.getElementById('add-nombre-' + tipo).value.trim();
      const cantidad = parseFloat(document.getElementById('add-cantidad-' + tipo).value) || 1;
      const unidad = document.getElementById('add-ud-' + tipo).value.trim() || 'pzas';
      const categoria = document.getElementById('add-categoria-' + tipo).value;
      
      if (!nombre) { alert('Escribe el nombre'); return; }
      
      await fetch('/api/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, cantidad, unidad, categoria })
      });
      
      document.getElementById('add-nombre-' + tipo).value = '';
      document.getElementById('add-cantidad-' + tipo).value = '1';
      loadItems(tipo);
      loadItemsCero();
    }
    
    async function loadKcalInfo() {
      try {
        const res = await fetch('/api/kcal-info');
        const data = await res.json();
        getOrson = Math.round(data.orson.get);
        getMaritza = Math.round(data.maritza.get);
        document.getElementById('get-orson').textContent = getOrson;
        document.getElementById('get-maritza').textContent = getMaritza;
        await loadConsumo();
      } catch (e) { console.error(e); }
    }
    
    async function loadConsumo() {
      try {
        const res = await fetch('/api/consumo/hoy');
        const data = await res.json();
        document.getElementById('kcal-orson').textContent = Math.round(data.orson.kcal);
        document.getElementById('kcal-maritza').textContent = Math.round(data.maritza.kcal);
        const pctO = Math.min(100, (data.orson.kcal / getOrson) * 100);
        const pctM = Math.min(100, (data.maritza.kcal / getMaritza) * 100);
        document.getElementById('barra-orson').style.width = pctO + '%';
        document.getElementById('barra-maritza').style.width = pctM + '%';
      } catch (e) { console.error(e); }
    }
    
    async function registrarConsumo() {
      const alimento = document.getElementById('cons-alimento').value.trim();
      const kcal = parseFloat(document.getElementById('cons-kcal').value) || 0;
      const persona = document.getElementById('cons-persona').value;
      
      if (!alimento) { alert('Escribe el alimento'); return; }
      
      await fetch('/api/consumo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alimento, kcal, persona })
      });
      
      document.getElementById('cons-alimento').value = '';
      document.getElementById('cons-kcal').value = '100';
      loadConsumo();
    }
    
    function showSection(tipo) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.getElementById('sec-' + tipo).classList.add('active');
      document.querySelector('.tab.' + tipo).classList.add('active');
    }
    
    loadData();
  </script>
</body>
</html>
'''

@app.route("/")
def index():
    return render_template_string(TEMPLATE)

if __name__ == "__main__":
    app.run("0.0.0.0", port=8000, debug=True)
