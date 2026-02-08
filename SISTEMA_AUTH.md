# Sistema de Autenticación y Permisos

## ✅ Sistema Implementado

Se ha implementado un sistema completo de autenticación basado en **usuarios**, **grupos** y **permisos** que permite controlar qué reportes puede ver cada usuario según su grupo.

---

## 📊 Estructura de Base de Datos

### Tabla: `grupos`

Almacena los grupos de usuarios.

| Campo       | Tipo         | Descripción                                      |
| ----------- | ------------ | ------------------------------------------------ |
| id          | SERIAL       | ID único del grupo                               |
| codigo      | VARCHAR(100) | Código único del grupo (ej: 'admin', 'usuarios') |
| nombre      | VARCHAR(255) | Nombre descriptivo del grupo                     |
| descripcion | TEXT         | Descripción del grupo                            |
| estado      | VARCHAR(20)  | Estado: 'activo' o 'inactivo'                    |
| created_at  | TIMESTAMP    | Fecha de creación                                |
| updated_at  | TIMESTAMP    | Fecha de última actualización                    |

### Tabla: `usuarios`

Almacena los usuarios del sistema.

| Campo      | Tipo         | Descripción                                 |
| ---------- | ------------ | ------------------------------------------- |
| id         | SERIAL       | ID único del usuario                        |
| username   | VARCHAR(100) | Nombre de usuario (único)                   |
| password   | VARCHAR(255) | Contraseña (en texto plano para demo)       |
| nombre     | VARCHAR(255) | Nombre completo del usuario                 |
| estado     | VARCHAR(20)  | Estado: 'activo' o 'inactivo'               |
| grupo_id   | INTEGER      | ID del grupo al que pertenece (FK a grupos) |
| created_at | TIMESTAMP    | Fecha de creación                           |
| updated_at | TIMESTAMP    | Fecha de última actualización               |

### Tabla: `grupos_reportes` (Tabla Intermedia de Permisos)

Define qué reportes puede acceder cada grupo y con qué permisos.

| Campo          | Tipo         | Descripción                |
| -------------- | ------------ | -------------------------- |
| id             | SERIAL       | ID único del permiso       |
| grupo_id       | INTEGER      | ID del grupo (FK a grupos) |
| reporte_codigo | VARCHAR(100) | Código del reporte         |
| puede_ver      | BOOLEAN      | Permiso de visualización   |
| puede_crear    | BOOLEAN      | Permiso de creación        |
| puede_editar   | BOOLEAN      | Permiso de edición         |
| puede_eliminar | BOOLEAN      | Permiso de eliminación     |
| created_at     | TIMESTAMP    | Fecha de creación          |

**Constraint:** `UNIQUE(grupo_id, reporte_codigo)` - Un grupo solo puede tener un registro de permisos por reporte.

---

## 🔐 Credenciales por Defecto

### Grupos Creados

1. **Administradores** (codigo: `admin`)
   - Acceso total al sistema
   - Todos los permisos sobre todos los reportes
2. **Usuarios Generales** (codigo: `usuarios`)
   - Permisos básicos de visualización
   - Sin permisos asignados por defecto

### Usuario Admin

- **Usuario:** `admin`
- **Contraseña:** `admin123`
- **Grupo:** Administradores
- **Estado:** Activo

---

## 🌐 Endpoints API

### Autenticación

#### `POST /api/auth/login`

Autenticar un usuario.

**Request:**

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**

```json
{
  "success": true,
  "usuario": {
    "id": 1,
    "username": "admin",
    "nombre": "Administrador del Sistema",
    "estado": "activo",
    "grupo_id": 1,
    "grupo_codigo": "admin",
    "grupo_nombre": "Administradores"
  },
  "message": "Bienvenido Administrador del Sistema"
}
```

---

### Gestión de Usuarios

#### `GET /api/usuarios`

Listar todos los usuarios.

#### `POST /api/usuarios`

Crear un nuevo usuario.

**Request:**

```json
{
  "username": "usuario1",
  "password": "pass123",
  "nombre": "Juan Pérez",
  "grupo_id": 2,
  "estado": "activo"
}
```

#### `PUT /api/usuarios/{user_id}`

Actualizar un usuario existente.

**Request:**

```json
{
  "nombre": "Juan Carlos Pérez",
  "estado": "activo",
  "grupo_id": 1
}
```

---

### Gestión de Grupos

#### `GET /api/grupos`

Listar todos los grupos.

**Response:**

```json
[
  {
    "id": 1,
    "codigo": "admin",
    "nombre": "Administradores",
    "descripcion": "Grupo con acceso total",
    "estado": "activo",
    "total_usuarios": 1
  }
]
```

#### `POST /api/grupos`

Crear un nuevo grupo.

**Request:**

```json
{
  "codigo": "ventas",
  "nombre": "Equipo de Ventas",
  "descripcion": "Acceso a reportes de ventas",
  "estado": "activo"
}
```

#### `PUT /api/grupos/{grupo_id}`

Actualizar un grupo.

---

### Gestión de Permisos

#### `GET /api/permisos/grupo/{grupo_id}`

Obtener todos los permisos de un grupo.

#### `POST /api/permisos/grupo/{grupo_id}/reporte/{reporte_codigo}`

Asignar o actualizar permisos de un grupo sobre un reporte.

**Request:**

```json
{
  "puede_ver": true,
  "puede_crear": false,
  "puede_editar": false,
  "puede_eliminar": false
}
```

