# FrigoNinja - Inventario del Hogar

Sistema de inventario del hogar para Orson y Maritza.

## Características
- **Refrigerador**: Frutas, verduras, lácteos, carnes
- **Alacena**: Artículos de limpieza y hogar
- **Despensa**: Granos, latas, snacks
- **Por Comprar**: Lista automática de artículos agotados
- **Calorías**: Registro de consumo diario con metas personalizadas

## Tech Stack
- Flask + Gunicorn
- MongoDB (local o Atlas)
- Diseño Dark Mode moderno

## Configuración

### Variables de Entorno
```bash
export MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net"
export LOCAL_MONGO="mongodb://localhost:27017"
export MONGO_DB="frigoninja"
```

### Ejecutar Localmente
```bash
cd ~/refrigerador-service
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Servicio Systemd
```bash
systemctl --user start refrigerador
systemctl --user enable refrigerador
```

### Nginx + SSL
```bash
~/setup_nginx.sh
```

## API Endpoints
- `GET /api/health` - Estado de la app
- `GET /api/items?categoria=refri` - Obtener items
- `POST /api/items` - Agregar item
- `GET /api/items/en-cero` - Items agotados
- `GET /api/kcal-info` - Info calórica
- `POST /api/consumo` - Registrar consumo

## Deploy en get.tech
1. Clonar repo: `git clone https://github.com/fienbeh1/fridge.git`
2. Crear venv e instalar deps
3. Configurar MongoDB
4. Ejecutar `~/setup_nginx.sh`
