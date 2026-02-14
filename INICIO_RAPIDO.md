# 🚀 Guía de Inicio Rápido - Sistema Completo

## ⚡ Iniciar Todo con Docker (Recomendado)

```bash
# 1. Asegúrate de tener el archivo .env con tu API key de OpenAI
echo "OPENAI_API_KEY=sk-tu-key-aqui" > .env

# 2. Levanta todos los servicios
docker-compose up -d

# 3. Espera a que todos los servicios estén listos (30-60 segundos)
docker-compose ps

# 4. Accede al frontend
# http://localhost:8080
```

### Servicios Disponibles

| Servicio              | Puerto | URL                   | Usuario | Contraseña |
| --------------------- | ------ | --------------------- | ------- | ---------- |
| **Frontend** (Quasar) | 8080   | http://localhost:8080 | -       | -          |
| **Backend** (Flask)   | 5000   | http://localhost:5000 | -       | -          |
| **n8n** (Workflows)   | 5678   | http://localhost:5678 | admin   | admin123   |
| **PostgreSQL**        | 5432   | localhost:5432        | admin   | admin123   |
| **ChromaDB**          | 8000   | http://localhost:8000 | -       | -          |

---

## 🔧 Desarrollo Local (Sin Docker)

### Backend

```bash
# 1. Ir a la carpeta del backend
cd backend

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
set OPENAI_API_KEY=sk-tu-key-aqui
set DB_HOST=localhost
set DB_USER=admin
set DB_PASSWORD=admin123
set DB_NAME=informes_db

# 6. Ejecutar
python app.py
```

Backend corriendo en: `http://localhost:5000`

### Frontend

```bash
# 1. Ir a la carpeta del frontend
cd frontend

# 2. Instalar dependencias
npm install

# 3. Ejecutar en modo desarrollo
npm run dev
```

Frontend corriendo en: `http://localhost:8080`

---

## 👤 Primer Uso

### 1. Crear Usuario Administrativo

```bash
# Ejecutar script Python para crear usuario admin
docker-compose exec backend python -c "
from models import Usuario
from db_manager import DatabaseManager
import bcrypt

db = DatabaseManager()
password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
db.execute('''
    INSERT INTO usuarios (username, nombre, password_hash, role)
    VALUES ('admin', 'Administrador', %s, 'admin')
    ON CONFLICT (username) DO NOTHING
''', (password.decode('utf-8'),))
print('Usuario admin creado')
"
```

**Credenciales:**

- Usuario: `admin`
- Contraseña: `admin123`

### 2. Login en el Frontend

1. Accede a http://localhost:8080
2. Ingresa: `admin` / `admin123`
3. Serás redirigido al dashboard

### 3. Subir tu Primer Reporte

#### Opción A: Desde el Frontend

1. Haz clic en el menú → **Administración**
2. Ve a la tab **Upload**
3. Completa el formulario:
   - **Código**: `ventas_enero`
   - **Nombre**: `Reporte de Ventas - Enero 2024`
   - **Contexto**: `Este reporte contiene las ventas del mes de enero...`
   - **Archivo**: Selecciona tu Excel (.xlsx)
4. Clic en **Subir y Procesar**
5. Espera la confirmación ✅

#### Opción B: Usando Scripts

```bash
# Generar datos de prueba
docker-compose exec backend python scripts/generate_sample_data.py

# O subir un archivo específico
curl -X POST -F "file=@mi_archivo.xlsx" \
     -F "codigo=ventas_enero" \
     -F "nombre=Ventas Enero" \
     -F "contexto=Reporte mensual" \
     http://localhost:5000/upload
```

### 4. Consultar con IA

1. Ve al inicio (menú → **Chat IA**)
2. Selecciona tu reporte del dropdown
3. Haz preguntas como:
   - "¿Cuál fue el total de ventas?"
   - "Muéstrame las 5 mejores ventas"
   - "¿Cuántos clientes compraron?"
   - "Compara las ventas de esta semana vs la anterior"

---

## 📊 Ejemplo Completo: Reporte de Facturación

### 1. Preparar Excel

Crea un archivo `facturacion.xlsx` con columnas:

- `fecha`
- `cliente`
- `factura_numero`
- `monto`
- `estado`
- `vendedor`

### 2. Subir desde la UI

- Código: `facturacion_2024`
- Nombre: `Facturación Emitida 2024`
- Contexto:
  ```
  Reporte de facturación emitida de manera unitaria.
  Incluye todas las facturas generadas en el año 2024.
  Campos: fecha, cliente, número de factura, monto, estado, vendedor.
  ```

### 3. Preguntas de Ejemplo

