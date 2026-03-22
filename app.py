# FrigoNinja - Sistema de Inventario del Hogar
# Autor: Orson & Maritza
from __future__ import annotations
import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.collection import Collection

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://frigoninja:FrigoPass123@cluster0.89joi35.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("MONGO_DB", "frigoninja")
LOCAL_MONGO = os.environ.get("LOCAL_MONGO", "mongodb://localhost:27017")

client = None
col = None
consumo_col = None

app = Flask(__name__)
CORS(app)

def get_collection() -> Collection:
    global client, col
    if col is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000, socketTimeoutMS=15000)
            client.admin.command("ping")
            col = client[DB_NAME]["items"]
            print("Connected to Atlas")
        except Exception as e:
            print(f"Atlas failed: {e}")
            client = MongoClient(LOCAL_MONGO, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            col = client[DB_NAME]["items"]
            print("Using local MongoDB")
    return col

def get_consumo_collection() -> Collection:
    global client, consumo_col
    if consumo_col is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000, socketTimeoutMS=15000)
            client.admin.command("ping")
            consumo_col = client[DB_NAME]["consumo"]
        except:
            client = MongoClient(LOCAL_MONGO)
            consumo_col = client[DB_NAME]["consumo"]
    return consumo_col

@app.route("/api/health")
def health():
    try:
        count = get_collection().count_documents({})
        return {"status": "ok", "items": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

@app.route("/api/items")
def get_items():
    try:
        col = get_collection()
        categoria = request.args.get("categoria", "todos")
        query = {"categoria": categoria} if categoria != "todos" else {}
        rows = list(col.find(query, {"nombre": 1, "cantidad": 1, "unidad": 1, "categoria": 1}).sort([("cantidad", 1), ("nombre", 1)]).limit(500))
        return jsonify([{"id": str(r["_id"]), "nombre": r.get("nombre", ""), "cantidad": r.get("cantidad", 1), "unidad": r.get("unidad", "pza"), "categoria": r.get("categoria", "refri")} for r in rows])
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/items/en-cero")
def items_en_cero():
    rows = list(get_collection().find({"cantidad": {"$lte": 0}}).sort("nombre", 1))
    return jsonify([{"id": str(r["_id"]), "nombre": r.get("nombre", ""), "cantidad": r.get("cantidad", 0), "unidad": r.get("unidad", "pza"), "categoria": r.get("categoria", "refri")} for r in rows])

@app.route("/api/items", methods=["POST"])
def add_item():
    data = request.get_json(force=True)
    doc = {"nombre": data.get("nombre", "").strip(), "cantidad": data.get("cantidad", 1), "unidad": data.get("unidad", "pza"), "categoria": data.get("categoria", "refri"), "creado_en": datetime.now(timezone.utc)}
    result = get_collection().insert_one(doc)
    return {"ok": True, "id": str(result.inserted_id)}, 201

@app.route("/api/items/<item_id>/+1", methods=["POST"])
def item_plus_one(item_id):
    from bson import ObjectId
    col = get_collection()
    item = col.find_one({"_id": ObjectId(item_id)})
    if not item:
        return {"error": "No encontrado"}, 404
    col.update_one({"_id": ObjectId(item_id)}, {"$set": {"cantidad": item.get("cantidad", 0) + 1}})
    return {"ok": True}

@app.route("/api/items/<item_id>/-1", methods=["POST"])
def item_minus_one(item_id):
    from bson import ObjectId
    col = get_collection()
    item = col.find_one({"_id": ObjectId(item_id)})
    if not item:
        return {"error": "No encontrado"}, 404
    col.update_one({"_id": ObjectId(item_id)}, {"$set": {"cantidad": max(0, item.get("cantidad", 1) - 1)}})
    return {"ok": True}

@app.route("/api/items/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    from bson import ObjectId
    get_collection().delete_one({"_id": ObjectId(item_id)})
    return {"ok": True}

@app.route("/api/consumo", methods=["POST"])
def add_consumo():
    data = request.get_json(force=True)
    doc = {"fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "alimento": data.get("alimento", ""), "kcal": data.get("kcal", 0), "persona": data.get("persona", "orson"), "creado_en": datetime.now(timezone.utc)}
    get_consumo_collection().insert_one(doc)
    return {"ok": True}

@app.route("/api/consumo/hoy")
def consumo_hoy():
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = list(get_consumo_collection().find({"fecha": hoy}))
    totals = {p: {"kcal": 0} for p in ["orson", "maritza"]}
    for row in rows:
        p = row.get("persona", "orson")
        if p in totals:
            totals[p]["kcal"] += row.get("kcal", 0)
    return jsonify(totals)

@app.route("/api/kcal-info")
def kcal_info():
    def calc(p, a, ed, s):
        return (88.362 + 13.397*p + 4.799*a - 5.677*ed) if s=="h" else (447.593 + 9.247*p + 3.098*a - 4.330*ed)
    return jsonify({"orson": {"get": calc(70,167,40,"h")*1.2}, "maritza": {"get": calc(60,157,68,"m")*1.55}})

@app.route("/")
def index():
    return render_template(open("templates/index.html").read())

if __name__ == "__main__":
    app.run("0.0.0.0", port=8000, debug=True)