#### `DELETE /api/permisos/grupo/{grupo_id}/reporte/{reporte_codigo}`

Eliminar permisos de un grupo sobre un reporte.

#### `GET /api/permisos/usuario/{user_id}/reportes`

Obtener todos los reportes que un usuario puede ver.

**Response:**

```json
[
  {
    "id": 1,
    "codigo": "facturacion_diaria",
    "nombre": "Facturación Diaria",
    "descripcion": "...",
    "activo": true
  }
]
```

---

## 💻 Páginas Web

### `/login`

Página de inicio de sesión.

- Formulario de username/password
- Validación de credenciales
- Almacena datos del usuario en localStorage
- Redirección automática según el grupo

### `/` (Index)

Portal principal para usuarios.

- Muestra reportes permitidos según permisos
- Requiere autenticación

### `/admin`

Panel de administración.

- Gestión de reportes
- Gestión de usuarios
- Gestión de grupos
- Gestión de permisos

---

## 🔧 Métodos del DatabaseManager

### Autenticación

- `autenticar_usuario(username, password)` - Valida credenciales

### Usuarios

- `crear_usuario(username, password, nombre, grupo_id, estado)` - Crea usuario
- `obtener_usuarios()` - Lista todos los usuarios
- `actualizar_usuario(user_id, datos)` - Actualiza usuario

### Grupos

- `crear_grupo(codigo, nombre, descripcion, estado)` - Crea grupo
- `obtener_grupos()` - Lista todos los grupos
- `actualizar_grupo(grupo_id, datos)` - Actualiza grupo

### Permisos

- `asignar_permiso_grupo(grupo_id, reporte_codigo, ...)` - Asigna permisos
- `obtener_permisos_grupo(grupo_id)` - Lista permisos de un grupo
- `obtener_reportes_permitidos_usuario(user_id)` - Reportes del usuario
- `verificar_permiso_usuario(user_id, reporte_codigo, accion)` - Verifica permiso
- `eliminar_permiso_grupo(grupo_id, reporte_codigo)` - Elimina permiso

---

## 🚀 Cómo Usar

### 1. Iniciar Sesión

```
http://localhost:5000/login
Usuario: admin
Password: admin123
```

### 2. Crear un Nuevo Grupo

```bash
curl -X POST http://localhost:5000/api/grupos \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "ventas",
    "nombre": "Equipo de Ventas",
    "descripcion": "Acceso a reportes de ventas"
  }'
```

### 3. Crear un Usuario

```bash
curl -X POST http://localhost:5000/api/usuarios \
  -H "Content-Type: application/json" \
  -d '{
    "username": "vendedor1",
    "password": "venta123",
    "nombre": "Carlos Vendedor",
    "grupo_id": 3
  }'
```

### 4. Asignar Permisos a un Grupo

```bash
curl -X POST http://localhost:5000/api/permisos/grupo/3/reporte/facturacion_diaria \
  -H "Content-Type: application/json" \
  -d '{
    "puede_ver": true,
    "puede_crear": false,
    "puede_editar": false,
    "puede_eliminar": false
  }'
```

### 5. Consultar Reportes de un Usuario

```bash
curl http://localhost:5000/api/permisos/usuario/2/reportes
```

---

## 📝 Flujo de Autenticación

```
1. Usuario ingresa a /login
2. Completa formulario (username/password)
3. POST /api/auth/login valida credenciales
4. Si es válido:
   - Devuelve datos del usuario con grupo
   - Frontend guarda en localStorage
   - Redirige a /admin (admin) o / (usuario)
5. Las páginas verifican autenticación
6. API filtra reportes según permisos del grupo
```

---

## 🔒 Seguridad

⚠️ **IMPORTANTE - Para Producción:**

1. **Hashear Passwords:** Implementar bcrypt o similar

   ```python
   import bcrypt
   hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
   ```

2. **Tokens JWT:** Implementar autenticación basada en tokens
3. **HTTPS:** Usar conexiones seguras
4. **Validación:** Validar todos los inputs
5. **CORS:** Configurar adecuadamente
6. **Rate Limiting:** Limitar intentos de login

---

## 📊 Estado Actual

✅ Tablas creadas
✅ Grupos por defecto creados (admin, usuarios)
✅ Usuario admin creado
✅ Permisos asignados al grupo admin
✅ API de autenticación funcionando
✅ API de gestión de usuarios funcionando
✅ API de gestión de grupos funcionando
✅ API de gestión de permisos funcionando
✅ Página de login creada

---

## 🔄 Próximos Pasos Sugeridos

1. **Proteger Rutas:** Agregar middleware de autenticación
2. **Implementar JWT:** Para sesiones más seguras
3. **Hashear Passwords:** Usar bcrypt
4. **Actualizar Frontend:** Filtrar reportes según permisos
5. **Panel de Administración:** UI para gestionar usuarios/grupos/permisos
6. **Logs de Auditoría:** Registrar acciones de usuarios
7. **Recuperación de Password:** Sistema de reset
8. **Perfiles de Usuario:** Página de configuración personal

---

## 📞 URLs de Acceso

- **Login:** http://localhost:5000/login
- **Portal Usuario:** http://localhost:5000/
- **Admin Panel:** http://localhost:5000/admin
- **API Base:** http://localhost:5000/api/

---

## 🧪 Pruebas de la API

Puedes usar curl o herramientas como Postman/Insomnia para probar la API.

**Ejemplo de Login:**

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```
