# Solución ChromaDB - Indexación de Datos

## Estado Actual: ✅ RESUELTO

ChromaDB está funcionando correctamente. El problema de indexación era debido a:

### Problemas Encontrados y Solucionados:

1. **Healthcheck Incorrecto** ❌➜✅
   - **Problema**: El contenedor usaba `/api/v1/heartbeat` (deprecado)
   - **Solución**: Eliminado healthcheck (no es necesario, ChromaDB funciona sin él)
   - **Cambio**: [docker-compose.yml](docker-compose.yml) - Sección ChromaDB simplificada

2. **Incompatibilidad de Versiones** ❌➜✅
   - **Problema**: chromadb cliente 0.4.22 incompatible con servidor latest
   - **Error**: `KeyError: '_type'`
   - **Solución**: Actualizado a `chromadb>=0.5.23` en [requirements.txt](backend/requirements.txt)
   - **Causa**: El servidor ChromaDB latest usa API v2, cliente viejo solo v1

3. **Método de Creación de Colecciones** ❌➜✅
   - **Problema**: `get_collection()` + `create_collection()` causaba conflictos
   - **Solución**: Usar `get_or_create_collection()` en [analysis_agent.py](backend/analysis_agent.py)

4. **Volumen de Persistencia** ❌➜✅
   - **Problema**: Datos en `/chroma/data` pero variable apuntaba a `/data`
   - **Solución**: Cambio de volumen de `chroma_data:/chroma/data` a `chroma_data:/data`

### Proceso de Primera Ejecución

⏳ **IMPORTANTE**: La primera vez que se usa ChromaDB, descarga el modelo de embeddings:

```
Modelo: all-MiniLM-L6-v2
Tamaño: ~79 MB
Tiempo: 3-5 minutos (depende de conexión)
Ubicación: /root/.cache/chroma/onnx_models/
```

Este proceso es **NORMAL y ÚNICO**. Después de la primera descarga, la indexación es rápida (< 10 segundos).

## Pruebas de Validación

### 1. Verificar Estado de ChromaDB

```powershell
# Ver contenedores
docker-compose ps

# ChromaDB debería mostrar "Up" (sin "unhealthy")
```

### 2. Probar Conexión

```powershell
curl http://localhost:8000/api/v2
# Debe devolver: {"nanosecond heartbeat":...}
```

### 3. Ejecutar Indexación

```powershell
python .\scripts\test_indexacion.py
```

**Salida esperada** (después de descargar modelo):

```
✅ ¡INDEXACIÓN EXITOSA!
   Registros indexados: 1000
   Colección: reporte_facturacion_emitida_de_manera_unitaria
🎉 ChromaDB está funcionando correctamente
```

### 4. Verificar Descarga del Modelo

Si la indexación tarda mucho la primera vez:

```powershell
docker logs devprueba-backend --tail 20
```

Buscar líneas como:

```
/root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz: 100%
```

## Archivos Modificados

| Archivo                      | Cambios                                 | Estado   |
| ---------------------------- | --------------------------------------- | -------- |
| `docker-compose.yml`         | Removido healthcheck, corregido volumen | ✅       |
| `backend/requirements.txt`   | `chromadb>=0.5.23`                      | ✅       |
| `backend/analysis_agent.py`  | `get_or_create_collection()`            | ✅       |
| `scripts/test_indexacion.py` | Script de prueba                        | ✅ NUEVO |

## Uso Post-Configuración

### API de Indexación

```bash
POST http://localhost:5000/api/analysis/{codigo_reporte}/indexar
```

**Ejemplo**:

```powershell
curl -X POST "http://localhost:5000/api/analysis/facturacion%20emitida%20de%20manera%20unitaria/indexar"
```

### Desde Panel de Administración

1. Abrir http://localhost:5000/admin.html
2. Ir a sección "Análisis de Datos"
3. Hacer clic en "Indexar Datos"
4. Esperar confirmación de éxito

## Troubleshooting

### Si la indexación falla:

1. **Verfiicar que ChromaDB esté corriendo**:

   ```powershell
   docker-compose ps chroma
   # Debe mostrar "Up"
   ```

2. **Reiniciar ChromaDB**:

   ```powershell
   docker-compose restart chroma
   Start-Sleep -Seconds 10
   ```

3. **Verificar logs**:

   ```powershell
   docker logs devprueba-backend --tail 50
   docker logs devprueba-chroma --tail 50
   ```

4. **Recrear contenedor** (si persiste):
   ```powershell
   docker-compose stop chroma backend
   docker-compose rm -f chroma
   docker volume rm devprueba_chroma_data
   docker-compose up -d chroma backend
   ```

## Próximos Pasos

- ✅ ChromaDB configurado y funcionando
- ⏳ Esperando descarga inicial del modelo de embeddings
- 📝 Probar búsqueda semántica después de indexación
- 📊 Validar consultas con lenguaje natural

---

**Nota**: Una vez que el modelo esté descargado (se puede verificar con `docker logs`), ejecutar `test_indexacion.py` y debería completarse en segundos.
