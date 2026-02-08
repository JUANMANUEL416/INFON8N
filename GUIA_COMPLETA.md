# 🎉 Sistema de Reportes Dinámicos - Implementación Completa

## ✅ Funcionalidades Implementadas

### 1. 🔐 Sistema de Autenticación

#### Características:

- Login con usuario y contraseña
- Validación de autenticación en todas las páginas
- Control de acceso basado en grupos
- Sesión persistente en localStorage
- Cerrar sesión

#### Páginas:

- **`/login`**: Página de inicio de sesión
- Redirección automática según el grupo del usuario
- Protección de rutas administrativas

#### Credenciales por Defecto:

```
Usuario: admin
Contraseña: admin123
Grupo: Administradores
```

---

### 2. 👥 Gestión de Usuarios y Grupos

#### Tablas de Base de Datos:

**`grupos`**

- id, codigo, nombre, descripcion, estado
- Grupos por defecto: `admin`, `usuarios`

**`usuarios`**

- id, username, password, nombre, estado, grupo_id
- Relación con grupos (FK)

**`grupos_reportes`** (Tabla Intermedia)

- id, grupo_id, reporte_codigo
- puede_ver, puede_crear, puede_editar, puede_eliminar
- Control granular de permisos

#### Panel de Administración - Sección Usuarios:

**Tab "Usuarios":**

- Lista todos los usuarios del sistema
- Crear nuevo usuario con username, password, nombre, grupo
- Editar usuarios existentes
- Ver grupo asignado y estado

**Tab "Grupos":**

- Lista todos los grupos
- Crear nuevo grupo con código, nombre, descripción
- Ver cantidad de usuarios por grupo
- Editar grupos existentes

**Tab "Permisos":**

- Asignar permisos de reportes a grupos
- Control granular: ver, crear, editar, eliminar
- Interfaz visual con checkboxes
- Actualización en tiempo real

---

### 3. 🔌 API de Consultas Dinámicas

#### Nuevos Campos en Reportes:

**`api_endpoint`** (VARCHAR 255)

- Endpoint personalizado para consultar el reporte
- Ejemplo: `/api/query/facturas_especiales`
- Si está vacío, usa: `/api/query/{codigo}`

**`query_template`** (TEXT)

- Plantilla SQL personalizada para consultas
- Soporta placeholders: `{codigo}`, `{fecha_inicio}`, `{fecha_fin}`, `{limite}`, `{campo_*}`
- Si está vacío, usa consulta estándar

#### Endpoints de API:

**`GET /api/query/<codigo>`**
Consultar datos de un reporte con filtros.

**Parámetros de Query:**

```
?fecha_inicio=2026-01-01
&fecha_fin=2026-01-31
&limite=100
&campo_categoria=ventas
&campo_estado=pagado
```

**Respuesta:**

```json
{
  "success": true,
  "reporte": "Facturación Diaria",
  "total": 25,
  "datos": [
    {
      "id": 1,
      "datos": {
        "fecha": "2026-01-15",
        "monto": 1500.0,
        "categoria": "ventas"
      },
      "created_at": "2026-01-15T10:30:00",
      "uploaded_by": "admin"
    }
  ]
}
```

**`GET /api/query/<codigo>/export`**
Exportar datos filtrados a Excel.

**Parámetros:**

- Mismos que el endpoint de consulta
- Límite por defecto: 1000

**Respuesta:**

- Archivo Excel descargable
- Nombre: `{codigo}_{fecha}.xlsx`

---

### 4. 📊 Formulario de Creación de Reportes Mejorado

#### Nueva Sección: "🔌 API y Consultas"

Agregada después de la información básica, antes de los campos.

**Campos del Formulario:**

1. **Endpoint de API** (opcional)
   - Input text
   - Placeholder: `/api/query/facturacion_diaria`
   - Ayuda: "Si se deja vacío, se usará /api/query/{codigo}"

2. **Plantilla de Consulta SQL** (opcional)
   - Textarea multilinea
   - Placeholder con ejemplo de SQL
   - Ayuda sobre placeholders disponibles

**Ejemplo de Plantilla:**

```sql
SELECT * FROM datos_reportes
WHERE reporte_codigo = '{codigo}'
  AND datos->>'fecha' >= '{fecha_inicio}'
  AND datos->>'fecha' <= '{fecha_fin}'
  AND datos->>'categoria' = '{campo_categoria}'
ORDER BY created_at DESC
LIMIT {limite}
```

---

### 5. 🛠️ Métodos de DatabaseManager

#### Autenticación:

