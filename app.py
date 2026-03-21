from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from typing import Iterable

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("MONGO_DB", "refrigerador")

client: MongoClient[dict] | None = None
col: Collection[dict] | None = None

app = Flask(__name__)
CORS(app)


def get_collection() -> Collection[dict]:
    global client, col
    if col is None:
        client = MongoClient(MONGO_URI)
        col = client[DB_NAME]["items"]
    return col


def get_consumo_collection() -> Collection[dict]:
    global client, consumo_col
    if consumo_col is None:
        client = MongoClient(MONGO_URI)
        consumo_col = client[DB_NAME]["consumo"]
    return consumo_col


consumo_col: Collection[dict] | None = None


TEMPLATE = """<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Refrigerador - Orson y Maritza</title>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Playfair+Display:wght@600&display=swap');

      :root {
        --bg: radial-gradient(circle at top, #fdf3c9, #f1c27d 40%, #d86e5c 80%);
        --card: rgba(255, 255, 255, 0.92);
        --accent: #2f5d62;
        --accent-dark: #1b2a2f;
        --soft: #415a5f;
        --urgent: #c0392b;
        --frozen: #3498db;
        --orson: #2980b9;
        --maritza: #8e44ad;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: 'Space Grotesk', system-ui, sans-serif;
        background: var(--bg);
        color: #1b1b1b;
      }

      main { max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }

      h1 { font-family: 'Playfair Display', serif; font-size: clamp(1.8rem, 4vw, 2.5rem); margin: 0 0 0.3rem; }
      h2 { margin: 0 0 0.5rem; font-size: 1.05rem; color: var(--accent-dark); }
      h3 { margin: 0.6rem 0 0.3rem; font-size: 0.85rem; color: var(--soft); text-transform: uppercase; letter-spacing: 0.06em; }
      p.lede { margin: 0 0 1.2rem; color: rgba(0,0,0,0.6); font-size: 0.95rem; }

      .panel {
        background: var(--card);
        border-radius: 1.25rem;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 20px 50px rgba(35,45,52,0.15);
      }

      .kcal-bar { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
      .kcal-card { padding: 1rem; border-radius: 0.8rem; text-align: center; }
      .kcal-orson { background: rgba(41,128,185,0.12); border: 2px solid var(--orson); }
      .kcal-maritza { background: rgba(142,68,173,0.12); border: 2px solid var(--maritza); }
      .kcal-card .label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--soft); font-weight: 600; }
      .kcal-card .name { font-size: 1.4rem; font-weight: 700; }
      .kcal-card .value { font-size: 2rem; font-weight: 700; margin: 0.3rem 0; }
      .kcal-card .detail { font-size: 0.7rem; color: var(--soft); }

      .nutri-summary {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem;
        background: rgba(0,0,0,0.04); padding: 0.8rem; border-radius: 0.8rem; font-size: 0.8rem;
      }
      .nutri-item { text-align: center; }
      .nutri-item .val { font-weight: 700; font-size: 1.1rem; }
      .nutri-item .lbl { color: var(--soft); font-size: 0.65rem; text-transform: uppercase; }

      label { display: block; text-transform: uppercase; letter-spacing: 0.05em; color: var(--soft); font-size: 0.55rem; margin-bottom: 0.15rem; }
      input, select { width: 100%; padding: 0.6rem 0.7rem; border-radius: 0.6rem; border: 1px solid rgba(0,0,0,0.12); font-size: 0.9rem; font-family: inherit; margin-bottom: 0.5rem; }
      .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.5rem; }

      .quick-add h3 { font-size: 0.7rem; margin-top: 0.8rem; }
      .btn-grid { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.5rem; }

      .quick-btn {
        display: inline-flex; align-items: center; gap: 0.3rem;
        padding: 0.6rem 1rem; border-radius: 2rem;
        border: 1px solid rgba(0,0,0,0.15); background: rgba(255,255,255,0.8);
        font-size: 0.85rem; cursor: pointer; transition: all 0.2s;
      }
      .quick-btn:hover { background: var(--accent); color: white; border-color: var(--accent); }
      .quick-btn img { width: 20px; height: 20px; object-fit: contain; border-radius: 4px; }

      .qty-control { display: inline-flex; align-items: center; gap: 0.3rem; }
      .qty-btn { width: 28px; height: 28px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.2); background: white; font-size: 1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; }
      .qty-btn:hover { background: var(--accent); color: white; }
      .qty-val { min-width: 24px; text-align: center; font-weight: 600; }

      .btn { margin-top: 0.5rem; border: none; border-radius: 0.7rem; padding: 0.7rem 1.2rem; font-weight: 600; font-size: 0.9rem; cursor: pointer; color: white; background: linear-gradient(135deg, #1b2f3f, #3d8b9c); transition: transform 0.2s; }
      .btn:active { transform: translateY(1px); }
      .btn-danger { background: linear-gradient(135deg, #c0392b, #e74c3c); }

      .section-tabs { display: flex; gap: 0.4rem; margin-bottom: 1rem; flex-wrap: wrap; }
      .tab { padding: 0.4rem 0.8rem; border-radius: 2rem; border: none; cursor: pointer; font-size: 0.8rem; background: rgba(0,0,0,0.06); transition: all 0.2s; }
      .tab.active { background: var(--accent); color: white; }
      .tab.frozen.active { background: var(--frozen); }

      .table-wrapper { margin-top: 0.8rem; border-radius: 0.8rem; overflow: hidden; border: 1px solid rgba(0,0,0,0.08); }
      table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
      th, td { padding: 0.5rem 0.6rem; text-align: left; }
      th { background: rgba(255,255,255,0.8); font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--soft); }
      tr:nth-child(even) { background: rgba(250,250,250,0.5); }

      .urgency { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 1rem; font-size: 0.65rem; font-weight: 600; }
      .urgency.soon { background: #ffebee; color: var(--urgent); }
      .urgency.frozen { background: #e3f2fd; color: var(--frozen); }
      .urgency.ok { background: #e8f5e9; color: #27ae60; }

      .nutri-tag { font-size: 0.7rem; color: var(--soft); background: rgba(0,0,0,0.04); padding: 0.2rem 0.4rem; border-radius: 0.3rem; }
      .delete-btn { background: #e74c3c; color: white; border: none; border-radius: 0.3rem; padding: 0.25rem 0.5rem; cursor: pointer; font-size: 0.7rem; }

      .ideas-section { margin-top: 1rem; }
      .idea-card { border-radius: 0.9rem; background: rgba(255,255,255,0.85); padding: 1rem 1.2rem; margin-bottom: 0.8rem; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08); }
      .idea-card h4 { margin: 0 0 0.3rem; font-size: 1rem; }
      .idea-card .kcal { font-size: 0.8rem; color: var(--soft); }
      .idea-card .nutri { font-size: 0.75rem; color: var(--soft); }

      .status { margin-top: 0.5rem; min-height: 1.2rem; font-size: 0.8rem; color: var(--accent-dark); }

      .consumo-panel { background: rgba(46,204,113,0.1); border: 2px solid #27ae60; }
      .consumo-row { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr auto; gap: 0.5rem; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(0,0,0,0.08); }
      .consumo-row input { margin: 0; width: 100%; }
      .consumo-row .kcal-cons { font-weight: 600; text-align: center; }
      .progress-bar { width: 100%; height: 8px; background: rgba(0,0,0,0.1); border-radius: 4px; margin: 0.5rem 0; }
      .progress-fill { height: 100%; background: linear-gradient(90deg, #27ae60, #e74c3c); border-radius: 4px; transition: width 0.3s; }
      .ticket-area { margin-top: 1rem; }
      textarea { width: 100%; padding: 0.7rem; border-radius: 0.6rem; border: 1px solid rgba(0,0,0,0.12); font-family: inherit; font-size: 0.9rem; }
      .ticket-area textarea { width: 100%; height: 120px; border-radius: 0.8rem; padding: 0.8rem; font-family: monospace; font-size: 0.85rem; }

      @media (max-width: 700px) {
        .kcal-bar { grid-template-columns: 1fr; }
        .form-row { grid-template-columns: 1fr 1fr; }
        .table-wrapper { overflow-x: auto; }
        .consumo-row { grid-template-columns: 1fr auto; gap: 0.3rem; }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="panel">
        <p class="lede">Refrigerador familiar de Orson y Maritza. Agrega alimentos y genera ideas de comida balanceadas.</p>
        <h1>Refrigerador</h1>
      </section>

      <section class="panel" style="background:rgba(231,76,60,0.08); border:2px solid #e74c3c;">
        <h2 style="color:#c0392b;">⚠️ Artículos Agotados o en Cero</h2>
        <div class="section-tabs">
          <button class="tab active" onclick="filtrarEnCero('todos')">Todos</button>
          <button class="tab" onclick="filtrarEnCero('refrigerador')">Refrigerador</button>
          <button class="tab" onclick="filtrarEnCero('alacena')">Alacena</button>
        </div>
        <div id="en-cero-list" style="max-height:200px; overflow-y:auto;">
          <p style="color:var(--soft); font-size:0.85rem;">Cargando...</p>
        </div>
      </section>

      <section class="panel">
        <h2>Resumen Nutricional Diario</h2>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
          <div class="kcal-card kcal-orson">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="label">Orson</span>
              <select id="select-orson" onchange="cambiarPersona('orson')" style="font-size:0.7rem; padding:0.3rem;">
                <option value="orson" selected>Orson</option>
              </select>
            </div>
            <div style="font-size:1.8rem; font-weight:700;" id="get-orson">--</div>
            <div style="font-size:0.7rem; color:var(--soft);">kcal GET diarias</div>
            <div style="margin: 0.5rem 0;">
              <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
                <span>Consumidas:</span>
                <span id="consumidas-orson" style="font-weight:600;">0</span>
              </div>
              <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
                <span>Restantes:</span>
                <span id="restantes-orson" style="font-weight:600; color:#27ae60;">--</span>
              </div>
              <div class="progress-bar" style="height:12px; margin-top:0.3rem;">
                <div class="progress-fill" id="barra-orson" style="width:0%;"></div>
              </div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:0.5rem; font-size:0.7rem; margin-top:0.5rem;">
              <div style="text-align:center; padding:0.4rem; background:rgba(41,128,185,0.15); border-radius:0.4rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#2980b9;" id="prot-orson">--g</div>
                <div style="color:var(--soft); font-size:0.65rem;">Proteínas (30%)</div>
                <div style="font-size:0.6rem; color:var(--soft); margin:0.2rem 0;" id="prot-target-orson">Meta: --g</div>
                <div class="progress-bar" style="height:8px; margin-top:0.2rem;">
                  <div class="progress-fill" id="barra-prot-orson" style="width:0%; background:linear-gradient(90deg, #2980b9, #3498db);"></div>
                </div>
              </div>
              <div style="text-align:center; padding:0.4rem; background:rgba(142,68,173,0.15); border-radius:0.4rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#8e44ad;" id="carbos-orson">--g</div>
                <div style="color:var(--soft); font-size:0.65rem;">Carbos (55%)</div>
                <div style="font-size:0.6rem; color:var(--soft); margin:0.2rem 0;" id="carbos-target-orson">Meta: --g</div>
                <div class="progress-bar" style="height:8px; margin-top:0.2rem;">
                  <div class="progress-fill" id="barra-carbos-orson" style="width:0%; background:linear-gradient(90deg, #8e44ad, #9b59b6);"></div>
                </div>
              </div>
              <div style="text-align:center; padding:0.4rem; background:rgba(39,174,96,0.15); border-radius:0.4rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#27ae60;" id="grasas-orson">--g</div>
                <div style="color:var(--soft); font-size:0.65rem;">Grasas (15%)</div>
                <div style="font-size:0.6rem; color:var(--soft); margin:0.2rem 0;" id="grasas-target-orson">Meta: --g</div>
                <div class="progress-bar" style="height:8px; margin-top:0.2rem;">
                  <div class="progress-fill" id="barra-grasas-orson" style="width:0%; background:linear-gradient(90deg, #27ae60, #2ecc71);"></div>
                </div>
              </div>
            </div>
          </div>
          <div class="kcal-card kcal-maritza">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span class="label">Maritza</span>
              <select id="select-maritza" onchange="cambiarPersona('maritza')" style="font-size:0.7rem; padding:0.3rem;">
                <option value="maritza" selected>Maritza</option>
              </select>
            </div>
            <div style="font-size:1.8rem; font-weight:700;" id="get-maritza">--</div>
            <div style="font-size:0.7rem; color:var(--soft);">kcal GET diarias</div>
            <div style="margin: 0.5rem 0;">
              <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
                <span>Consumidas:</span>
                <span id="consumidas-maritza" style="font-weight:600;">0</span>
              </div>
              <div style="display:flex; justify-content:space-between; font-size:0.75rem;">
                <span>Restantes:</span>
                <span id="restantes-maritza" style="font-weight:600; color:#27ae60;">--</span>
              </div>
              <div class="progress-bar" style="height:12px; margin-top:0.3rem;">
                <div class="progress-fill" id="barra-maritza" style="width:0%;"></div>
              </div>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:0.5rem; font-size:0.7rem; margin-top:0.5rem;">
              <div style="text-align:center; padding:0.4rem; background:rgba(41,128,185,0.15); border-radius:0.4rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#2980b9;" id="prot-maritza">--g</div>
                <div style="color:var(--soft); font-size:0.65rem;">Proteínas (30%)</div>
                <div style="font-size:0.6rem; color:var(--soft); margin:0.2rem 0;" id="prot-target-maritza">Meta: --g</div>
                <div class="progress-bar" style="height:8px; margin-top:0.2rem;">
                  <div class="progress-fill" id="barra-prot-maritza" style="width:0%; background:linear-gradient(90deg, #2980b9, #3498db);"></div>
                </div>
              </div>
              <div style="text-align:center; padding:0.4rem; background:rgba(142,68,173,0.15); border-radius:0.4rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#8e44ad;" id="carbos-maritza">--g</div>
                <div style="color:var(--soft); font-size:0.65rem;">Carbos (55%)</div>
                <div style="font-size:0.6rem; color:var(--soft); margin:0.2rem 0;" id="carbos-target-maritza">Meta: --g</div>
                <div class="progress-bar" style="height:8px; margin-top:0.2rem;">
                  <div class="progress-fill" id="barra-carbos-maritza" style="width:0%; background:linear-gradient(90deg, #8e44ad, #9b59b6);"></div>
                </div>
              </div>
              <div style="text-align:center; padding:0.4rem; background:rgba(39,174,96,0.15); border-radius:0.4rem;">
                <div style="font-weight:700; font-size:1.1rem; color:#27ae60;" id="grasas-maritza">--g</div>
                <div style="color:var(--soft); font-size:0.65rem;">Grasas (15%)</div>
                <div style="font-size:0.6rem; color:var(--soft); margin:0.2rem 0;" id="grasas-target-maritza">Meta: --g</div>
                <div class="progress-bar" style="height:8px; margin-top:0.2rem;">
                  <div class="progress-fill" id="barra-grasas-maritza" style="width:0%; background:linear-gradient(90deg, #27ae60, #2ecc71);"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="nutri-summary" style="background:rgba(0,0,0,0.05);">
          <div class="nutri-item"><div class="val" id="total-kcal-hoy">0</div><div class="lbl">Kcal hoy</div></div>
          <div class="nutri-item"><div class="val" id="total-prot-hoy">0g</div><div class="lbl">Proteínas</div></div>
          <div class="nutri-item"><div class="val" id="total-carbos-hoy">0g</div><div class="lbl">Carbohidratos</div></div>
          <div class="nutri-item"><div class="val" id="total-grasas-hoy">0g</div><div class="lbl">Grasas</div></div>
          <div class="nutri-item"><div class="val" id="total-azuc-hoy">0g</div><div class="lbl">Azúcares</div></div>
        </div>
      </section>

      <section class="panel consumo-panel">
        <h2>Registro de Consumo</h2>
        <div style="background:rgba(46,204,113,0.1); padding:1rem; border-radius:0.8rem; margin-bottom:1rem;">
          <h3 style="margin:0 0 0.5rem; font-size:0.85rem;">Seleccionar del Refrigerador</h3>
          <div class="form-row">
            <div>
              <label>Alimento del refri</label>
              <select id="cons-refri" onchange="seleccionarDelRefri()">
                <option value="">-- Seleccionar --</option>
              </select>
            </div>
            <div>
              <label>Cantidad (piezas o porciones)</label>
              <input id="cons-piezas" type="number" value="1" min="1" onchange="calcularCantidad()">
            </div>
            <div>
              <label>Peso por pieza (g)</label>
              <input id="cons-peso-pieza" type="number" value="100" onchange="calcularCantidad()">
            </div>
            <div>
              <label style="color:var(--soft);">= Total (g)</label>
              <div id="cons-total-gramos" style="font-size:1.2rem; font-weight:700; padding:0.5rem; background:white; border-radius:0.5rem;">100g</div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <div>
            <label>Persona</label>
            <select id="cons-persona">
              <option value="orson">Orson</option>
              <option value="maritza">Maritza</option>
            </select>
          </div>
          <div>
            <label>Hora</label>
            <select id="cons-hora">
              <option value="desayuno">Desayuno</option>
              <option value="comida">Comida</option>
              <option value="cena">Cena</option>
              <option value="snack">Snack</option>
            </select>
          </div>
          <div>
            <label>Alimento (manual)</label>
            <input id="cons-alimento" placeholder="Nombre del alimento">
          </div>
          <div>
            <label>Cantidad (g)</label>
            <input id="cons-cantidad" type="number" value="250" placeholder="250">
          </div>
        </div>
        <div class="form-row" style="margin-top:0.5rem;">
          <div><label>Kcal/100g</label><input id="cons-kcal" type="number" placeholder="0" value="0"></div>
          <div><label>Proteínas g</label><input id="cons-prot" type="number" placeholder="0" value="0" step="0.1"></div>
          <div><label>Carbos g</label><input id="cons-carbs" type="number" placeholder="0" value="0" step="0.1"></div>
          <div><label>Grasas g</label><input id="cons-grasa" type="number" placeholder="0" value="0" step="0.1"></div>
        </div>
        <div style="margin-top:0.8rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
          <button class="btn" onclick="agregarConsumo()">+ Registrar al consumo</button>
        </div>
        <div id="consumo-list" style="margin-top:1rem;"></div>
        <div style="margin-top:1rem;">
          <button class="btn btn-danger" onclick="limpiarConsumo()">Limpiar registro diario</button>
        </div>
      </section>

      <section class="panel">
        <h2>Agregar Alimento</h2>
        <form id="itemForm">
        <div class="form-row">
          <div><label for="nombre">Nombre</label><input id="nombre" name="nombre" placeholder="Ej. Tomates" required></div>
          <div><label for="cantidad">Cantidad</label><input id="cantidad" name="cantidad" placeholder="Ej. 2 piezas"></div>
          <div><label for="categoria">Categoría</label>
            <select id="categoria" name="categoria">
                <option value="frutas">Frutas</option>
                <option value="verduras">Verduras</option>
                <option value="carnes">Carnes</option>
                <option value="lacteos">Lácteos</option>
                <option value="congelados">Congelados</option>
                <option value="granos">Granos</option>
                <option value="legumbres">Legumbres</option>
                <option value="condimentos">Condimentos</option>
                <option value="bebidas">Bebidas</option>
                <option value="comida-china">Comida China</option>
                <option value="alacena">Alacena</option>
                <option value="otros">Otros</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div><label for="kcal">Kcal/100g</label><input id="kcal" name="kcal" type="number" placeholder="0"></div>
            <div><label for="proteinas">Proteínas (g)</label><input id="proteinas" name="proteinas" type="number" placeholder="0" step="0.1"></div>
            <div><label for="grasas">Grasas (g)</label><input id="grasas" name="grasas" type="number" placeholder="0" step="0.1"></div>
            <div><label for="carbos">Carbohidratos (g)</label><input id="carbos" name="carbos" type="number" placeholder="0" step="0.1"></div>
          </div>
          <div class="form-row">
            <div><label for="azucares">Azúcares (g)</label><input id="azucares" name="azucares" type="number" placeholder="0" step="0.1"></div>
            <div><label for="fibra">Fibra (g)</label><input id="fibra" name="fibra" type="number" placeholder="0" step="0.1"></div>
            <div><label for="tipo-grasa">Tipo Grasa</label>
              <select id="tipo-grasa" name="tipo-grasa">
                <option value="">Sin clasificar</option>
                <option value="sat">Saturada</option>
                <option value="mono">Monoinsaturada</option>
                <option value="poli">Poliinsaturada</option>
                <option value="trans">Trans</option>
              </select>
            </div>
            <div><label for="ig">Índice Glucémico</label><input id="ig" name="ig" type="number" placeholder="0" min="0" max="100"></div>
          </div>
          <div class="form-row">
            <div><label for="calcio">Calcio (mg)</label><input id="calcio" name="calcio" type="number" placeholder="0"></div>
            <div><label for="hierro">Hierro (mg)</label><input id="hierro" name="hierro" type="number" placeholder="0" step="0.1"></div>
            <div><label for="potasio">Potasio (mg)</label><input id="potasio" name="potasio" type="number" placeholder="0"></div>
            <div><label for="fosforo">Fósforo (mg)</label><input id="fosforo" name="fosforo" type="number" placeholder="0"></div>
          </div>
          <div class="form-row">
            <div><label for="selenio">Selenio (mcg)</label><input id="selenio" name="selenio" type="number" placeholder="0"></div>
            <div><label for="zinc">Zinc (mg)</label><input id="zinc" name="zinc" type="number" placeholder="0" step="0.1"></div>
            <div><label for="magnesio">Magnesio (mg)</label><input id="magnesio" name="magnesio" type="number" placeholder="0"></div>
            <div><label for="cromo">Cromo (mcg)</label><input id="cromo" name="cromo" type="number" placeholder="0" step="0.1"></div>
          </div>
          <div class="form-row">
            <div><label>Caducidad</label><input type="date" id="fecha_cad"></div>
            <div><label>¿Congelado?</label><input type="checkbox" id="es_congelado" style="width:auto; margin-top:0.8rem;"></div>
          </div>
          <button type="submit" class="btn">Guardar Alimento</button>
        </form>
        <div class="status" id="status"></div>

        <div class="quick-add">
          <h3>Frutas de Temporada</h3>
          <div class="btn-grid" id="frutas-grid"></div>
          <h3>Carnes y Proteínas</h3>
          <div class="btn-grid" id="carnes-grid"></div>
          <h3>Lácteos</h3>
          <div class="btn-grid" id="lacteos-grid"></div>
          <h3>Leches</h3>
          <div class="btn-grid" id="leches-grid"></div>
          <h3>Verduras</h3>
          <div class="btn-grid" id="verduras-grid"></div>
          <h3>Granos y Legumbres</h3>
          <div class="btn-grid" id="granos-grid"></div>
          <h3>Bebidas</h3>
          <div class="btn-grid" id="bebidas-grid"></div>
          <h3>Condimentos</h3>
          <div class="btn-grid" id="condimentos-grid"></div>
        </div>
      </section>

      <section class="panel">
        <h2>Captura de Ticket de Compra</h2>
        <p style="font-size:0.8rem; color:var(--soft); margin-top:0;">Pega el texto del ticket para agregar artículos automáticamente</p>
        <label for="ticket-text" style="display:none;">Texto del ticket</label>
        <textarea id="ticket-text" name="ticket-text" placeholder="Pega aquí el texto del ticket..."></textarea>
        <button class="btn" onclick="procesarTicket()">Procesar Ticket</button>
      </section>

      <section class="panel">
        <h2>Contenido del Refrigerador</h2>
        <div class="section-tabs">
          <button class="tab active" data-cat="todos">Todos</button>
          <button class="tab" data-cat="frutas">Frutas</button>
          <button class="tab" data-cat="verduras">Verduras</button>
          <button class="tab" data-cat="carnes">Carnes</button>
          <button class="tab" data-cat="lacteos">Lácteos</button>
          <button class="tab" data-cat="congelados">❄️ Congelados</button>
          <button class="tab" data-cat="granos">Granos</button>
          <button class="tab" data-cat="legumbres">Legumbres</button>
          <button class="tab" data-cat="bebidas">Bebidas</button>
          <button class="tab" data-cat="comida-china">🍜 China</button>
          <button class="tab" data-cat="alacena">🏪 Alacena</button>
        </div>
        <div class="table-wrapper">
          <table id="itemsTable">
            <thead>
              <tr>
                <th>Alimento</th>
                <th>Cant</th>
                <th>Cad</th>
                <th>Urg</th>
                <th>Kcal</th>
                <th>P(g)</th>
                <th>G(g)</th>
                <th>C(g)</th>
                <th>IG</th>
                <th></th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </section>

      <section class="panel ideas-section">
        <h2>Ideas de Comida</h2>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1rem; align-items:center;">
          <button class="btn" onclick="generarIdeas('desayuno')">☀️ Desayuno</button>
          <button class="btn" onclick="generarIdeas('comida')">🍽️ Comida</button>
          <button class="btn" onclick="generarIdeas('cena')">🌙 Cena</button>
          <button class="btn" onclick="generarIdeas('snack')">🍎 Snack</button>
          <button class="btn" onclick="generarIdeas('rapida')">⚡ Rápida</button>
          <button class="btn" onclick="generarIdeas('saludable')">🥗 Saludable</button>
          <button class="btn" style="background:linear-gradient(135deg, #e67e22, #d35400);" onclick="generarIdeas('casera')">🏠 Comida casera</button>
          <div style="margin-left:auto;">
            <label style="display:inline; margin-right:0.3rem; font-size:0.7rem;">Para:</label>
            <select id="idea-persona" style="padding:0.4rem; border-radius:0.5rem; font-size:0.85rem;">
              <option value="orson">Orson</option>
              <option value="maritza">Maritza</option>
            </select>
          </div>
        </div>
        <div id="ideasList"></div>
        <div style="margin-top:1rem; text-align:center;">
          <button class="btn" style="background:linear-gradient(135deg, #9b59b6, #8e44ad);" onclick="generarIdeasActual()">🔄 Generar nuevas ideas</button>
        </div>
      </section>
    </main>

    <script>
      const ALIMENTOS = {
        frutas: [
          { nombre: 'Mango', cantidad: '1 pza', kcal: 60, prot: 0.8, gras: 0.4, carb: 15, azuc: 14, fibra: 1.6, ig: 51, cad_refri: 5, cad_cong: 40, img: '🥭' },
          { nombre: 'Aguacate', cantidad: '1 pza', kcal: 160, prot: 2, gras: 15, carb: 9, azuc: 0.7, fibra: 7, ig: 15, cad_refri: 5, cad_cong: 30, img: '🥑' },
          { nombre: 'Plátano', cantidad: '1 pza', kcal: 89, prot: 1.1, gras: 0.3, carb: 23, azuc: 12, fibra: 2.6, ig: 51, cad_refri: 5, cad_cong: 30, img: '🍌' },
          { nombre: 'Manzana', cantidad: '1 pza', kcal: 52, prot: 0.3, gras: 0.2, carb: 14, azuc: 10, fibra: 2.4, ig: 36, cad_refri: 14, cad_cong: 60, img: '🍎' },
          { nombre: 'Naranja', cantidad: '1 pza', kcal: 47, prot: 0.9, gras: 0.1, carb: 12, azuc: 9, fibra: 2.4, ig: 43, cad_refri: 14, cad_cong: 45, img: '🍊' },
          { nombre: 'Papaya', cantidad: '500g', kcal: 43, prot: 0.5, gras: 0.3, carb: 11, azuc: 7, fibra: 1.7, ig: 59, cad_refri: 7, cad_cong: 30, img: '🍈' },
          { nombre: 'Sandía', cantidad: '1kg', kcal: 30, prot: 0.6, gras: 0.2, carb: 8, azuc: 6, fibra: 0.4, ig: 76, cad_refri: 7, cad_cong: 45, img: '🍉' },
          { nombre: 'Fresas', cantidad: '250g', kcal: 32, prot: 0.7, gras: 0.3, carb: 8, azuc: 5, fibra: 2, ig: 40, cad_refri: 5, cad_cong: 30, img: '🍓' },
          { nombre: 'Uvas', cantidad: '300g', kcal: 69, prot: 0.7, gras: 0.2, carb: 18, azuc: 16, fibra: 0.9, ig: 59, cad_refri: 10, cad_cong: 45, img: '🍇' },
          { nombre: 'Piña', cantidad: '500g', kcal: 50, prot: 0.5, gras: 0.1, carb: 13, azuc: 10, fibra: 1.4, ig: 59, cad_refri: 7, cad_cong: 30, img: '🍍' },
          { nombre: 'Limón', cantidad: '6 pzas', kcal: 29, prot: 1.1, gras: 0.3, carb: 9, azuc: 2, fibra: 2.8, ig: 20, cad_refri: 21, cad_cong: 60, img: '🍋' },
          { nombre: 'Coco', cantidad: '100g', kcal: 354, prot: 3.3, gras: 33, carb: 15, azuc: 5, fibra: 9, ig: 45, cad_refri: 5, cad_cong: 60, img: '🥥' },
          { nombre: 'Pera', cantidad: '3 pzas', kcal: 57, prot: 0.4, gras: 0.1, carb: 15, azuc: 10, fibra: 3.1, ig: 38, cad_refri: 10, cad_cong: 45, img: '🍐' },
        ],
        carnes: [
          { nombre: 'Pollo', cantidad: '500g', kcal: 165, prot: 31, gras: 3.6, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 3, cad_cong: 30, tipo: 'bajo-grasa', img: '🍗' },
          { nombre: 'Res molida', cantidad: '500g', kcal: 250, prot: 26, gras: 15, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 3, cad_cong: 30, tipo: 'medio-grasa', img: '🥩' },
          { nombre: 'Cerdo', cantidad: '500g', kcal: 242, prot: 27, gras: 14, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 3, cad_cong: 30, tipo: 'medio-grasa', img: '🐖' },
          { nombre: 'Salchichas', cantidad: '6 pzas', kcal: 290, prot: 12, gras: 25, carb: 2, azuc: 1, fibra: 0, ig: 0, cad_refri: 5, cad_cong: 25, tipo: 'alto-grasa', img: '🌭' },
          { nombre: 'Jamón', cantidad: '200g', kcal: 145, prot: 21, gras: 6, carb: 1.5, azuc: 1, fibra: 0, ig: 0, cad_refri: 7, cad_cong: 25, tipo: 'medio-grasa', img: '🍖' },
          { nombre: 'Pechuga de pollo', cantidad: '400g', kcal: 120, prot: 23, gras: 2.5, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 3, cad_cong: 30, tipo: 'bajo-grasa', img: '🍗' },
          { nombre: 'Chicharrón', cantidad: '500g', kcal: 550, prot: 35, gras: 45, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 12, cad_cong: 60, tipo: 'alto-grasa', img: '🥓' },
          { nombre: 'Huevos', cantidad: '12 pzas', kcal: 155, prot: 13, gras: 11, carb: 1.1, azuc: 1.1, fibra: 0, ig: 0, cad_refri: 21, cad_cong: 90, tipo: 'medio-grasa', img: '🥚' },
          { nombre: 'Atún', cantidad: '1 lata', kcal: 132, prot: 29, gras: 1, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 5, cad_cong: 30, tipo: 'bajo-grasa', img: '🐟' },
        ],
        lacteos: [
          { nombre: 'Queso oaxaca', cantidad: '300g', kcal: 280, prot: 25, gras: 21, carb: 1, azuc: 0.5, fibra: 0, ig: 0, cad_refri: 14, cad_cong: 60, img: '🧀' },
          { nombre: 'Queso panela', cantidad: '400g', kcal: 200, prot: 20, gras: 12, carb: 3, azuc: 0, fibra: 0, ig: 0, cad_refri: 14, cad_cong: 60, img: '🧀' },
          { nombre: 'Queso cotija', cantidad: '200g', kcal: 300, prot: 25, gras: 22, carb: 2, azuc: 0, fibra: 0, ig: 0, cad_refri: 21, cad_cong: 90, img: '🧀' },
          { nombre: 'Queso Monterrey', cantidad: '200g', kcal: 350, prot: 25, gras: 28, carb: 1, azuc: 0, fibra: 0, ig: 0, cad_refri: 14, cad_cong: 60, img: '🧀' },
          { nombre: 'Crema', cantidad: '500ml', kcal: 210, prot: 2, gras: 22, carb: 4, azuc: 3, fibra: 0, ig: 0, cad_refri: 7, cad_cong: 60, img: '🥛' },
          { nombre: 'Yogur natural', cantidad: '500g', kcal: 59, prot: 3.5, gras: 1, carb: 4, azuc: 4, fibra: 0, ig: 15, cad_refri: 14, cad_cong: 45, img: '🥛' },
          { nombre: 'Mantequilla barra', cantidad: '90g', kcal: 717, prot: 1, gras: 81, carb: 0.1, azuc: 0.1, fibra: 0, ig: 0, cad_refri: 30, cad_cong: 180, tipo: 'alto-grasa', img: '🧈' },
          { nombre: 'Pastel de queso', cantidad: '1/2 pastel', kcal: 320, prot: 6, gras: 18, carb: 35, azuc: 25, fibra: 0, ig: 45, cad_refri: 5, cad_cong: 30, img: '🍰' },
        ],
        leches: [
          { nombre: 'Leche entera', cantidad: '1L', kcal: 61, prot: 3.2, gras: 3.3, carb: 4.8, azuc: 5, fibra: 0, ig: 15, cad_refri: 7, cad_cong: 45, tipo: 'medio-grasa', img: '🥛' },
          { nombre: 'Leche semidescremada', cantidad: '1L', kcal: 45, prot: 3.4, gras: 1.5, carb: 5, azuc: 5, fibra: 0, ig: 15, cad_refri: 7, cad_cong: 45, tipo: 'bajo-grasa', img: '🥛' },
          { nombre: 'Leche descremada', cantidad: '1L', kcal: 35, prot: 3.4, gras: 0.2, carb: 5, azuc: 5, fibra: 0, ig: 15, cad_refri: 7, cad_cong: 45, tipo: 'bajo-grasa', img: '🥛' },
          { nombre: 'Leche chocolatada', cantidad: '1L', kcal: 85, prot: 3, gras: 2.5, carb: 14, azuc: 12, fibra: 0, ig: 35, cad_refri: 7, cad_cong: 45, img: '🥛' },
          { nombre: 'Leche de avena', cantidad: '1L', kcal: 45, prot: 1, gras: 1.5, carb: 7, azuc: 4, fibra: 1, ig: 30, cad_refri: 10, cad_cong: 45, img: '🥛' },
          { nombre: 'Yogur de fruta', cantidad: '500g', kcal: 85, prot: 3, gras: 1, carb: 16, azuc: 14, fibra: 0, ig: 30, cad_refri: 14, cad_cong: 45, img: '🥛' },
        ],
        verduras: [
          { nombre: 'Jitomate', cantidad: '6 pzas', kcal: 18, prot: 0.9, gras: 0.2, carb: 4, azuc: 2.5, fibra: 1.2, ig: 15, cad_refri: 10, cad_cong: 45, img: '🍅' },
          { nombre: 'Cebolla', cantidad: '3 pzas', kcal: 40, prot: 1.1, gras: 0.1, carb: 9, azuc: 4, fibra: 1.7, ig: 10, cad_refri: 30, cad_cong: 60, img: '🧅' },
          { nombre: 'Ajo', cantidad: '1 cabeza', kcal: 149, prot: 6.4, gras: 0.5, carb: 33, azuc: 1, fibra: 2.1, ig: 10, cad_refri: 30, cad_cong: 60, img: '🧄' },
          { nombre: 'Chile', cantidad: '4 pzas', kcal: 40, prot: 2, gras: 0.4, carb: 9, azuc: 4, fibra: 1.5, ig: 15, cad_refri: 14, cad_cong: 45, img: '🌶️' },
          { nombre: 'Pimiento', cantidad: '2 pzas', kcal: 31, prot: 1, gras: 0.3, carb: 6, azuc: 4, fibra: 2.1, ig: 15, cad_refri: 14, cad_cong: 45, img: '🫑' },
          { nombre: 'Lechuga', cantidad: '1 cabeza', kcal: 15, prot: 1.4, gras: 0.2, carb: 3, azuc: 1, fibra: 1.3, ig: 10, cad_refri: 7, cad_cong: 30, img: '🥬' },
          { nombre: 'Espinacas', cantidad: '300g', kcal: 23, prot: 2.9, gras: 0.4, carb: 3.6, azuc: 0.4, fibra: 2.2, ig: 15, cad_refri: 5, cad_cong: 30, img: '🥬' },
          { nombre: 'Brócoli', cantidad: '400g', kcal: 34, prot: 2.8, gras: 0.4, carb: 7, azuc: 1.5, fibra: 2.6, ig: 15, cad_refri: 7, cad_cong: 45, img: '🥦' },
          { nombre: 'Calabaza', cantidad: '500g', kcal: 26, prot: 1, gras: 0.1, carb: 6.5, azuc: 3, fibra: 0.5, ig: 45, cad_refri: 14, cad_cong: 45, img: '🎃' },
          { nombre: 'Elote', cantidad: '4 pzas', kcal: 86, prot: 3.3, gras: 1.4, carb: 19, azuc: 6, fibra: 2.7, ig: 52, cad_refri: 5, cad_cong: 45, img: '🌽' },
          { nombre: 'Zanahoria', cantidad: '500g', kcal: 41, prot: 0.9, gras: 0.2, carb: 10, azuc: 5, fibra: 2.8, ig: 35, cad_refri: 21, cad_cong: 60, img: '🥕' },
          { nombre: 'Nopal', cantidad: '400g', kcal: 16, prot: 1.3, gras: 0.1, carb: 3.3, azuc: 1, fibra: 2.2, ig: 15, cad_refri: 7, cad_cong: 30, img: '🌵' },
        ],
        granos: [
          { nombre: 'Tortillas de maíz', cantidad: '1kg', kcal: 218, prot: 5.7, gras: 2.8, carb: 45, azuc: 0.5, fibra: 6, ig: 52, cad_refri: 10, cad_cong: 60, img: '🫓' },
          { nombre: 'Tortillas de harina', cantidad: '30 pzas', kcal: 304, prot: 8, gras: 8, carb: 50, azuc: 2, fibra: 2, ig: 68, cad_refri: 14, cad_cong: 60, img: '🫓' },
          { nombre: 'Tortillas integrales', cantidad: '20 pzas', kcal: 260, prot: 9, gras: 7, carb: 45, azuc: 2, fibra: 7, ig: 55, cad_refri: 14, cad_cong: 60, img: '🫓' },
          { nombre: 'Arroz blanco', cantidad: '1kg', kcal: 130, prot: 2.7, gras: 0.3, carb: 28, azuc: 0, fibra: 0.4, ig: 73, cad_refri: 365, cad_cong: 365, img: '🍚' },
          { nombre: 'Arroz integral', cantidad: '1kg', kcal: 112, prot: 2.6, gras: 0.9, carb: 24, azuc: 0.5, fibra: 1.8, ig: 50, cad_refri: 365, cad_cong: 365, img: '🍚' },
          { nombre: 'Frijoles', cantidad: '500g', kcal: 78, prot: 5, gras: 0.4, carb: 14, azuc: 0.3, fibra: 6.5, ig: 30, cad_refri: 7, cad_cong: 180, tipo: 'complejo', img: '🫘' },
          { nombre: 'Lentejas', cantidad: '500g', kcal: 116, prot: 9, gras: 0.4, carb: 20, azuc: 1.8, fibra: 8, ig: 25, cad_refri: 365, cad_cong: 365, tipo: 'complejo', img: '🫘' },
          { nombre: 'Habas', cantidad: '500g', kcal: 110, prot: 8, gras: 0.4, carb: 19, azuc: 5, fibra: 5, ig: 30, cad_refri: 5, cad_cong: 90, tipo: 'complejo', img: '🫘' },
          { nombre: 'Pan blanco', cantidad: '500g', kcal: 265, prot: 9, gras: 3.2, carb: 49, azuc: 5, fibra: 2.7, ig: 70, cad_refri: 7, cad_cong: 90, img: '🍞' },
          { nombre: 'Pan integral', cantidad: '500g', kcal: 240, prot: 10, gras: 3.5, carb: 42, azuc: 6, fibra: 7, ig: 55, cad_refri: 7, cad_cong: 90, img: '🍞' },
          { nombre: 'Pasta', cantidad: '500g', kcal: 131, prot: 5, gras: 1.1, carb: 25, azuc: 0.6, fibra: 1.8, ig: 65, cad_refri: 730, cad_cong: 730, img: '🍝' },
          { nombre: 'Totopos', cantidad: '500g', kcal: 489, prot: 7, gras: 25, carb: 60, azuc: 1, fibra: 4, ig: 55, cad_refri: 60, cad_cong: 180, img: '🫓' },
        ],
        bebidas: [
          { nombre: 'Coca-Cola 600ml', cantidad: '1 pza', kcal: 42, prot: 0, gras: 0, carb: 11, azuc: 11, fibra: 0, ig: 63, cad_refri: 180, cad_cong: 180, tipo: 'azucar-simple', img: '🥤' },
          { nombre: 'Coca-Cola 2L', cantidad: '1 pza', kcal: 42, prot: 0, gras: 0, carb: 11, azuc: 11, fibra: 0, ig: 63, cad_refri: 180, cad_cong: 180, tipo: 'azucar-simple', img: '🥤' },
          { nombre: 'Agua natural', cantidad: '1L', kcal: 0, prot: 0, gras: 0, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 365, cad_cong: 365, img: '💧' },
          { nombre: 'Jugo de naranja', cantidad: '1L', kcal: 45, prot: 0.7, gras: 0.2, carb: 10, azuc: 8, fibra: 0.2, ig: 50, cad_refri: 7, cad_cong: 45, img: '🧃' },
          { nombre: 'Refresco de dieta', cantidad: '600ml', kcal: 0, prot: 0, gras: 0, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 180, cad_cong: 180, img: '🥤' },
          { nombre: 'Café', cantidad: '1 taza', kcal: 2, prot: 0.3, gras: 0, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 2, cad_cong: 0, img: '☕' },
          { nombre: 'Té', cantidad: '1 taza', kcal: 2, prot: 0, gras: 0, carb: 0.5, azuc: 0, fibra: 0, ig: 5, cad_refri: 2, cad_cong: 0, img: '🍵' },
        ],
        condimentos: [
          { nombre: 'Mayonesa', cantidad: '1kg', kcal: 680, prot: 1, gras: 75, carb: 1, azuc: 0, fibra: 0, ig: 0, cad_refri: 180, cad_cong: 365, img: '🫙' },
          { nombre: 'Catsup', cantidad: '500g', kcal: 112, prot: 1.7, gras: 0.1, carb: 27, azuc: 22, fibra: 0.5, ig: 50, cad_refri: 365, cad_cong: 365, img: '🫙' },
          { nombre: 'Mostaza', cantidad: '400g', kcal: 66, prot: 4, gras: 4, carb: 5, azuc: 2, fibra: 3, ig: 15, cad_refri: 365, cad_cong: 365, img: '🫙' },
          { nombre: 'Chipotles', cantidad: '1 lata', kcal: 40, prot: 2, gras: 1, carb: 7, azuc: 5, fibra: 2, ig: 30, cad_refri: 180, cad_cong: 365, img: '🌶️' },
          { nombre: 'Salsa soy', cantidad: '500ml', kcal: 53, prot: 8, gras: 0, carb: 5, azuc: 0, fibra: 0.8, ig: 15, cad_refri: 730, cad_cong: 730, img: '🫙' },
          { nombre: 'Aceite de oliva', cantidad: '500ml', kcal: 884, prot: 0, gras: 100, carb: 0, azuc: 0, fibra: 0, ig: 0, cad_refri: 730, cad_cong: 730, img: '🫒' },
          { nombre: 'Miel', cantidad: '500g', kcal: 304, prot: 0.3, gras: 0, carb: 82, azuc: 82, fibra: 0.2, ig: 61, cad_refri: 730, cad_cong: 730, tipo: 'azucar-simple', img: '🍯' },
        ]
      };

      let currentFilter = 'todos';

      function renderQuickButtons() {
        const grids = { frutas: 'frutas-grid', carnes: 'carnes-grid', lacteos: 'lacteos-grid', leches: 'leches-grid', verduras: 'verduras-grid', granos: 'granos-grid', bebidas: 'bebidas-grid', condimentos: 'condimentos-grid' };
        Object.entries(grids).forEach(([cat, gridId]) => {
          const grid = document.getElementById(gridId);
          if (!grid || !ALIMENTOS[cat]) return;
          grid.innerHTML = ALIMENTOS[cat].map(a => `
            <div class="quick-btn" style="flex-direction:column; align-items:center; padding:0.8rem;">
              <div style="font-size:1.5rem;">${a.img || ''}</div>
              <div style="font-weight:600; font-size:0.8rem;">${a.nombre}</div>
              <div class="qty-control" onclick="event.stopPropagation()">
                <button class="qty-btn" onclick="cambiarCantidad('${a.nombre}', -1)">−</button>
                <span class="qty-val" id="qty-${a.nombre}">1</span>
                <button class="qty-btn" onclick="cambiarCantidad('${a.nombre}', 1)">+</button>
              </div>
              <div style="font-size:0.65rem; color:var(--soft);">${a.cantidad}</div>
            </div>
          `).join('');

          grid.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
              const nombre = btn.querySelector('div:nth-child(2)').textContent;
              const item = Object.values(ALIMENTOS).flat().find(a => a.nombre === nombre);
              if (!item) return;
              const qty = parseInt(document.getElementById('qty-' + nombre)?.textContent || '1');
              autoFillForm(item);
              if (confirm(`¿Agregar ${qty}x ${nombre} al refrigerador?`)) {
                for (let i = 0; i < qty; i++) {
                  addItem(item);
                }
              }
            });
          });
        });
      }

      const cantidades = {};
      function cambiarCantidad(nombre, delta) {
        cantidades[nombre] = Math.max(1, (cantidades[nombre] || 1) + delta);
        document.getElementById('qty-' + nombre).textContent = cantidades[nombre];
      }

      function autoFillForm(item) {
        document.getElementById('nombre').value = item.nombre;
        document.getElementById('cantidad').value = item.cantidad;
        document.getElementById('kcal').value = item.kcal;
        document.getElementById('proteinas').value = item.prot;
        document.getElementById('grasas').value = item.gras;
        document.getElementById('carbos').value = item.carb;
        document.getElementById('azucares').value = item.azuc || 0;
        document.getElementById('fibra').value = item.fibra || 0;
        document.getElementById('ig').value = item.ig || 0;
        
        const today = new Date();
        const cad = new Date(today);
        cad.setDate(cad.getDate() + item.cad_refri);
        document.getElementById('fecha_cad').value = cad.toISOString().split('T')[0];
      }

      async function addItem(item) {
        const today = new Date();
        const cad = new Date(today);
        cad.setDate(cad.getDate() + item.cad_refri);
        
        await fetch('/api/refrigerador', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: item.nombre,
            cantidad: item.cantidad,
            categoria: getCategoria(item),
            kcal: item.kcal,
            proteinas: item.prot,
            grasas: item.gras,
            carbohidratos: item.carb,
            azucares: item.azuc || 0,
            fibra: item.fibra || 0,
            ig: item.ig || 0,
            consumir_antes: cad.toISOString().split('T')[0]
          })
        });
        fetchItems(currentFilter);
      }

      function getCategoria(item) {
        const nombre = item.nombre.toLowerCase();
        if (nombre.includes('leche') || nombre.includes('yogur')) return 'lacteos';
        if (nombre.includes('pollo') || nombre.includes('res') || nombre.includes('cerdo') || nombre.includes('huevo') || nombre.includes('atún') || nombre.includes('jamón') || nombre.includes('chicharrón')) return 'carnes';
        if (nombre.includes('aguacate') || nombre.includes('mango') || nombre.includes('plátano') || nombre.includes('manzana') || nombre.includes('naranja') || nombre.includes('fresa') || nombre.includes('uva') || nombre.includes('pera')) return 'frutas';
        if (nombre.includes('jitomate') || nombre.includes('cebolla') || nombre.includes('ajo') || nombre.includes('lechuga') || nombre.includes('brócoli') || nombre.includes('zanahoria') || nombre.includes('nopal')) return 'verduras';
        if (nombre.includes('frijol') || nombre.includes('lenteja') || nombre.includes('haba')) return 'legumbres';
        if (nombre.includes('tortilla') || nombre.includes('arroz') || nombre.includes('pan') || nombre.includes('pasta') || nombre.includes('totopo')) return 'granos';
        if (nombre.includes('coca') || nombre.includes('refresco') || nombre.includes('agua') || nombre.includes('jugo') || nombre.includes('café') || nombre.includes('té')) return 'bebidas';
        return 'otros';
      }

      function getUrgency(item) {
        if (!item.consumir_antes && !item.fecha_cad) return { text: 'OK', cls: 'ok' };
        const now = new Date();
        const cadDate = new Date(item.consumir_antes || item.fecha_cad);
        const diff = Math.ceil((cadDate - now) / (1000*60*60*24));
        if (item.categoria === 'congelados') return { text: '❄️', cls: 'frozen' };
        if (diff <= 2) return { text: '¡YA!', cls: 'soon' };
        if (diff <= 5) return { text: diff+'d', cls: 'soon' };
        return { text: diff+'d', cls: 'ok' };
      }

      function formatDate(str) {
        if (!str) return '-';
        return new Date(str).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
      }

      async function fetchItems(cat = 'todos') {
        currentFilter = cat;
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        var catTab = document.querySelector('.tab[data-cat="' + cat + '"]');
        if (catTab) catTab.classList.add('active');

        const res = await fetch('/api/refrigerador' + (cat !== 'todos' ? '?categoria=' + cat : ''));
        const items = await res.json();

        const tbody = document.querySelector('#itemsTable tbody');
        if (items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="10">Vacío. Agrega alimentos.</td></tr>';
          return;
        }

        tbody.innerHTML = items.map(item => {
          const urg = getUrgency(item);
          return `<tr>
            <td><strong>${item.nombre}</strong></td>
            <td>${item.cantidad || '-'}</td>
            <td>${formatDate(item.consumir_antes)}</td>
            <td><span class="urgency ${urg.cls}">${urg.text}</span></td>
            <td>${item.kcal || '-'}</td>
            <td>${item.proteinas || '-'}</td>
            <td>${item.grasas || '-'}</td>
            <td>${item.carbohidratos || '-'}</td>
            <td>${item.ig || '-'}</td>
            <td>
              <button class="consumir-btn" onclick="consumirItem(&quot;${item.id}&quot;, &quot;${item.nombre}&quot;)" style="background:#27ae60; color:white; border:none; border-radius:0.3rem; padding:0.25rem 0.5rem; cursor:pointer; font-size:0.7rem; margin-right:0.3rem;">✓</button>
              <button class="delete-btn" onclick="delItem(&quot;${item.id}&quot;)">✕</button>
            </td>
          </tr>`;
        }).join('');
      }

      document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => fetchItems(tab.dataset.cat));
      });

      async function delItem(id) {
        await fetch('/api/refrigerador/' + id, { method: 'DELETE' });
        fetchItems(currentFilter);
      }

      async function consumirItem(id, nombre) {
        const persona = confirm('Para quien es?\\n\\nOK = Orson\\nCancelar = Maritza') ? 'orson' : 'maritza';
        try {
          const res = await fetch('/api/refrigerador/' + id + '/consumir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ persona, hora: 'comida' })
          });
          const data = await res.json();
          if (data.ok) {
            alert('¡' + nombre + ' agregado al consumo!');
            await cargarConsumoHoy();
            fetchItems(currentFilter);
          }
        } catch (e) { console.error('Error:', e); }
      }

      document.getElementById('itemForm').addEventListener('submit', async e => {
        e.preventDefault();
        const data = {
          nombre: document.getElementById('nombre').value.trim(),
          cantidad: document.getElementById('cantidad').value.trim(),
          categoria: document.getElementById('categoria').value,
          kcal: parseFloat(document.getElementById('kcal').value) || 0,
          proteinas: parseFloat(document.getElementById('proteinas').value) || 0,
          grasas: parseFloat(document.getElementById('grasas').value) || 0,
          carbohidratos: parseFloat(document.getElementById('carbos').value) || 0,
          azucares: parseFloat(document.getElementById('azucares').value) || 0,
          fibra: parseFloat(document.getElementById('fibra').value) || 0,
          ig: parseFloat(document.getElementById('ig').value) || 0,
          tipo_grasa: document.getElementById('tipo-grasa').value,
          calcio: parseFloat(document.getElementById('calcio').value) || 0,
          hierro: parseFloat(document.getElementById('hierro').value) || 0,
          potasio: parseFloat(document.getElementById('potasio').value) || 0,
          fosforo: parseFloat(document.getElementById('fosforo').value) || 0,
          selenio: parseFloat(document.getElementById('selenio').value) || 0,
          zinc: parseFloat(document.getElementById('zinc').value) || 0,
          magnesio: parseFloat(document.getElementById('magnesio').value) || 0,
          cromo: parseFloat(document.getElementById('cromo').value) || 0,
          consumir_antes: document.getElementById('fecha_cad').value || null,
        };

        const res = await fetch('/api/refrigerador', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        if (res.ok) {
          document.getElementById('status').textContent = '✓ Guardado';
          document.getElementById('itemForm').reset();
          fetchItems(currentFilter);
        } else {
          document.getElementById('status').textContent = 'Error al guardar';
        }
      });

      async function loadKcalInfo() {
        try {
          const res = await fetch('/api/kcal-info');
          if (!res.ok) throw new Error('HTTP ' + res.status);
          const data = await res.json();
          getOrson = Math.round(data.orson.get);
          getMaritza = Math.round(data.maritza.get);
          await cargarConsumoHoy();
          cargarEnCero('todos');
        } catch (e) { console.error('Error cargando kcal:', e); }
      }

      let enCeroFilter = 'todos';

      async function cargarEnCero(filtro) {
        enCeroFilter = filtro;
        document.querySelectorAll('#en-cero-list + .section-tabs .tab, .panel:has(#en-cero-list) .tab').forEach(t => {
          t.classList.remove('active');
        });
        try {
          const cat = filtro === 'refrigerador' ? 'todos' : filtro;
          const res = await fetch('/api/refrigerador/en-cero?categoria=' + cat);
          const items = await res.json();
          const list = document.getElementById('en-cero-list');
          if (items.length === 0) {
            list.innerHTML = '<p style="color:var(--soft); font-size:0.85rem;">No hay artículos agotados</p>';
            return;
          }
          list.innerHTML = '<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:0.5rem;">' +
            items.map(item => {
              const bgColor = item.categoria === 'alacena' ? 'rgba(142,68,173,0.15)' : 'rgba(41,128,185,0.15)';
              return '<div style="padding:0.5rem; background:' + bgColor + '; border-radius:0.5rem; display:flex; justify-content:space-between; align-items:center;">' +
                '<div><strong>' + item.nombre + '</strong><br><small style="color:var(--soft);">' + (item.categoria === 'alacena' ? 'Alacena' : 'Refrigerador') + '</small></div>' +
                '<div style="text-align:right;"><span style="color:#e74c3c; font-weight:bold;">0</span><br><small>' + item.cantidad + '</small></div>' +
                '</div>';
            }).join('') + '</div>';
        } catch (e) { console.error('Error cargando en cero:', e); }
      }

      function filtrarEnCero(filtro) {
        cargarEnCero(filtro);
      }

      async function cargarConsumoHoy() {
        try {
          const res = await fetch('/api/consumo/hoy');
          if (!res.ok) throw new Error('HTTP ' + res.status);
          const data = await res.json();
          consumoOrson = {
            kcal: data.orson?.kcal || 0,
            prot: data.orson?.proteinas || 0,
            carbs: data.orson?.carbohidratos || 0,
            grasa: data.orson?.grasas || 0
          };
          consumoMaritza = {
            kcal: data.maritza?.kcal || 0,
            prot: data.maritza?.proteinas || 0,
            carbs: data.maritza?.carbohidratos || 0,
            grasa: data.maritza?.grasas || 0
          };
          consumoList = [];
          actualizarTotalesConsumo();
          renderConsumo();
        } catch (e) { console.error('Error cargando consumo:', e); }
      }

      async function agregarConsumo() {
        const alimento = document.getElementById('cons-alimento').value.trim();
        const cantidad = parseFloat(document.getElementById('cons-cantidad').value) || 100;
        const kcal = parseFloat(document.getElementById('cons-kcal').value) || 0;
        const prot = parseFloat(document.getElementById('cons-prot').value) || 0;
        const carbs = parseFloat(document.getElementById('cons-carbs').value) || 0;
        const grasa = parseFloat(document.getElementById('cons-grasa').value) || 0;
        const persona = document.getElementById('cons-persona').value;
        const hora = document.getElementById('cons-hora').value;

        if (!alimento) {
          alert('Ingresa el nombre del alimento');
          return;
        }

        const factor = cantidad / 100;
        const item = {
          id: Date.now(),
          alimento: alimento,
          cantidad: cantidad,
          kcal: kcal * factor,
          prot: prot * factor,
          carbs: carbs * factor,
          grasa: grasa * factor,
          persona: persona,
          hora: hora
        };

        try {
          await fetch('/api/consumo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              alimento: item.alimento,
              cantidad: item.cantidad,
              kcal: item.kcal,
              proteinas: item.prot,
              carbohidratos: item.carbs,
              grasas: item.grasa,
              persona: item.persona,
              hora: item.hora
            })
          });
        } catch (e) { console.error('Error guardando consumo:', e); }

        consumoList.push(item);
        
        if (persona === 'orson') {
          consumoOrson.kcal += item.kcal;
          consumoOrson.prot += item.prot;
          consumoOrson.carbs += item.carbs;
          consumoOrson.grasa += item.grasa;
        } else {
          consumoMaritza.kcal += item.kcal;
          consumoMaritza.prot += item.prot;
          consumoMaritza.carbs += item.carbs;
          consumoMaritza.grasa += item.grasa;
        }

        renderConsumo();
        actualizarTotalesConsumo();

        document.getElementById('cons-alimento').value = '';
        document.getElementById('cons-cantidad').value = '100';
        document.getElementById('cons-kcal').value = '0';
        document.getElementById('cons-prot').value = '0';
        document.getElementById('cons-carbs').value = '0';
        document.getElementById('cons-grasa').value = '0';
      }

      function renderConsumo() {
        const list = document.getElementById('consumo-list');
        if (consumoList.length === 0) {
          list.innerHTML = '<p style="color:var(--soft); font-size:0.85rem; padding:1rem;">Sin consumo registrado hoy. Agrega alimentos arriba.</p>';
          return;
        }
        list.innerHTML = '<table style="width:100%; border-collapse:collapse; font-size:0.8rem;"><thead><tr style="background:rgba(0,0,0,0.05);"><th style="padding:0.5rem; text-align:left;">Alimento</th><th style="padding:0.5rem;">g</th><th style="padding:0.5rem;">Kcal</th><th style="padding:0.5rem;">P</th><th style="padding:0.5rem;">C</th><th style="padding:0.5rem;">G</th><th style="padding:0.5rem;">Quién</th><th style="padding:0.5rem;"></th></tr></thead><tbody>' +
          consumoList.map((c, i) => `
            <tr style="border-bottom:1px solid rgba(0,0,0,0.05);">
              <td style="padding:0.5rem;"><strong>${c.alimento}</strong><br><small style="color:var(--soft)">${c.hora}</small></td>
              <td style="padding:0.5rem; text-align:center;">${c.cantidad}</td>
              <td style="padding:0.5rem; text-align:center; font-weight:600;">${Math.round(c.kcal)}</td>
              <td style="padding:0.5rem; text-align:center;">${c.prot.toFixed(1)}g</td>
              <td style="padding:0.5rem; text-align:center;">${c.carbs.toFixed(1)}g</td>
              <td style="padding:0.5rem; text-align:center;">${c.grasa.toFixed(1)}g</td>
              <td style="padding:0.5rem; text-align:center;"><span style="padding:0.2rem 0.5rem; border-radius:1rem; font-size:0.7rem; background:${c.persona === 'orson' ? 'rgba(41,128,185,0.2)' : 'rgba(142,68,173,0.2)'};">${c.persona === 'orson' ? 'O' : 'M'}</span></td>
              <td style="padding:0.5rem;"><button class="delete-btn" onclick="removerConsumo(${i})" style="padding:0.2rem 0.5rem;">✕</button></td>
            </tr>
          `).join('') +
          '</tbody></table>';
      }

      function removerConsumo(idx) {
        const item = consumoList[idx];
        if (item.persona === 'orson') {
          consumoOrson.kcal -= item.kcal;
          consumoOrson.prot -= item.prot;
          consumoOrson.carbs -= item.carbs;
          consumoOrson.grasa -= item.grasa;
        } else {
          consumoMaritza.kcal -= item.kcal;
          consumoMaritza.prot -= item.prot;
          consumoMaritza.carbs -= item.carbs;
          consumoMaritza.grasa -= item.grasa;
        }
        consumoList.splice(idx, 1);
        renderConsumo();
        actualizarTotalesConsumo();
      }

      function limpiarConsumo() {
        if (!confirm('¿Limpiar todo el registro de hoy?')) return;
        consumoList = [];
        consumoOrson = { kcal: 0, prot: 0, carbs: 0, grasa: 0 };
        consumoMaritza = { kcal: 0, prot: 0, carbs: 0, grasa: 0 };
        renderConsumo();
        actualizarTotalesConsumo();
      }

      function actualizarTotalesConsumo() {
        const orsonRest = Math.max(0, getOrson - consumoOrson.kcal);
        const maritzaRest = Math.max(0, getMaritza - consumoMaritza.kcal);
        const orsonPct = Math.min(100, (consumoOrson.kcal / getOrson) * 100);
        const maritzaPct = Math.min(100, (consumoMaritza.kcal / getMaritza) * 100);

        document.getElementById('get-orson').textContent = getOrson;
        document.getElementById('get-maritza').textContent = getMaritza;
        document.getElementById('consumidas-orson').textContent = Math.round(consumoOrson.kcal);
        document.getElementById('consumidas-maritza').textContent = Math.round(consumoMaritza.kcal);
        document.getElementById('restantes-orson').textContent = Math.round(orsonRest);
        document.getElementById('restantes-maritza').textContent = Math.round(maritzaRest);
        
        const barraO = document.getElementById('barra-orson');
        const barraM = document.getElementById('barra-maritza');
        barraO.style.width = orsonPct + '%';
        barraM.style.width = maritzaPct + '%';
        barraO.style.background = orsonPct > 100 ? '#e74c3c' : 'linear-gradient(90deg, #27ae60, #2ecc71)';
        barraM.style.background = maritzaPct > 100 ? '#e74c3c' : 'linear-gradient(90deg, #8e44ad, #9b59b6)';

        const protTargetOrson = Math.round((getOrson * 0.30) / 4);
        const carbsTargetOrson = Math.round((getOrson * 0.55) / 4);
        const grasasTargetOrson = Math.round((getOrson * 0.15) / 9);
        const protTargetMaritza = Math.round((getMaritza * 0.30) / 4);
        const carbsTargetMaritza = Math.round((getMaritza * 0.55) / 4);
        const grasasTargetMaritza = Math.round((getMaritza * 0.15) / 9);

        document.getElementById('prot-target-orson').textContent = 'Meta: ' + protTargetOrson + 'g';
        document.getElementById('carbos-target-orson').textContent = 'Meta: ' + carbsTargetOrson + 'g';
        document.getElementById('grasas-target-orson').textContent = 'Meta: ' + grasasTargetOrson + 'g';
        document.getElementById('prot-target-maritza').textContent = 'Meta: ' + protTargetMaritza + 'g';
        document.getElementById('carbos-target-maritza').textContent = 'Meta: ' + carbsTargetMaritza + 'g';
        document.getElementById('grasas-target-maritza').textContent = 'Meta: ' + grasasTargetMaritza + 'g';

        document.getElementById('prot-orson').textContent = Math.round(consumoOrson.prot) + 'g';
        document.getElementById('prot-maritza').textContent = Math.round(consumoMaritza.prot) + 'g';
        document.getElementById('carbos-orson').textContent = Math.round(consumoOrson.carbs) + 'g';
        document.getElementById('carbos-maritza').textContent = Math.round(consumoMaritza.carbs) + 'g';
        document.getElementById('grasas-orson').textContent = Math.round(consumoOrson.grasa) + 'g';
        document.getElementById('grasas-maritza').textContent = Math.round(consumoMaritza.grasa) + 'g';

        const protPctOrson = Math.min(100, (consumoOrson.prot / protTargetOrson) * 100);
        const carbsPctOrson = Math.min(100, (consumoOrson.carbs / carbsTargetOrson) * 100);
        const grasasPctOrson = Math.min(100, (consumoOrson.grasa / grasasTargetOrson) * 100);
        const protPctMaritza = Math.min(100, (consumoMaritza.prot / protTargetMaritza) * 100);
        const carbsPctMaritza = Math.min(100, (consumoMaritza.carbs / carbsTargetMaritza) * 100);
        const grasasPctMaritza = Math.min(100, (consumoMaritza.grasa / grasasTargetMaritza) * 100);

        document.getElementById('barra-prot-orson').style.width = protPctOrson + '%';
        document.getElementById('barra-carbos-orson').style.width = carbsPctOrson + '%';
        document.getElementById('barra-grasas-orson').style.width = grasasPctOrson + '%';
        document.getElementById('barra-prot-maritza').style.width = protPctMaritza + '%';
        document.getElementById('barra-carbos-maritza').style.width = carbsPctMaritza + '%';
        document.getElementById('barra-grasas-maritza').style.width = grasasPctMaritza + '%';

        const totalKcal = consumoOrson.kcal + consumoMaritza.kcal;
        const totalProt = consumoOrson.prot + consumoMaritza.prot;
        const totalCarbs = consumoOrson.carbs + consumoMaritza.carbs;
        const totalGrasa = consumoOrson.grasa + consumoMaritza.grasa;
        document.getElementById('total-kcal-hoy').textContent = Math.round(totalKcal);
        document.getElementById('total-prot-hoy').textContent = totalProt.toFixed(1) + 'g';
        document.getElementById('total-carbos-hoy').textContent = totalCarbs.toFixed(1) + 'g';
        document.getElementById('total-grasas-hoy').textContent = totalGrasa.toFixed(1) + 'g';
        document.getElementById('total-azuc-hoy').textContent = '0g';
      }

      function cambiarPersona(persona) {
        document.getElementById('cons-persona').value = persona;
      }

      function mostrarQuickAdd() {
        const panel = document.getElementById('quick-add-panel');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      }

      function quickSelect(nombre, kcal, prot, carbs, grasa) {
        document.getElementById('cons-alimento').value = nombre;
        document.getElementById('cons-kcal').value = kcal;
        document.getElementById('cons-prot').value = prot;
        document.getElementById('cons-carbs').value = carbs;
        document.getElementById('cons-grasa').value = grasa;
        document.getElementById('quick-add-panel').style.display = 'none';
      }

      let refriItems = [];

      async function cargarRefriParaConsumo() {
        try {
          const res = await fetch('/api/refrigerador');
          refriItems = await res.json();
          const select = document.getElementById('cons-refri');
          select.innerHTML = '<option value="">-- Seleccionar del refrigerador --</option>';
          refriItems.forEach(item => {
            const opt = document.createElement('option');
            opt.value = item._id || item.id;
            opt.textContent = item.nombre + ' (' + (item.cantidad || 'sin cantidad') + ')';
            opt.dataset.nombre = item.nombre;
            opt.dataset.kcal = item.kcal || 0;
            opt.dataset.prot = item.proteinas || 0;
            opt.dataset.carbs = item.carbohidratos || 0;
            opt.dataset.gras = item.grasas || 0;
            select.appendChild(opt);
          });
        } catch (e) { console.error('Error cargando refri:', e); }
      }

      function seleccionarDelRefri() {
        const select = document.getElementById('cons-refri');
        const opt = select.options[select.selectedIndex];
        if (!opt || !opt.value) return;
        
        const nombre = opt.dataset.nombre;
        const kcal = parseFloat(opt.dataset.kcal) || 0;
        const prot = parseFloat(opt.dataset.prot) || 0;
        const carbs = parseFloat(opt.dataset.carbs) || 0;
        const gras = parseFloat(opt.dataset.gras) || 0;
        
        document.getElementById('cons-alimento').value = nombre;
        document.getElementById('cons-kcal').value = kcal;
        document.getElementById('cons-prot').value = prot;
        document.getElementById('cons-carbs').value = carbs;
        document.getElementById('cons-grasa').value = gras;
        
        let peso = 100;
        if (nombre.toLowerCase().includes('tortilla') && nombre.toLowerCase().includes('harina')) {
          peso = 60;
          document.getElementById('cons-piezas').value = 2;
        } else if (nombre.toLowerCase().includes('tortilla') && nombre.toLowerCase().includes('maíz')) {
          peso = 30;
          document.getElementById('cons-piezas').value = 3;
        } else if (nombre.toLowerCase().includes('pan')) {
          peso = 30;
          document.getElementById('cons-piezas').value = 2;
        } else if (nombre.toLowerCase().includes('huevo')) {
          peso = 50;
          document.getElementById('cons-piezas').value = 2;
        } else if (nombre.toLowerCase().includes('jamon') || nombre.toLowerCase().includes('jamón')) {
          peso = 30;
          document.getElementById('cons-piezas').value = 3;
        } else if (nombre.toLowerCase().includes('aguacate')) {
          peso = 150;
          document.getElementById('cons-piezas').value = 1;
        } else if (nombre.toLowerCase().includes('mango') || nombre.toLowerCase().includes('manzana') || nombre.toLowerCase().includes('pera')) {
          peso = 150;
          document.getElementById('cons-piezas').value = 1;
        } else if (nombre.toLowerCase().includes('platano') || nombre.toLowerCase().includes('plátano')) {
          peso = 120;
          document.getElementById('cons-piezas').value = 1;
        }
        
        document.getElementById('cons-peso-pieza').value = peso;
        calcularCantidad();
      }

      function calcularCantidad() {
        const piezas = parseInt(document.getElementById('cons-piezas').value) || 1;
        const pesoPieza = parseInt(document.getElementById('cons-peso-pieza').value) || 100;
        const total = piezas * pesoPieza;
        document.getElementById('cons-total-gramos').textContent = total + 'g';
        document.getElementById('cons-cantidad').value = total;
      }

      let consumoList = [];
      let consumoOrson = { kcal: 0, prot: 0, carbs: 0, grasa: 0 };
      let consumoMaritza = { kcal: 0, prot: 0, carbs: 0, grasa: 0 };
      let getOrson = 1920;
      let getMaritza = 1851;
      let lastTipo = 'comida';

      function procesarTicket() {
        const texto = document.getElementById('ticket-text').value;
        const lineas = texto.split(String.fromCharCode(10)).filter(l => l.trim());
        let agregados = 0;

        lineas.forEach(linea => {
          const match = linea.match(/([A-Za-záéíóúñÑ\s]+)[\s$]*([\d,]+\.?\d*)/i);
          if (match) {
            const nombre = match[1].trim();
            fetch('/api/refrigerador', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                nombre,
                cantidad: match[2] || '1',
                categoria: 'otros'
              })
            });
            agregados++;
          }
        });

        alert(`Se procesaron ${agregados} artículos del ticket`);
        fetchItems(currentFilter);
      }

      async function generarIdeas(tipo) {
        lastTipo = tipo;
        const list = document.getElementById('ideasList');
        list.innerHTML = '<div class="idea-card">Generando ideas...</div>';

        try {
          const fridgeRes = await fetch('/api/refrigerador');
          const fridgeItems = await fridgeRes.json();
          
          const res = await fetch('/api/recetas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo, fridgeItems })
          });
          const data = await res.json();

          list.innerHTML = data.ideas.map((idea, idx) => `
            <div class="idea-card" id="idea-${idx}" style="${idea.preparado ? 'opacity:0.6; border:2px solid #27ae60;' : ''}">
              <div style="display:flex; justify-content:space-between; align-items:start;">
                <div>
                  <h4 style="margin:0 0 0.3rem;">${idea.nombre}</h4>
                  ${idea.preparado ? '<span style="background:#27ae60; color:white; padding:0.2rem 0.5rem; border-radius:1rem; font-size:0.7rem;">✓ Digerido</span>' : ''}
                  ${idea.score > 0 ? '<span style="background:#2ecc71; color:white; padding:0.15rem 0.4rem; border-radius:1rem; font-size:0.65rem; margin-left:0.3rem;">✓ Tienes ingredientes</span>' : ''}
                </div>
                <div style="font-size:1.2rem;">${idea.urgente ? '⚠️' : '🍽️'}</div>
              </div>
              <p style="margin:0.3rem 0; font-size:0.85rem; color:var(--soft);">${idea.descripcion}</p>
              ${idea.disponibles && idea.disponibles.length > 0 ? '<div style="margin:0.3rem 0; font-size:0.75rem; color:#27ae60;"><strong>Ingredientes disponibles:</strong> ' + idea.disponibles.slice(0, 5).join(', ') + '</div>' : '<div style="margin:0.3rem 0; font-size:0.75rem; color:#e74c3c;">⚠️ Sin ingredientes del refrigerador</div>'}
              <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:center; margin-top:0.5rem;">
                <span style="background:rgba(231,76,60,0.1); padding:0.3rem 0.6rem; border-radius:0.5rem; font-size:0.75rem; font-weight:600;">
                  🔥 ${idea.kcal} kcal
                </span>
                <span style="background:rgba(52,152,219,0.1); padding:0.3rem 0.6rem; border-radius:0.5rem; font-size:0.75rem;">
                  P: ${idea.prot}g
                </span>
                <span style="background:rgba(155,89,182,0.1); padding:0.3rem 0.6rem; border-radius:0.5rem; font-size:0.75rem;">
                  C: ${idea.carb}g
                </span>
                <span style="background:rgba(39,174,96,0.1); padding:0.3rem 0.6rem; border-radius:0.5rem; font-size:0.75rem;">
                  G: ${idea.gras}g
                </span>
              </div>
              ${idea.urgente ? '<div style="color:var(--urgent); font-weight:600; font-size:0.75rem; margin-top:0.5rem;">⚠️ Usa productos próximos a caducar</div>' : ''}
              ${!idea.preparado ? `
                <div style="margin-top:0.8rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
                  <button class="btn" onclick="prepararIdea(${idx}, '${idea.nombre}', ${idea.kcal}, ${idea.prot}, ${idea.carb}, ${idea.gras})" style="padding:0.5rem 1rem; font-size:0.8rem;">
                    🍽️ Preparar y digerir
                  </button>
                  <select id="prep-persona-${idx}" style="padding:0.5rem; border-radius:0.5rem; font-size:0.8rem;">
                    <option value="orson">Para Orson</option>
                    <option value="maritza">Para Maritza</option>
                  </select>
                </div>
              ` : '<div style="margin-top:0.5rem; color:#27ae60; font-weight:600;">✓ Ya digerido por ' + (idea.preparadoPor || 'alguien') + '</div>'}
            </div>
          `).join('');
        } catch (e) {
          list.innerHTML = '<div class="idea-card">Error al generar ideas</div>';
        }
      }

      async function generarIdeasActual() {
        await generarIdeas(lastTipo);
      }

      let ideasPreparadas = [];

      function prepararIdea(idx, nombre, kcal, prot, carb, gras) {
        const persona = document.getElementById('prep-persona-' + idx).value;
        const hora = document.getElementById('idea-persona')?.value || persona;
        
        const item = {
          id: Date.now(),
          alimento: nombre,
          cantidad: 1,
          kcal: kcal,
          prot: prot,
          carbs: carb,
          grasa: gras,
          persona: persona,
          hora: hora
        };

        consumoList.push(item);
        
        if (persona === 'orson') {
          consumoOrson.kcal += item.kcal;
          consumoOrson.prot += item.prot;
          consumoOrson.carbs += item.carbs;
          consumoOrson.grasa += item.grasa;
        } else {
          consumoMaritza.kcal += item.kcal;
          consumoMaritza.prot += item.prot;
          consumoMaritza.carbs += item.carbs;
          consumoMaritza.grasa += item.grasa;
        }

        ideasPreparadas.push({ idx, nombre, persona });
        
        const card = document.getElementById('idea-' + idx);
        if (card) {
          card.style.opacity = '0.6';
          card.style.border = '2px solid #27ae60';
          card.innerHTML = card.innerHTML.replace('Preparar y digerir', '✓ Digerido');
          const btn = card.querySelector('button');
          if (btn) btn.remove();
        }

        actualizarTotalesConsumo();
        renderConsumo();
        
        alert('¡Listo! ' + nombre + ' agregado al consumo de ' + (persona === 'orson' ? 'Orson' : 'Maritza'));
      }

      loadKcalInfo();
      fetchItems();
      renderQuickButtons();
      cargarRefriParaConsumo();
    </script>
  </body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(TEMPLATE)


def calcular_tmb(peso_kg: float, altura_cm: float, edad: int, sexo: str) -> float:
    if sexo == "hombre":
        return 88.362 + (13.397 * peso_kg) + (4.799 * altura_cm) - (5.677 * edad)
    return 447.593 + (9.247 * peso_kg) + (3.098 * altura_cm) - (4.330 * edad)


@app.route("/api/kcal-info")
def kcal_info():
    return jsonify({
        "orson": {
            "tmb": calcular_tmb(70, 167, 40, "hombre"),
            "get": calcular_tmb(70, 167, 40, "hombre") * 1.2,
            "factor": 1.2,
            "peso": 70,
            "edad": 40,
            "altura": 167
        },
        "maritza": {
            "tmb": calcular_tmb(60, 157, 68, "mujer"),
            "get": calcular_tmb(60, 157, 68, "mujer") * 1.55,
            "factor": 1.55,
            "peso": 60,
            "edad": 68,
            "altura": 157
        }
    })


@app.route("/api/refrigerador", methods=["GET", "POST"])
def refrigerador():
    collection = get_collection()

    if request.method == "POST":
        data = request.get_json(force=True)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return {"error": "Es necesario un nombre."}, 400

        now = datetime.now(timezone.utc)
        categoria = data.get("categoria", "otros")

        caducidad_dias = {"frutas": 5, "verduras": 7, "carnes": 3, "lacteos": 7, "congelados": 90, "granos": 30, "legumbres": 7, "condimentos": 365, "bebidas": 180, "alacena": 365}.get(categoria, 14)

        if data.get("consumir_antes"):
            consumir_antes = data["consumir_antes"]
        else:
            consumir_antes = (now + timedelta(days=caducidad_dias)).strftime("%Y-%m-%d")

        doc = {
            "nombre": nombre,
            "cantidad": data.get("cantidad") or None,
            "categoria": categoria,
            "kcal": data.get("kcal") or 0,
            "proteinas": data.get("proteinas") or 0,
            "grasas": data.get("grasas") or 0,
            "carbohidratos": data.get("carbohidratos") or 0,
            "azucares": data.get("azucares") or 0,
            "fibra": data.get("fibra") or 0,
            "ig": data.get("ig") or 0,
            "tipo_grasa": data.get("tipo_grasa") or None,
            "calcio": data.get("calcio") or 0,
            "hierro": data.get("hierro") or 0,
            "potasio": data.get("potasio") or 0,
            "fosforo": data.get("fosforo") or 0,
            "selenio": data.get("selenio") or 0,
            "zinc": data.get("zinc") or 0,
            "magnesio": data.get("magnesio") or 0,
            "cromo": data.get("cromo") or 0,
            "consumir_antes": consumir_antes,
            "fecha_cad": data.get("fecha_cad") or None,
            "agregado_en": now,
        }

        result = collection.insert_one(doc)
        return {"ok": True, "id": str(result.inserted_id)}, 201

    categoria = request.args.get("categoria")
    
    if categoria == "todos":
        query = {"categoria": {"$ne": "alacena"}}
    elif categoria == "alacena":
        query = {"categoria": "alacena"}
    else:
        query = {"categoria": categoria} if categoria else {}
    
    rows = list(collection.find(query).sort("consumir_antes", 1 if categoria else DESCENDING))

    items = [{
        "id": str(row["_id"]),
        "nombre": row["nombre"],
        "cantidad": row.get("cantidad"),
        "categoria": row.get("categoria"),
        "kcal": row.get("kcal", 0),
        "proteinas": row.get("proteinas", 0),
        "grasas": row.get("grasas", 0),
        "carbohidratos": row.get("carbohidratos", 0),
        "azucares": row.get("azucares", 0),
        "fibra": row.get("fibra", 0),
        "ig": row.get("ig", 0),
        "tipo_grasa": row.get("tipo_grasa"),
        "consumir_antes": row.get("consumir_antes"),
    } for row in rows]

    return jsonify(items)


@app.route("/api/refrigerador/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    from bson import ObjectId
    collection = get_collection()
    collection.delete_one({"_id": ObjectId(item_id)})
    return {"ok": True}


@app.route("/api/consumo", methods=["GET", "POST"])
def api_consumo():
    consumo_col = get_consumo_collection()
    
    if request.method == "POST":
        data = request.get_json(force=True)
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        doc = {
            "fecha": hoy,
            "alimento": data.get("alimento"),
            "cantidad": data.get("cantidad"),
            "kcal": data.get("kcal"),
            "proteinas": data.get("proteinas"),
            "carbohidratos": data.get("carbohidratos"),
            "grasas": data.get("grasas"),
            "persona": data.get("persona"),
            "hora": data.get("hora"),
            "creado_en": datetime.now(timezone.utc)
        }
        
        result = consumo_col.insert_one(doc)
        return {"ok": True, "id": str(result.inserted_id)}, 201
    
    fecha = request.args.get("fecha", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    rows = list(consumo_col.find({"fecha": fecha}).sort("creado_en", 1))
    
    items = [{
        "id": str(row["_id"]),
        "alimento": row.get("alimento"),
        "cantidad": row.get("cantidad"),
        "kcal": row.get("kcal", 0),
        "proteinas": row.get("proteinas", 0),
        "carbohidratos": row.get("carbohidratos", 0),
        "grasas": row.get("grasas", 0),
        "persona": row.get("persona"),
        "hora": row.get("hora"),
    } for row in rows]
    
    totals = {"orson": {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0},
              "maritza": {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}
    
    for item in items:
        p = item.get("persona", "orson")
        if p in totals:
            totals[p]["kcal"] += item.get("kcal", 0)
            totals[p]["proteinas"] += item.get("proteinas", 0)
            totals[p]["carbohidratos"] += item.get("carbohidratos", 0)
            totals[p]["grasas"] += item.get("grasas", 0)
    
    return jsonify({"items": items, "totals": totals, "fecha": fecha})


@app.route("/api/consumo/<record_id>", methods=["DELETE"])
def delete_consumo(record_id):
    from bson import ObjectId
    consumo_col = get_consumo_collection()
    consumo_col.delete_one({"_id": ObjectId(record_id)})
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


@app.route("/api/consumo/historial", methods=["GET"])
def consumo_historial():
    consumo_col = get_consumo_collection()
    dias = request.args.get("dias", 7, type=int)
    fecha_inicio = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
    
    rows = list(consumo_col.find({"fecha": {"$gte": fecha_inicio}}).sort("fecha", 1))
    
    diarios = {}
    for row in rows:
        fecha = row.get("fecha")
        persona = row.get("persona", "orson")
        if fecha not in diarios:
            diarios[fecha] = {"orson": {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0},
                             "maritza": {"kcal": 0, "proteinas": 0, "carbohidratos": 0, "grasas": 0}}
        if persona in diarios[fecha]:
            diarios[fecha][persona]["kcal"] += row.get("kcal", 0)
            diarios[fecha][persona]["proteinas"] += row.get("proteinas", 0)
            diarios[fecha][persona]["carbohidratos"] += row.get("carbohidratos", 0)
            diarios[fecha][persona]["grasas"] += row.get("grasas", 0)
    
    return jsonify({"historial": diarios, "dias": dias})


@app.route("/api/consumo/estadisticas", methods=["GET"])
def consumo_estadisticas():
    consumo_col = get_consumo_collection()
    dias = request.args.get("dias", 30, type=int)
    fecha_inicio = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
    
    pipeline = [
        {"$match": {"fecha": {"$gte": fecha_inicio}}},
        {"$group": {
            "_id": {"persona": "$persona", "fecha": "$fecha"},
            "kcal": {"$sum": "$kcal"},
            "proteinas": {"$sum": "$proteinas"},
            "carbohidratos": {"$sum": "$carbohidratos"},
            "grasas": {"$sum": "$grasas"}
        }},
        {"$sort": {"_id.fecha": 1}}
    ]
    
    resultados = list(consumo_col.aggregate(pipeline))
    
    stats = {"orson": {"promedio_kcal": 0, "dias": 0, "total_kcal": 0, "total_prot": 0, "total_carb": 0, "total_gras": 0},
             "maritza": {"promedio_kcal": 0, "dias": 0, "total_kcal": 0, "total_prot": 0, "total_carb": 0, "total_gras": 0}}
    
    for r in resultados:
        p = r["_id"]["persona"]
        if p in stats:
            stats[p]["dias"] += 1
            stats[p]["total_kcal"] += r["kcal"]
            stats[p]["total_prot"] += r["proteinas"]
            stats[p]["total_carb"] += r["carbohidratos"]
            stats[p]["total_gras"] += r["grasas"]
    
    for p in stats:
        if stats[p]["dias"] > 0:
            stats[p]["promedio_kcal"] = round(stats[p]["total_kcal"] / stats[p]["dias"], 1)
            stats[p]["promedio_prot"] = round(stats[p]["total_prot"] / stats[p]["dias"], 1)
            stats[p]["promedio_carb"] = round(stats[p]["total_carb"] / stats[p]["dias"], 1)
            stats[p]["promedio_gras"] = round(stats[p]["total_gras"] / stats[p]["dias"], 1)
    
    return jsonify({"estadisticas": stats, "periodo_dias": dias})


@app.route("/api/refrigerador/en-cero", methods=["GET"])
def items_en_cero():
    collection = get_collection()
    query = request.args.get("categoria")
    if query and query != "todos":
        rows = list(collection.find({"categoria": query}).sort("nombre", 1))
    else:
        rows = list(collection.find({}).sort("nombre", 1))
    
    items = []
    for row in rows:
        cantidad_str = row.get("cantidad", "0")
        try:
            cantidad_num = float(cantidad_str.split()[0]) if cantidad_str else 0
        except:
            cantidad_num = 0
        items.append({
            "id": str(row["_id"]),
            "nombre": row["nombre"],
            "cantidad": row.get("cantidad"),
            "cantidad_num": cantidad_num,
            "categoria": row.get("categoria"),
            "kcal": row.get("kcal", 0),
            "proteinas": row.get("proteinas", 0),
            "grasas": row.get("grasas", 0),
            "carbohidratos": row.get("carbohidratos", 0),
            "azucares": row.get("azucares", 0),
            "fibra": row.get("fibra", 0),
            "ig": row.get("ig", 0),
            "consumir_antes": row.get("consumir_antes"),
        })
    
    items.sort(key=lambda x: x["cantidad_num"])
    return jsonify(items)


@app.route("/api/refrigerador/<item_id>", methods=["PUT"])
def update_item(item_id):
    from bson import ObjectId
    collection = get_collection()
    data = request.get_json(force=True)
    update_data = {}
    for key in ["nombre", "cantidad", "categoria", "kcal", "proteinas", "grasas", "carbohidratos", "azucares", "fibra", "ig", "consumir_antes"]:
        if key in data:
            update_data[key] = data[key]
    collection.update_one({"_id": ObjectId(item_id)}, {"$set": update_data})
    return {"ok": True}


@app.route("/api/refrigerador/<item_id>/consumir", methods=["POST"])
def consumir_item(item_id):
    from bson import ObjectId
    collection = get_collection()
    data = request.get_json(force=True) or {}
    cantidad = data.get("cantidad", 1)
    
    item = collection.find_one({"_id": ObjectId(item_id)})
    if not item:
        return {"error": "Item no encontrado"}, 404
    
    consumo_col = get_consumo_collection()
    ahora = datetime.now(timezone.utc)
    hoy = ahora.strftime("%Y-%m-%d")
    
    consumo_doc = {
        "fecha": hoy,
        "alimento": item.get("nombre"),
        "cantidad": cantidad,
        "kcal": (item.get("kcal", 0) / 100) * cantidad,
        "proteinas": (item.get("proteinas", 0) / 100) * cantidad,
        "carbohidratos": (item.get("carbohidratos", 0) / 100) * cantidad,
        "grasas": (item.get("grasas", 0) / 100) * cantidad,
        "persona": data.get("persona", "orson"),
        "hora": data.get("hora", "comida"),
        "de_refri": True,
        "item_id": item_id,
        "creado_en": ahora
    }
    
    consumo_col.insert_one(consumo_doc)
    return {"ok": True}
    
    return {"ok": True}


INGREDIENT_MAP = {
    "huevo": ["huevo", "huevos"],
    "jamon": ["jamon", "jamón"],
    "pollo": ["pollo"],
    "res": ["res", "bistec", "carne"],
    "cerdo": ["cerdo", "costilla", "chicharron", "chicharrón"],
    "atun": ["atun", "atún"],
    "tortilla": ["tortilla", "tortillas"],
    "frijol": ["frijol", "frijoles"],
    "arroz": ["arroz"],
    "pan": ["pan"],
    "queso": ["queso", "quesos"],
    "aguacate": ["aguacate", "guacamole"],
    "jitomate": ["jitomate", "tomate", "salsa"],
    "cebolla": ["cebolla"],
    "lechuga": ["lechuga"],
    "aguacate": ["aguacate"],
    "platano": ["platano", "plátano"],
    "mango": ["mango"],
    "fresa": ["fresa", "fresas"],
    "uva": ["uva", "uvas"],
    "manzana": ["manzana"],
    "naranja": ["naranja"],
    "yogur": ["yogur", "yoghurt"],
    "leche": ["leche"],
    "miel": ["miel"],
    "mantequilla": ["mantequilla"],
    "crema": ["crema"],
    "elote": ["elote"],
    "calabaza": ["calabaza"],
    "zanahoria": ["zanahoria"],
    "brocoli": ["brocoli", "brócoli"],
    "espinaca": ["espinaca", "espinacas"],
    "pimiento": ["pimiento", "pimenton"],
    "papa": ["papa", "patata"],
    "pasta": ["pasta"],
    "lenteja": ["lenteja", "lentejas"],
    "nopal": ["nopal"],
    "chipotle": ["chipotle", "chipotles"],
    "salchicha": ["salchicha"],
}

def get_ingredient_key(nombre: str) -> str | None:
    nombre_lower = nombre.lower()
    for key, aliases in INGREDIENT_MAP.items():
        for alias in aliases:
            if alias in nombre_lower:
                return key
    return None

@app.route("/api/recetas", methods=["POST"])
def recetas():
    data = request.get_json(force=True)
    tipo = data.get("tipo", "comida")
    fridge_items = data.get("fridgeItems", [])

    ahora = datetime.now(timezone.utc)
    
    urgente = []
    otros = []
    fridge_names_lower = []
    fridge_by_key = {}
    
    for item in fridge_items:
        nombre = item.get("nombre", "")
        fridge_names_lower.append(nombre.lower())
        key = get_ingredient_key(nombre)
        if key:
            if key not in fridge_by_key:
                fridge_by_key[key] = []
            fridge_by_key[key].append(nombre)
        
        cad = item.get("consumir_antes")
        if cad:
            try:
                cad_date = datetime.strptime(cad, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                dias_restantes = (cad_date - ahora).days
                if dias_restantes <= 5:
                    urgente.append((item, dias_restantes))
                else:
                    otros.append((item, dias_restantes))
            except (ValueError, TypeError):
                pass
    
    urgente.sort(key=lambda x: x[1])
    otros.sort(key=lambda x: x[1])
    
    nombres_urgentes = [i[0]["nombre"] for i in urgente[:8]]
    nombres_otros = [i[0]["nombre"] for i in otros[:10]]
    urgente_keys = set(get_ingredient_key(n) for n in nombres_urgentes if get_ingredient_key(n))

    recetas_db = {
        "desayuno": [
            ("Huevos con jamón", ["huevo", "jamon"], "Huevos revueltos con jamón del refrigerador, sirve con tortillas.", 380, 25, 22, 8, 15),
            ("Huevos divorciados", ["huevo", "frijol"], "Huevos fritos con salsa verde y roja, frijoles y tortillas.", 450, 28, 24, 35, 45),
            ("Huevos rancheros", ["huevo", "frijol", "tortilla"], "Huevos sobre tortilla frita con salsa ranchera, frijoles y queso.", 480, 26, 28, 40, 50),
            ("Omelette con verduras", ["huevo", "jitomate"], "Omelette con espinacas, jitomate, queso y hierbas.", 320, 22, 20, 12, 15),
            ("Huevos tibios con jamón", ["huevo", "jamon", "pan"], "Huevos pochados con jamón, pan tostado y aguacate.", 420, 30, 26, 25, 20),
            ("Tortillas con frijoles", ["tortilla", "frijol"], "Tortillas de maíz con frijoles refritos, queso fresco y salsa.", 420, 18, 16, 50, 52),
            ("Molletes", ["pan", "frijol", "queso"], "Bolillos con frijoles, queso fundido y salsa.", 450, 20, 18, 55, 60),
            ("Chilaquiles verdes", ["tortilla", "crema"], "Tortillas fritas con salsa verde, crema, queso y cebolla.", 480, 22, 24, 45, 55),
            ("Chilaquiles rojos", ["tortilla", "pollo", "crema"], "Tortillas fritas con salsa roja, crema, queso y pollo deshebrado.", 520, 30, 26, 42, 52),
            ("Enfrijoladas", ["tortilla", "frijol", "crema"], "Tortillas mojadas en caldo de frijoles con queso y crema.", 400, 18, 16, 45, 50),
            ("Panqueques con fruta", ["platano", "miel", "mantequilla"], "Panqueques fluffy con plátano, miel y mantequilla.", 380, 12, 14, 52, 65),
            ("Frutas con yogur", ["yogur"], "Frutas del refrigerador picadas con yogur natural y granola.", 200, 8, 6, 30, 35),
            ("Pan con aguacate", ["pan", "aguacate"], "Pan integral con aguacate machacado, sal, limón y aceite de oliva.", 290, 8, 16, 28, 15),
            ("Avena con frutas", ["platano", "miel"], "Avena cocida con plátano, fresas y miel.", 280, 10, 8, 45, 40),
            ("Yogur con frutas y miel", ["yogur", "mango"], "Yogur natural con mango, uvas y un toque de miel.", 220, 9, 7, 35, 38),
            ("Hot cakes con jamón", ["huevo", "jamon"], "Hot cakes fluffy con jamón y queso.", 450, 24, 18, 55, 58),
            ("Sándwich de jamón", ["pan", "jamon", "jitomate", "lechuga"], "Pan integral con jamón, queso, lechuga y jitomate.", 320, 18, 12, 35, 30),
            ("Licuado de frutas", ["leche", "platano", "mango", "miel"], "Leche con plátano, mango y miel.", 250, 10, 8, 40, 45),
            ("Tostadas francesas", ["huevo", "pan", "mantequilla"], "Pan francés empapado en huevo, freído con mantequilla y syrup.", 420, 14, 22, 45, 55),
            ("Quesadillas de queso", ["tortilla", "queso"], "Tortillas de harina con queso Oaxaca fundido.", 380, 18, 18, 35, 55),
            ("Huevos con salchicha", ["huevo", "salchicha"], "Huevos revueltos con salchicha y tortillas.", 420, 22, 24, 20, 35),
            ("Yogur con granola", ["yogur", "platano"], "Yogur natural con granola, miel y plátano.", 220, 10, 8, 35, 38),
        ],
        "comida": [
            ("Tacos de res", ["res", "tortilla"], "Tortillas con res molida, cebolla, cilantro y salsa verde.", 450, 28, 22, 38, 52),
            ("Albondigas con salsa", ["res"], "Albóndigas de res en caldo con verduras, arroz blanco.", 480, 32, 24, 30, 35),
            ("Picadillo de res", ["res", "papa", "zanahoria"], "Res molida con papa, zanahoria, chícharro y aceitunas.", 420, 28, 22, 35, 40),
            ("Carne en su jugo", ["res", "arroz"], "Res cocida con nabos, chayote, cilantro y arroz.", 450, 35, 20, 25, 30),
            ("Milanesa con arroz", ["res", "arroz"], "Milanesa empanizada con arroz blanco y ensalada.", 550, 35, 28, 45, 50),
            ("Milanesa con puré", ["res", "papa"], "Milanesa empanizada con puré de papa cremoso.", 580, 32, 30, 48, 55),
            ("Bistec a la mexicana", ["res", "jitomate"], "Bistec con jitomate, cebolla, chile y arroz.", 420, 30, 18, 25, 35),
            ("Chiles rellenos", ["jitomate"], "Chiles poblanos rellenos de res, bañados en salsa de tomate.", 480, 28, 24, 40, 45),
            ("Enchiladas de res", ["tortilla", "res"], "Tortillas con res deshebrada, bañadas en salsa roja y queso.", 520, 32, 26, 42, 52),
            ("Enchiladas verdes", ["tortilla", "pollo", "crema"], "Tortillas con pollo deshebrado, salsa verde, crema y queso.", 480, 30, 24, 38, 48),
            ("Enchiladas suizas", ["tortilla", "pollo", "crema"], "Tortillas con pollo, salsa verde, crema y queso gratinado.", 520, 32, 28, 35, 50),
            ("Tamales de res", ["tortilla", "res"], "Masa con res deshebrada en salsa roja, envueltos en hoja.", 450, 25, 20, 50, 55),
            ("Pechuga empanizada", ["pollo", "arroz"], "Pechuga de pollo empanizada con arroz y ensalada.", 480, 40, 18, 35, 40),
            ("Pechuga a la plancha", ["pollo"], "Pechuga de pollo a la plancha con calabacitas y arroz.", 380, 42, 8, 15, 15),
            ("Pollo en crema", ["pollo", "crema", "elote", "arroz"], "Pollo deshebrado en crema de elote con arroz.", 450, 35, 22, 25, 35),
            ("Pollo con verduras", ["pollo"], "Pollo salteado con brócoli, zanahoria y pimiento.", 380, 38, 12, 20, 20),
            ("Mole de pollo", ["pollo", "tortilla", "arroz"], "Pollo en mole poblano con arroz y tortillas.", 550, 35, 28, 45, 40),
            ("Pozole rojo", ["pollo", "tortilla"], "Caldo de maíz pozolero con pollo, rábanos, lechuga y oregano.", 380, 28, 14, 45, 35),
            ("Sopa de tortilla", ["pollo", "tortilla", "aguacate"], "Caldo con chilaquiles, pollo deshebrado y aguacate.", 350, 22, 16, 30, 40),
            ("Ensalada César", ["lechuga", "pollo", "queso"], "Lechuga romana, pollo, queso parmesano, crutones y aderezo César.", 380, 32, 20, 18, 20),
            ("Ensalada del chef", ["lechuga", "jamon", "huevo"], "Lechuga, jamón, queso, huevo, aceitunas y aderezo.", 350, 25, 22, 15, 25),
            ("Ceviche de atún", ["atun", "cebolla", "aguacate"], "Atún fresco con cebolla morada, cilantro, limón y aguacate.", 280, 35, 8, 15, 25),
            ("Tacos de pescado", ["tortilla", "jitomate"], "Tortillas con pescado empanizado, ensalada y salsa.", 420, 28, 18, 40, 45),
            ("Burrito bowl", ["arroz", "frijol", "pollo", "aguacate"], "Arroz, frijoles, pollo deshebrado, aguacate y verduras.", 520, 35, 18, 55, 30),
            ("Guisado de cerdo", ["cerdo"], "Cerdo guisado con calabaza, elote y chícharros, tortillas.", 480, 32, 24, 30, 35),
            ("Costillas en salsa", ["cerdo", "arroz", "frijol"], "Costillas de cerdo en salsa roja con arroz y frijoles.", 550, 35, 32, 35, 40),
            ("Pechuga asada", ["pollo", "nopal", "arroz", "tortilla"], "Pechuga de pollo asada con nopales, arroz y tortillas.", 420, 40, 14, 25, 25),
            ("Arrachera con guacamole", ["res", "tortilla", "aguacate"], "Carne asada con tortillas, guacamole, cebolla y cilantro.", 500, 38, 28, 30, 35),
            ("Fajitas de res", ["res", "pimiento", "tortilla"], "Res asada con pimientos, cebolla, tortillas y salsa.", 480, 35, 22, 35, 40),
        ],
        "cena": [
            ("Sopa de verduras", [], "Caldo con calabaza, zanahoria, chayote y hierbabuena.", 180, 6, 4, 30, 35),
            ("Sopa de pollo", ["pollo"], "Caldo de pollo con verduras, arroz y cilantro.", 250, 18, 10, 25, 30),
            ("Sopa de lentejas", ["lenteja"], "Lentejas con verduras, laurel y aceite de oliva.", 280, 15, 8, 42, 25),
            ("Sopa de pasta", ["pasta"], "Caldo con pasta, verduras y queso parmesano.", 260, 12, 10, 35, 40),
            ("Crema de elote", ["elote"], "Crema suave de elote con crutones y queso.", 220, 10, 12, 25, 40),
            ("Enchiladas rápidas", ["tortilla"], "Tortillas con restos del guiso, bañadas en salsa.", 400, 22, 18, 40, 52),
            ("Quesadillas", ["tortilla", "queso"], "Tortillas de harina con queso fundido y verduras.", 350, 15, 18, 35, 55),
            ("Tortilla española", ["huevo", "papa"], "Tortilla de huevos con papa y cebolla, ensalada verde.", 350, 14, 20, 30, 50),
            ("Ensalada de atún", ["atun", "lechuga", "jitomate"], "Atún con lechuga, jitomate, cebolla y aderezo.", 280, 32, 12, 10, 15),
            ("Pasta con atún", ["pasta", "atun", "jitomate"], "Pasta con salsa de atún, aceitunas y jitomate.", 420, 25, 16, 50, 45),
            ("Pasta carbonara", ["pasta", "huevo", "queso"], "Pasta con huevo, queso parmesano, tocino y crema.", 520, 22, 28, 45, 50),
            ("Pasta con verduras", ["pasta", "pimiento"], "Pasta integral con calabacín, pimiento y aceite de oliva.", 380, 12, 14, 55, 45),
            ("Tacos de bistec", ["res", "tortilla"], "Tortillas con bistec, cebolla, cilantro y salsa.", 380, 28, 16, 30, 45),
            ("Hot dogs", ["pan", "salchicha"], "Pan con salchicha, mostaza, catsup y cebolla.", 380, 14, 20, 35, 55),
            ("Pizza casera", ["pan", "queso", "jamon", "jitomate"], "Pan pizza con salsa, queso, jamón y verduras.", 450, 20, 18, 50, 60),
            ("Pechuga deshebrada", ["pollo", "arroz"], "Pechuga deshebrada con arroz y ensalada.", 350, 35, 10, 25, 30),
            ("Huevo hilado", ["huevo"], "Huevos cocidos picados con mayonesa, mostaza y paprika.", 280, 18, 22, 5, 10),
            ("Tostadas de frijol", ["tortilla", "frijol", "crema"], "Tostadas con frijoles, queso, crema y salsa.", 350, 14, 16, 40, 50),
            ("Croquetas de jamón", ["jamon", "huevo"], "Croquetas crujientes de jamón con salsa de tomate.", 380, 18, 20, 30, 45),
            ("Caldo de frijoles", ["frijol", "queso"], "Caldo espeso de frijoles con queso y chiles toreados.", 320, 16, 12, 45, 35),
        ],
        "snack": [
            ("Frutas picadas", [], "Frutas del refrigerador en cubos.", 120, 2, 1, 25, 40),
            ("Queso con galletas", ["queso"], "Queso panela en cubos con totopos o galletas.", 250, 10, 15, 20, 45),
            ("Verduras con aderezo", ["zanahoria"], "Palitos de zanahoria, apio y pimiento con hummus.", 150, 3, 12, 10, 15),
            ("Yogur con granola", ["yogur", "platano"], "Yogur natural con granola, miel y frutas.", 200, 8, 6, 30, 35),
            ("Pan con queso", ["pan", "queso"], "Pan integral con queso Monterrey fundido.", 280, 12, 14, 30, 50),
            ("Guacamole con totopos", ["aguacate"], "Aguacate machacado con cebolla, cilantro y totopos.", 200, 4, 16, 12, 15),
            ("Palitos de queso", ["queso"], "Queso fundido en bastones empanizados.", 320, 14, 20, 18, 35),
            ("Gelatina de frutas", [], "Gelatina con trozos de fruta fresca.", 150, 3, 2, 30, 45),
            ("Café con pan", ["pan"], "Café con leche y pan dulce.", 200, 6, 8, 28, 50),
            ("Sándwich rápido", ["pan", "jamon", "queso", "lechuga"], "Pan con jamón, queso y lechuga.", 280, 14, 12, 30, 45),
            ("Nopales con queso", ["nopal", "queso"], "Nopales asados con queso y salsa verde.", 180, 8, 10, 10, 15),
            ("Chiles toreados", ["chipotle"], "Chiles jalapeños fritos con queso y tocino.", 280, 10, 22, 12, 20),
            ("Ceviche rápido", ["jitomate", "aguacate"], "Jitomate, aguacate y cebolla con limón y cilantro.", 150, 4, 10, 15, 20),
            ("Sopes", ["tortilla", "frijol", "crema", "queso"], "Masa frita con frijoles, queso, crema y salsa.", 350, 12, 18, 40, 55),
            ("Esquites", ["elote"], "Elote cocido con mayonesa, queso y chile.", 220, 8, 14, 25, 45),
        ],
        "rapida": [
            ("Tacos express", ["tortilla", "frijol", "queso"], "Tortillas con frijoles, queso y salsa en 5 minutos.", 320, 14, 14, 38, 50),
            ("Omelette express", ["huevo", "queso", "jamon"], "Huevos batidos con queso y jamón en microondas.", 280, 18, 18, 8, 15),
            ("Sándwich calientito", ["pan", "queso", "jamon"], "Pan con queso y jamón gratinado.", 300, 16, 14, 28, 50),
            ("Pasta rápida", ["pasta"], "Pasta con mantequilla, ajo y queso.", 380, 12, 16, 45, 55),
            ("Arroz con huevo", ["arroz", "huevo"], "Arroz frito con huevo revuelto.", 350, 14, 16, 42, 60),
            ("Tostadas rápidas", ["tortilla", "frijol", "aguacate"], "Tostadas con frijoles y aguacate.", 280, 10, 12, 35, 50),
            ("Hot dog express", ["pan", "salchicha"], "Pan con salchicha, mostaza y catsup.", 320, 12, 18, 30, 55),
            ("Tortilla con queso", ["tortilla", "queso"], "Tortilla de harina con queso fundido.", 250, 10, 12, 28, 55),
        ],
        "saludable": [
            ("Ensalada verde", ["lechuga", "aguacate"], "Lechuga, espinaca, pepino, aguacate y aderezo ligero.", 220, 8, 16, 15, 15),
            ("Pechuga a la plancha", ["pollo", "brocoli"], "Pechuga con brócoli al vapor y arroz integral.", 350, 38, 10, 25, 25),
            ("Salmón con verduras", [], "Filete de salmón con espárragos y papa al horno.", 420, 35, 22, 20, 20),
            ("Bowl de quinoa", ["frijol"], "Quinoa con verduras roast eadas, garbanzos y tahini.", 380, 15, 14, 50, 35),
            ("Smoothie verde", ["espinaca", "platano", "mango", "leche"], "Espinacas, plátano, mango y leche de almendras.", 180, 6, 4, 32, 40),
            ("Avena overnight", ["platano", "miel"], "Avena remojada con semillas, frutas y miel.", 280, 10, 8, 45, 40),
            ("Tostada de aguacate", ["pan", "aguacate", "huevo"], "Pan integral con aguacate, huevo pochado y semillas.", 320, 14, 18, 28, 15),
            ("Wrap de pollo", ["tortilla", "pollo"], "Tortilla integral con pollo, verduras y hummus.", 320, 28, 12, 30, 30),
        ],
        "casera": [
            ("Pechuga empanizada casera", ["pollo", "arroz", "frijol"], "Pechuga crujiente con arroz, frijoles y ensalada.", 520, 38, 24, 45, 50),
            ("Mole de olla", ["res"], "Carne de res con verduras en caldo espeso, tortillas.", 480, 35, 22, 35, 40),
            ("Pechuga entomatada", ["pollo", "jitomate"], "Pollo en salsa de tomate con arroz y ensalada.", 420, 36, 16, 25, 35),
            ("Carne con papa", ["res", "papa", "zanahoria"], "Carne guisada con papas, zanahoria y chícharro.", 480, 32, 24, 30, 35),
            ("Pollo con arroz", ["pollo", "arroz"], "Pollo hervido con arroz, verduras y caldo.", 400, 35, 14, 35, 40),
            ("Chicharron en salsa verde", ["cerdo", "tortilla", "arroz", "frijol"], "Chicharrón con salsa verde, arroz y frijoles.", 520, 28, 32, 30, 35),
            ("Lengua en salsa verde", ["tortilla", "arroz"], "Lengua cocida en salsa verde con arroz y tortillas.", 380, 30, 18, 20, 25),
            ("Menudo", ["res"], "Caldo de res con garbanzos, cebolla y oregano.", 350, 28, 14, 40, 35),
            ("Cordero con nopales", ["nopal", "arroz", "tortilla"], "Cordero asado con nopales, arroz y tortillas.", 480, 35, 26, 25, 30),
        ]
    }

    candidatos = recetas_db.get(tipo, recetas_db["comida"])
    ideas = []
    tiene_urgente = len(nombres_urgentes) > 0

    def score_recipe(ingredients: list) -> tuple[int, list]:
        score = 0
        matched = []
        for ing in ingredients:
            if ing in fridge_by_key:
                score += 2
                matched.extend(fridge_by_key[ing])
                if ing in urgente_keys:
                    score += 3
        return score, matched

    scored_recetas = []
    for item in candidatos:
        if len(item) == 8:
            nombre, ingredients, desc, kcal, prot, gras, carb, ig = item
        else:
            nombre, desc, kcal, prot, gras, carb, ig = item
            ingredients = []
        
        recipe_score, matched_ingredients = score_recipe(ingredients)
        scored_recetas.append({
            "nombre": nombre,
            "desc": desc,
            "kcal": kcal,
            "prot": prot,
            "gras": gras,
            "carb": carb,
            "ig": ig,
            "score": recipe_score,
            "matched": matched_ingredients,
            "ingredients": ingredients
        })

    scored_recetas.sort(key=lambda x: (-x["score"], random.random()))
    selected = scored_recetas[:6]

    for item in selected:
        desc_urgente = item["desc"]
        for nom in nombres_urgentes[:5]:
            if nom.lower() in desc_urgente.lower():
                desc_urgente = desc_urgente.replace(nom, nom + " (del refri)")
        
        matched_text = ""
        if item["matched"]:
            unique_matched = list(dict.fromkeys(item["matched"]))
            matched_text = " (Tienes: " + ", ".join(unique_matched[:4]) + ")"
        
        ideas.append({
            "nombre": item["nombre"],
            "descripcion": desc_urgente + matched_text,
            "kcal": item["kcal"],
            "prot": item["prot"],
            "gras": item["gras"],
            "carb": item["carb"],
            "ig": item["ig"],
            "urgente": tiene_urgente,
            "score": item["score"],
            "disponibles": item["matched"]
        })

    return {"ideas": ideas}


@app.route("/api/seed", methods=["POST"])
def seed_data():
    collection = get_collection()
    if collection.count_documents({}) > 0:
        collection.delete_many({})

    now = datetime.now(timezone.utc)
    items = [
        {"nombre": "Pastel de queso con frambuesa", "cantidad": "1/2 pastel (Costco)", "categoria": "lacteos", "kcal": 320, "proteinas": 6, "grasas": 18, "carbohidratos": 35, "azucares": 25, "fibra": 0, "ig": 45, "consumir_antes": (now + timedelta(days=5)).strftime("%Y-%m-%d")},
        {"nombre": "Lechuga", "cantidad": "1 cabeza", "categoria": "verduras", "kcal": 15, "proteinas": 1.4, "grasas": 0.2, "carbohidratos": 3, "azucares": 1, "fibra": 1.3, "ig": 10, "consumir_antes": (now + timedelta(days=7)).strftime("%Y-%m-%d")},
        {"nombre": "Jitomate", "cantidad": "2 piezas", "categoria": "verduras", "kcal": 18, "proteinas": 0.9, "grasas": 0.2, "carbohidratos": 4, "azucares": 2.5, "fibra": 1.2, "ig": 15, "consumir_antes": (now + timedelta(days=4)).strftime("%Y-%m-%d")},
        {"nombre": "Salchichas de res", "cantidad": "3 piezas", "categoria": "carnes", "kcal": 290, "proteinas": 12, "grasas": 25, "carbohidratos": 2, "azucares": 1, "fibra": 0, "ig": 0, "consumir_antes": (now + timedelta(days=3)).strftime("%Y-%m-%d")},
        {"nombre": "Guiso de cerdo con calabaza y elote", "cantidad": "330g (enlatado)", "categoria": "carnes", "kcal": 150, "proteinas": 12, "grasas": 8, "carbohidratos": 12, "azucares": 3, "fibra": 2, "ig": 45, "consumir_antes": (now + timedelta(days=2)).strftime("%Y-%m-%d")},
        {"nombre": "Tortillas de harina integral", "cantidad": "14 piezas", "categoria": "granos", "kcal": 290, "proteinas": 8, "grasas": 7, "carbohidratos": 48, "azucares": 2, "fibra": 6, "ig": 55, "consumir_antes": (now + timedelta(days=14)).strftime("%Y-%m-%d")},
        {"nombre": "Tortillas de harina blanca", "cantidad": "29 piezas", "categoria": "granos", "kcal": 304, "proteinas": 8, "grasas": 8, "carbohidratos": 50, "azucares": 2, "fibra": 2, "ig": 68, "consumir_antes": (now + timedelta(days=14)).strftime("%Y-%m-%d")},
        {"nombre": "Tortillas de maíz", "cantidad": "500g", "categoria": "granos", "kcal": 218, "proteinas": 5.7, "grasas": 2.8, "carbohidratos": 45, "azucares": 0.5, "fibra": 6, "ig": 52, "consumir_antes": (now + timedelta(days=10)).strftime("%Y-%m-%d")},
        {"nombre": "Jamón", "cantidad": "400g", "categoria": "carnes", "kcal": 145, "proteinas": 21, "grasas": 6, "carbohidratos": 1.5, "azucares": 1, "fibra": 0, "ig": 0, "consumir_antes": (now + timedelta(days=3)).strftime("%Y-%m-%d")},
        {"nombre": "Pan Bimbo integral", "cantidad": "4 rebanadas", "categoria": "granos", "kcal": 240, "proteinas": 9, "grasas": 3, "carbohidratos": 42, "azucares": 6, "fibra": 6, "ig": 55, "consumir_antes": (now + timedelta(days=10)).strftime("%Y-%m-%d")},
        {"nombre": "Totopos", "cantidad": "500g", "categoria": "granos", "kcal": 489, "proteinas": 7, "grasas": 25, "carbohidratos": 60, "azucares": 1, "fibra": 4, "ig": 55, "consumir_antes": (now + timedelta(days=60)).strftime("%Y-%m-%d")},
        {"nombre": "Mayonesa", "cantidad": "1kg", "categoria": "condimentos", "kcal": 680, "proteinas": 1, "grasas": 75, "carbohidratos": 1, "azucares": 0, "fibra": 0, "ig": 0, "consumir_antes": (now + timedelta(days=180)).strftime("%Y-%m-%d")},
        {"nombre": "Catsup", "cantidad": "49g", "categoria": "condimentos", "kcal": 112, "proteinas": 1.7, "grasas": 0.1, "carbohidratos": 27, "azucares": 22, "fibra": 0.5, "ig": 50, "consumir_antes": (now + timedelta(days=365)).strftime("%Y-%m-%d")},
        {"nombre": "Mostaza", "cantidad": "399g", "categoria": "condimentos", "kcal": 66, "proteinas": 4, "grasas": 4, "carbohidratos": 5, "azucares": 2, "fibra": 3, "ig": 15, "consumir_antes": (now + timedelta(days=365)).strftime("%Y-%m-%d")},
        {"nombre": "Chipotles", "cantidad": "1 lata (399g)", "categoria": "condimentos", "kcal": 40, "proteinas": 2, "grasas": 1, "carbohidratos": 7, "azucares": 5, "fibra": 2, "ig": 30, "consumir_antes": (now + timedelta(days=4)).strftime("%Y-%m-%d")},
        {"nombre": "Queso Monterrey", "cantidad": "200g", "categoria": "lacteos", "kcal": 350, "proteinas": 25, "grasas": 28, "carbohidratos": 1, "azucares": 0, "fibra": 0, "ig": 0, "consumir_antes": (now + timedelta(days=14)).strftime("%Y-%m-%d")},
        {"nombre": "Chicharrón de cachete", "cantidad": "500g", "categoria": "carnes", "kcal": 550, "proteinas": 35, "grasas": 45, "carbohidratos": 0, "azucares": 0, "fibra": 0, "ig": 0, "consumir_antes": (now + timedelta(days=60)).strftime("%Y-%m-%d")},
        {"nombre": "Pechuga de pollo", "cantidad": "400g (congelada)", "categoria": "congelados", "kcal": 120, "proteinas": 23, "grasas": 2.5, "carbohidratos": 0, "azucares": 0, "fibra": 0, "ig": 0, "consumir_antes": (now + timedelta(days=90)).strftime("%Y-%m-%d")},
        {"nombre": "Coca-Cola 2L", "cantidad": "1 pieza", "categoria": "bebidas", "kcal": 42, "proteinas": 0, "grasas": 0, "carbohidratos": 11, "azucares": 11, "fibra": 0, "ig": 63, "consumir_antes": (now + timedelta(days=180)).strftime("%Y-%m-%d")},
        {"nombre": "Frijoles refritos", "cantidad": "400g", "categoria": "legumbres", "kcal": 78, "proteinas": 5, "grasas": 0.4, "carbohidratos": 14, "azucares": 0.3, "fibra": 6.5, "ig": 30, "consumir_antes": (now + timedelta(days=7)).strftime("%Y-%m-%d")},
    ]

    collection.insert_many(items)
    return {"ok": True, "inserted": len(items)}


if __name__ == "__main__":
    app.run("0.0.0.0", port=8000, debug=True)
