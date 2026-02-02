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

| Servicio        | URL                   | Usuario | Contraseña |
| --------------- | --------------------- | ------- | ---------- |
| **n8n**         | http://localhost:5678 | admin   | admin123   |
| **Backend API** | http://localhost:5000 | -       | -          |
| **PostgreSQL**  | localhost:5432        | admin   | admin123   |
| **Chroma**      | http://localhost:8000 | -       | -          |

## **Verificar que todo funciona**

```bash
# Comprobar salud del backend
curl http://localhost:5000/health

# Deberías ver:
# {"status":"ok","message":"Backend funcionando"}
```

## **Próximos pasos**

### **1. Crear workflow en n8n**

1. Accede a http://localhost:5678
2. Crea un nuevo workflow
3. Añade nodo: "HTTP Request" → POST a `http://backend:5000/upload`
4. Adjunta trigger para archivos

### **2. Probar carga de archivos**

```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@datos.xlsx" \
  -F "type=facturas"
```

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