```python
autenticar_usuario(username, password)
# Retorna: Dict con datos del usuario + grupo, o None
```

#### Usuarios:

```python
crear_usuario(username, password, nombre, grupo_id, estado)
obtener_usuarios()  # Lista todos con info de grupo
actualizar_usuario(user_id, datos)
```

#### Grupos:

```python
crear_grupo(codigo, nombre, descripcion, estado)
obtener_grupos()  # Lista todos con count de usuarios
actualizar_grupo(grupo_id, datos)
```

#### Permisos:

```python
asignar_permiso_grupo(grupo_id, reporte_codigo, puede_ver, puede_crear, puede_editar, puede_eliminar)
obtener_permisos_grupo(grupo_id)
obtener_reportes_permitidos_usuario(user_id)
verificar_permiso_usuario(user_id, reporte_codigo, accion)
eliminar_permiso_grupo(grupo_id, reporte_codigo)
```

#### Consultas de Datos:

```python
consultar_datos_filtrado(reporte_codigo, fecha_inicio, fecha_fin, limite, filtros)
# Consulta estándar con filtros en campos JSONB

consultar_datos_custom(reporte_codigo, query_template, **kwargs)
# Ejecuta plantilla SQL personalizada con placeholders
```

---

## 🌐 Endpoints API Completos

### Autenticación

```
POST   /api/auth/login
```

### Usuarios

```
GET    /api/usuarios
POST   /api/usuarios
PUT    /api/usuarios/{user_id}
```

### Grupos

```
GET    /api/grupos
POST   /api/grupos
PUT    /api/grupos/{grupo_id}
```

### Permisos

```
GET    /api/permisos/grupo/{grupo_id}
POST   /api/permisos/grupo/{grupo_id}/reporte/{reporte_codigo}
DELETE /api/permisos/grupo/{grupo_id}/reporte/{reporte_codigo}
GET    /api/permisos/usuario/{user_id}/reportes
```

### Reportes (Admin)

```
GET    /api/admin/reportes
POST   /api/admin/reportes
GET    /api/admin/reportes/{codigo}
DELETE /api/admin/reportes/{codigo}
POST   /api/admin/reportes/{codigo}/cargar
```

### Consultas Dinámicas

```
GET    /api/query/{codigo}
GET    /api/query/{codigo}/export
```

### Datos

```
GET    /api/reportes/{codigo}/datos
GET    /api/reportes/{codigo}/estadisticas
```

---

## 🎨 Mejoras de Interfaz

### Admin Panel:

- ✅ Validación de autenticación
- ✅ Botón de cerrar sesión
- ✅ Tab de Usuarios con tabla
- ✅ Tab de Grupos con tabla
- ✅ Tab de Permisos con matriz de checkboxes
- ✅ Modales para crear usuario y grupo
- ✅ Formulario de reportes con sección API
- ✅ Estilos para tablas y badges

### Login Page:

- ✅ Diseño atractivo con gradiente
- ✅ Validación de formulario
- ✅ Mensajes de error/éxito
- ✅ Redirección automática
- ✅ Credenciales de ejemplo visibles

---

## 📝 Migraciones Ejecutadas

### 1. `migrate_auth.py`

- ✅ Creó tabla `grupos`
- ✅ Creó nueva tabla `usuarios` con password
- ✅ Creó tabla `grupos_reportes`
- ✅ Migró datos de usuarios_old
- ✅ Insertó grupos por defecto (admin, usuarios)
- ✅ Insertó usuario admin
- ✅ Asignó permisos al grupo admin

### 2. `migrate_api_campos.py`

- ✅ Agregó columna `api_endpoint` a `reportes_config`
- ✅ Agregó columna `query_template` a `reportes_config`

---

## 🚀 Casos de Uso

### Caso 1: Consultar Facturación del Mes

```bash
curl "http://localhost:5000/api/query/facturacion_diaria?fecha_inicio=2026-02-01&fecha_fin=2026-02-28&limite=100"
```

### Caso 2: Filtrar por Campo Personalizado

```bash
curl "http://localhost:5000/api/query/facturas?campo_categoria=servicios&campo_estado=pagado"
```

### Caso 3: Exportar a Excel

```bash
curl "http://localhost:5000/api/query/facturas/export?fecha_inicio=2026-01-01&fecha_fin=2026-01-31" -O -J
```

### Caso 4: Crear Usuario de Ventas

```bash
curl -X POST http://localhost:5000/api/usuarios \
  -H "Content-Type: application/json" \
  -d '{
    "username": "vendedor1",
    "password": "pass123",
    "nombre": "Juan Vendedor",
    "grupo_id": 3,
    "estado": "activo"
  }'
```

