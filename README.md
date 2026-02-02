# Sistema de Análisis de Informes Gerenciales con n8n

Plataforma local para automatizar la carga y análisis de reportes gerenciales (facturación, cartera, etc.) usando n8n, PostgreSQL y APIs de IA.

## **Requisitos Previos**

- Docker Desktop instalado ([descargar](https://www.docker.com/products/docker-desktop))
- Git (opcional)
- Mínimo 8GB RAM disponible

## **Estructura del Proyecto**

```
devprueba/
├── docker-compose.yml       # Orquestación de contenedores
├── .env                     # Variables de entorno
├── backend/                 # API Python (Flask)
│   ├── app.py              # Aplicación principal
│   ├── requirements.txt     # Dependencias Python
│   └── Dockerfile          # Imagen Docker
├── data/                    # Archivos Excel subidos
├── scripts/                # Scripts Python adicionales
└── n8n/                    # Configuración de n8n
```

## **Inicio Rápido**

### **1. Clonar el proyecto**

```bash
cd c:\Dev8n8\devprueba
```

### **2. Iniciar los servicios**

```bash
docker-compose up -d
```

Espera 30-60 segundos para que todo esté listo.

### **3. Acceder a los servicios**

| Servicio           | URL                          | Usuario | Contraseña |
| ------------------ | ---------------------------- | ------- | ---------- |
| **Aplicación Web** | http://localhost:5000        | -       | -          |
| **n8n**            | http://localhost:5678        | admin   | admin123   |
| **Backend API**    | http://localhost:5000/health | -       | -          |
| **PostgreSQL**     | localhost:5432               | admin   | admin123   |
| **Chroma**         | http://localhost:8000        | -       | -          |

### **4. Usar la Aplicación Web** 🌐

**La forma más fácil para el cliente:**

1. Abrir navegador en: **http://localhost:5000**
2. Descargar la plantilla que necesite
3. Completar los datos en Excel
4. Subir el archivo desde la web
5. Ver estadísticas actualizadas

✅ **No requiere conocimientos técnicos**
✅ **Interfaz visual e intuitiva**
✅ **Validación automática de archivos**

## **Verificar que todo funciona**

```bash
# Comprobar salud del backend
curl http://localhost:5000/health

# Deberías ver:
# {"status":"ok","message":"Backend funcionando"}
```

## **Próximos pasos (para desarrolladores)**

### **1. Generar plantillas de datos** (ya hecho ✅)

```bash
cd scripts
python create_templates.py
```

Esto creará plantillas Excel en `data/plantillas/` con estructura fija para:

- **Facturación diaria** - Carga de facturas
- **Cartera vencida** - Cuentas por cobrar
- **Ventas productos** - Ventas por producto
- **Gastos operativos** - Gastos del día

### **2. Configurar workflows en n8n** (opcional)

1. Accede a http://localhost:5678
2. Crea un nuevo workflow
3. Añade nodo: "HTTP Request" → POST a `http://backend:5000/upload`
4. Adjunta trigger para archivos

### **4. Probar carga de archivos**

````bash
# Cargar facturas
curl -X POST http://localhost:5000/upload \
  -F "file=@data/plantillas/plantilla_facturacion_diaria.xlsx" \
  -F "type=facturas"

# Carg5. Ver estadísticas**

```bash
curl http://localhost:5000/stats
````

### **6. Ver plantillas disponibles**

```bash
curl http://localhost:5000/templates
```

## **📋 Tipos de datos soportados**

| Tipo        | Plantilla                         | Descripción         |
| ----------- | --------------------------------- | ------------------- |
| `facturas`  | plantilla_facturacion_diaria.xlsx | Facturación diaria  |
| `cartera`   | plantilla_cartera_vencida.xlsx    | Cartera vencida     |
| `productos` | plantilla_ventas_productos.xlsx   | Ventas por producto |
| `gastos`    | plantilla_gastos_operativos.xlsx  | Gastos operativos   |

Ver documentación completa en: `data/plantillas/README.md

# Cargar productos

curl -X POST http://localhost:5000/upload \
 -F "file=@data/plantillas/plantilla_ventas_productos.xlsx" \
 -F "type=productos"

# Cargar gastos

curl -X POST http://localhost:5000/upload \
 -F "file=@data/plantillas/plantilla_gastos_operativos.xlsx" \
 -F "type=gastos"

````

### **5. Probar carga de archivos**

```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@datos.xlsx" \
  -F "type=facturas"
````

### **3. Ver estadísticas**

```bash
curl http://localhost:5000/stats
```

## **Parar los servicios**

```bash
docker-compose down
```

## **Ver logs**

```bash
# Todos
docker-compose logs -f

# Específico
docker-compose logs -f backend
docker-compose logs -f n8n
docker-compose logs -f postgres
```

## **Troubleshooting**

### Puerto ya en uso

```bash
# Cambiar en docker-compose.yml, línea del puerto conflictivo
# Por ejemplo, cambiar "5678:5678" a "5679:5678"
```

### Base de datos no inicializa

```bash
docker-compose down -v  # Elimina volúmenes
docker-compose up -d    # Reinicia
```

### Backend no conecta a BD

```bash
docker-compose logs backend
# Verifica que "postgres" esté healthy
docker-compose ps
```

## **Próximas Fases**

- [ ] Integración con OpenAI para análisis inteligente
- [ ] Chatbot de preguntas sobre datos
- [ ] Frontend React para interfaz
- [ ] Exportación de reportes
- [ ] Programación de cargas automáticas

---

**Estado**: 🟢 Backend operativo | 🟢 BD inicializada | 🟡 n8n listo para workflows