```
Usuario: ¿Cuál es el total facturado?
IA: El total facturado es $1,234,567.89

Usuario: ¿Quién es el vendedor con más ventas?
IA: El vendedor con más ventas es Juan Pérez con $345,678.90

Usuario: Muéstrame las facturas pendientes
IA: [Tabla con facturas donde estado = 'pendiente']

Usuario: Compara el primer trimestre vs el segundo
IA:
- Q1 (Ene-Mar): $450,000
- Q2 (Abr-Jun): $520,000
- Incremento: 15.6%
```

---

## 🔄 Comandos Útiles Docker

```bash
# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs solo del backend
docker-compose logs -f backend

# Ver logs solo del frontend
docker-compose logs -f frontend

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra datos)
docker-compose down -v

# Reconstruir un servicio específico
docker-compose up -d --build backend

# Ejecutar comando en el backend
docker-compose exec backend python scripts/test_sistema.py

# Ver estado de servicios
docker-compose ps

# Reiniciar un servicio
docker-compose restart backend
```

---

## 🧪 Verificar que Todo Funciona

### Test Rápido del Sistema

```bash
# 1. Verificar que todos los servicios estén corriendo
docker-compose ps

# 2. Test del backend
curl http://localhost:5000/api/reportes

# 3. Test de ChromaDB
curl http://localhost:8000/api/v1/heartbeat

# 4. Test del frontend
curl http://localhost:8080

# 5. Test completo de IA (ejecutar desde el backend)
docker-compose exec backend python scripts/test_rapido.py
```

### Verificar Indexación

```bash
docker-compose exec backend python scripts/verificar_chromadb.py
```

Deberías ver:

```
✓ ChromaDB conectado
✓ Colección encontrada: informes_data
✓ Documentos indexados: 1523
```

---

## 🐛 Solución de Problemas Comunes

### El frontend no carga

```bash
# 1. Verificar que el contenedor esté corriendo
docker-compose ps frontend

# 2. Ver logs
docker-compose logs frontend

# 3. Reconstruir
docker-compose up -d --build frontend
```

### Error 401 al hacer requests

- Verifica que estás logueado
- Revisa que el token no haya expirado
- Haz logout y login nuevamente

### No se indexan los datos

```bash
# Verificar que ChromaDB esté corriendo
docker-compose ps chroma

# Ejecutar indexación manual
docker-compose exec backend python -c "
from analysis_agent import AnalysisAgent
agent = AnalysisAgent()
agent.indexar_datos_reporte('tu_codigo_reporte')
print('Indexación completada')
"
```

### El chat IA no responde

1. Verifica que tengas una API key de OpenAI válida
2. Revisa los logs del backend: `docker-compose logs backend`
3. Confirma que el reporte esté indexado
4. Intenta limpiar la conversación y volver a preguntar

### PostgreSQL no conecta

```bash
# Espera a que PostgreSQL esté listo
docker-compose up -d postgres
sleep 30

# Verificar healthcheck
docker inspect devprueba-postgres | grep Health
```

---

## 📝 Workflow Típico

### Flujo Diario de Uso

```
1. Usuario Admin sube nuevo Excel
   ↓
2. Backend procesa e indexa automáticamente en ChromaDB
   ↓
3. Usuario común accede al Chat IA
   ↓
4. Selecciona el reporte
   ↓
5. Hace preguntas en lenguaje natural
   ↓
6. IA responde usando RAG + Function Calling
   ↓
7. Usuario puede limpiar sesión o seguir conversando
```

### Integración con n8n

```
1. Configura webhook en n8n (puerto 5678)
   ↓
2. Sistema externo envía datos JSON
   ↓
3. n8n procesa y llama a /webhook/upload
   ↓
4. Backend guarda en PostgreSQL
   ↓
5. Backend indexa en ChromaDB automáticamente
   ↓
6. Datos disponibles para consulta inmediata
```

---

## 🎯 Checklist de Inicio

- [ ] Docker y Docker Compose instalados
- [ ] Archivo `.env` con `OPENAI_API_KEY`
- [ ] `docker-compose up -d` ejecutado
- [ ] Usuario admin creado
- [ ] Login exitoso en http://localhost:8080
- [ ] Primer reporte subido
- [ ] Datos indexados en ChromaDB
- [ ] Primera pregunta al chat IA respondida ✅

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs: `docker-compose logs -f`
2. Verifica el archivo `.env`
3. Confirma que todos los puertos estén libres (5000, 5678, 8080, 5432, 8000)
4. Reconstruye los contenedores: `docker-compose up -d --build`

---

## 🎉 ¡Sistema Listo!

Ahora tienes un sistema completo de Business Intelligence con:

✅ Frontend moderno en Vue 3 + Quasar  
✅ Backend API en Flask  
✅ Base de datos PostgreSQL  
✅ Vector Database ChromaDB  
✅ IA conversacional con OpenAI GPT-4o  
✅ Memoria de conversaciones  
✅ Function Calling para cálculos precisos  
✅ Auto-indexación de datos  
✅ Workflows con n8n  
✅ Todo containerizado con Docker

**¡A consultar tus reportes con IA!** 🚀