### Caso 5: Asignar Permiso de Solo Lectura

```bash
curl -X POST http://localhost:5000/api/permisos/grupo/3/reporte/facturas \
  -H "Content-Type: application/json" \
  -d '{
    "puede_ver": true,
    "puede_crear": false,
    "puede_editar": false,
    "puede_eliminar": false
  }'
```

---

## 🔧 Configuración de Reporte con API Personalizada

### Ejemplo: Reporte de Ventas Mensuales

**Información Básica:**

- Nombre: Ventas Mensuales
- Código: `ventas_mensuales`
- Categoría: Ventas
- Descripción: Reporte consolidado de ventas por mes

**API y Consultas:**

- Endpoint de API: `/api/query/ventas/consolidado`
- Plantilla de Consulta:

```sql
SELECT
  datos->>'mes' as mes,
  SUM((datos->>'monto')::decimal) as total,
  COUNT(*) as cantidad
FROM datos_reportes
WHERE reporte_codigo = '{codigo}'
  AND datos->>'año' = '{campo_año}'
GROUP BY datos->>'mes'
ORDER BY mes
LIMIT {limite}
```

**Uso:**

```bash
curl "http://localhost:5000/api/query/ventas_mensuales?campo_año=2026&limite=12"
```

---

## ⚠️ Notas Importantes

### Seguridad:

1. **Passwords en texto plano**: Solo para desarrollo
   - En producción: Implementar bcrypt

   ```python
   import bcrypt
   hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
   ```

2. **Validación de SQL**: Las plantillas de consulta no están sanitizadas
   - Implementar validación y escape de parámetros
   - Usar prepared statements

3. **CORS**: Configurado para desarrollo
   - En producción: Restringir orígenes permitidos

4. **Autenticación**: Basada en localStorage
   - En producción: Implementar JWT tokens
   - Agregar expiración de sesiones

### Performance:

1. **Consultas JSONB**: Pueden ser lentas con muchos datos
   - Considerar índices GIN en campos JSONB
   - Evaluar desnormalización de datos críticos

2. **Límite de registros**: Default 100/1000
   - Implementar paginación para grandes volúmenes

---

## 📊 Estado Actual del Sistema

### ✅ Completado:

- [x] Sistema de autenticación
- [x] Gestión de usuarios
- [x] Gestión de grupos
- [x] Sistema de permisos
- [x] API de consultas dinámicas
- [x] Exportación a Excel
- [x] Interfaz de administración de usuarios
- [x] Formulario con campos de API
- [x] Migraciones de BD

### 🔄 Por Mejorar:

- [ ] Hasheo de passwords (bcrypt)
- [ ] Tokens JWT para sesiones
- [ ] Validación de plantillas SQL
- [ ] Paginación de resultados
- [ ] Logs de auditoría
- [ ] Recuperación de contraseña
- [ ] Índices en campos JSONB
- [ ] Tests unitarios

---

## 🎯 Próximos Pasos Sugeridos

1. **Seguridad**:
   - Implementar bcrypt para passwords
   - JWT para autenticación stateless
   - Rate limiting en login
   - HTTPS en producción

2. **Funcionalidad**:
   - Dashboard con métricas
   - Notificaciones de sistema
   - Historial de cambios
   - Búsqueda avanzada de datos

3. **Performance**:
   - Cache de consultas frecuentes
   - Índices optimizados
   - Compresión de responses
   - CDN para assets estáticos

4. **UX**:
   - Tema oscuro/claro
   - Favoritos de reportes
   - Exportación a otros formatos (CSV, PDF)
   - Gráficos y visualizaciones

---

## 📞 URLs de Acceso

- **Login**: http://localhost:5000/login
- **Portal Usuario**: http://localhost:5000/
- **Admin Panel**: http://localhost:5000/admin
- **API Docs**: http://localhost:5000/api/

---

## 🧪 Pruebas Rápidas

### 1. Login

```javascript
// Navegador Console
localStorage.getItem("usuario");
```

### 2. Crear Grupo

```bash
curl -X POST http://localhost:5000/api/grupos \
  -H "Content-Type: application/json" \
  -d '{"codigo":"ventas","nombre":"Equipo Ventas","descripcion":"Vendedores"}'
```

### 3. Consultar API

```bash
curl "http://localhost:5000/api/query/facturacion_diaria?limite=10"
```

---

¡Sistema completo y listo para usar! 🎉
