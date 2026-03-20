# Refrigerador local

## Levantar el servidor

- Usa el `venv` incluido y `gunicorn` para simular un entorno WSGI:
  ```bash
  ./venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 app:app
  ```
- Alternativamente ejecuta el helper `start-gunicorn.sh`:
  ```bash
  ./start-gunicorn.sh
  ```

## Alias sugerido

Agrega esto a tu `~/.bashrc` (o el shell que uses) para arrancar con alias:

```bash
alias refrigerador="cd /home/f/refrigerador-service && ./start-gunicorn.sh"
```

Luego basta con correr `refrigerador` y el alias se encargará de cambiar de directorio y levantar gunicorn.
