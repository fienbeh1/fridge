# Ejercicios MongoDB - Refrigerador

Practica MongoDB usando `mongosh` con la base de datos `refrigerador`.

## Conexion

```bash
mongosh mongodb://localhost:27017/refrigerador
```

## Colecciones disponibles

- `items` - almacena los alimentos del refrigerador

---

## Ejercicio 1: Insertar documentos

```js
// Insertar un alimento
db.items.insertOne({
  nombre: "Tomates",
  cantidad: "500g",
  comprado_en: new Date()
})

// Insertar varios a la vez
db.items.insertMany([
  { nombre: "Cebolla", cantidad: "3 unidades", comprado_en: new Date() },
  { nombre: "Ajo", cantidad: "1 cabeza", comprado_en: new Date() },
  { nombre: "Pimiento rojo", cantidad: "2 unidades", comprado_en: new Date() }
])
```

---

## Ejercicio 2: Consultar documentos

```js
// Ver todos los items
db.items.find()

// Ver todos con formato legible
db.items.find().pretty()

// Buscar por nombre especifico
db.items.find({ nombre: "Tomates" })

// Buscar items con cantidad mayor a 2
db.items.find({ cantidad: { $exists: true } })

// Contar documentos
db.items.countDocuments()

// Solo mostrar nombres
db.items.find({}, { nombre: 1, _id: 0 })
```

---

## Ejercicio 3: Actualizar documentos

```js
// Actualizar un campo
db.items.updateOne(
  { nombre: "Tomates" },
  { $set: { cantidad: "1kg" } }
)

// Agregar un campo nuevo
db.items.updateOne(
  { nombre: "Tomates" },
  { $set: { categoria: "verdura" } }
)

// Actualizar varios
db.items.updateMany(
  {},
  { $set: { disponible: true } }
)
```

---

## Ejercicio 4: Eliminar documentos

```js
// Eliminar uno por nombre
db.items.deleteOne({ nombre: "Ajo" })

// Eliminar varios que cumplan condicion
db.items.deleteMany({ nombre: { $regex: "^C" } })

// Eliminar todos ( cuidado! )
db.items.deleteMany({})
```

---

## Ejercicio 5: Consultas avanzadas

```js
// Ordenar por fecha (mas reciente primero)
db.items.find().sort({ comprado_en: -1 })

// Limitar resultados
db.items.find().limit(3)

// Skip primeros resultados (paginar)
db.items.find().skip(2).limit(2)

// Buscar por rango de fechas
db.items.find({
  comprado_en: {
    $gte: new Date("2026-01-01"),
    $lt: new Date("2026-12-31")
  }
})
```

---

## Ejercicio 6: Agregaciones basicas

```js
// Contar items por categoria (si existe)
db.items.aggregate([
  { $group: { _id: "$categoria", total: { $sum: 1 } } }
])

// Items ordenados alfabeticamente
db.items.aggregate([
  { $sort: { nombre: 1 } },
  { $project: { nombre: 1, cantidad: 1 } }
])
```

---

## Ejercicio 7: Indices

```js
// Crear indice en nombre para busquedas rapidas
db.items.createIndex({ nombre: 1 })

// Ver indices existentes
db.items.getIndexes()

// Indice texto para busqueda de palabras
db.items.createIndex({ nombre: "text" })

// Buscar usando indice texto
db.items.find({ $text: { $search: "tomate" } })
```

---

## Comandos utiles

```js
// Ver base de datos actual
db

// Listar bases de datos
show dbs

// Ver colecciones
show collections

// Ver estado de la base de datos
db.stats()

// Ver tamanio de coleccion
db.items.stats()
```

---

## Soluciones rapidas

```js
// Borra todo y empieza de nuevo
db.items.drop()

// Ver documentacion
db.help()
```
