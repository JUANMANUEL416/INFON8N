# 🚀 Migración Frontend a Quasar - Sistema de Reportes IA

## 📋 Resumen de la Migración

Se ha completado la migración del frontend de Flask templates (HTML + JS vanilla) a **Quasar Framework (Vue 3)**, proporcionando una interfaz moderna, reactiva y con mejor experiencia de usuario.

---

## ✅ Lo que se ha Implementado

### 1. **Estructura del Proyecto**

```
frontend/
├── src/
│   ├── boot/           # Plugins iniciales
│   │   └── axios.js    # Cliente HTTP con interceptores
│   ├── components/     # Componentes reutilizables
│   │   └── ChatIA.vue  # Chat interactivo con IA
│   ├── css/
│   │   └── app.scss    # Estilos globales
│   ├── layouts/
│   │   └── MainLayout.vue  # Layout principal con drawer
│   ├── pages/
│   │   ├── LoginPage.vue      # Página de inicio de sesión
│   │   ├── UsuarioPage.vue    # Vista del usuario (Chat)
│   │   ├── AdminPage.vue      # Panel administrativo
│   │   └── ErrorNotFound.vue  # Página 404
│   ├── router/
│   │   ├── index.js    # Configuración del router
│   │   └── routes.js   # Definición de rutas
│   ├── stores/
│   │   └── auth.js     # Pinia store para autenticación
│   ├── App.vue         # Componente raíz
│   └── main.js         # Entry point
├── public/             # Assets estáticos
├── Dockerfile          # Multi-stage build con Nginx
├── nginx.conf          # Reverse proxy + SPA routing
├── package.json        # Dependencias
├── quasar.config.js    # Configuración de Quasar
├── jsconfig.json       # Alias de paths
└── .eslintrc.cjs       # Linting rules
```

### 2. **Características Implementadas**

#### 🔐 Autenticación
- Login con validación de credenciales
- Persistencia de sesión con JWT tokens en localStorage
- Interceptores de axios para añadir automáticamente el token
- Guards de navegación para proteger rutas
- Redirección automática a /login si token inválido (401)
- Logout con confirmación

#### 💬 Chat IA (Componente Principal)
- Selector de reportes disponibles
- Interfaz de chat moderna con burbujas de mensajes
- **Memoria conversacional** con session_id único
- Indicador visual de "escribiendo"
- Formateo avanzado de respuestas:
  - Conversión de saltos de línea a `<br>`
  - Listas con viñetas renderizadas
  - Números/montos resaltados
- **Visualización de datos en tablas**
  - Muestra hasta 10 registros en tabla HTML
  - Indica total de registros si hay más
- Scroll automático al enviar/recibir mensajes
- Botón para limpiar conversación
- Muestra código de sesión actual

#### 👤 Vista de Usuario
- Listado de reportes disponibles
- Selector dropdown para cambiar de reporte
- Integración con componente ChatIA
- Mensaje informativo si no hay reportes

#### 👨‍💼 Panel de Administración
- **Tab Sistema**:
  - Vista con 3 tabs: Reportes, Upload, Usuarios
  
- **Gestión de Reportes**:
  - Tabla con listado de reportes
  - Crear nuevo reporte (código, nombre, contexto)
  - Ver detalles de reporte
  - Eliminar with confirmación
  
- **Upload de Datos**:
  - Formulario para subir Excel
  - Campos: código, nombre, contexto, archivo
  - Procesamiento automático con indexación IA
  - Validación de formato (.xlsx, .xls)
  
- **Gestión de Usuarios**:
  - Tabla de usuarios
  - Crear nuevos usuarios
  - Roles: user / admin con badges

#### 🎨 UI/UX
- **Quasar Material Design**
- Drawer lateral colapsable
- Header con nombre de usuario
- Iconografía Material Icons + MDI + FontAwesome
- Responsive design (mobile, tablet, desktop)
- Loading states y notificaciones toast
- Diálogos de confirmación
- Scrollbar personalizado
- Gradientes y sombras modernas

### 3. **Integración con Backend**

El frontend consume la API del backend Flask:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/login` | Autenticación de usuarios |
| GET | `/api/reportes` | Listar reportes disponibles |
| POST | `/api/reportes` | Crear nuevo reporte |
| DELETE | `/api/reportes/:codigo` | Eliminar reporte |
| POST | `/upload` | Subir archivo Excel y procesar |
| POST | `/api/analysis/:codigo/pregunta` | Consultar al agente IA |
| DELETE | `/api/analysis/:codigo/session/:session_id/limpiar` | Limpiar sesión de chat |
| GET | `/api/usuarios` | Listar usuarios |
| POST | `/api/usuarios` | Crear usuario |

### 4. **Configuración Docker**

#### Dockerfile Multi-Stage
1. **Build stage**: Instala dependencias y compila app con Vite
2. **Production stage**: Nginx sirviendo archivos estáticos

#### nginx.conf
- Proxy reverso para `/api`, `/upload`, `/webhook` → backend:5000
- Compresión gzip habilitada
- Cache de assets estáticos (1 año)
- Soporte SPA: todas las rutas → index.html
- Client max body size: 50MB para uploads

#### docker-compose.yml
```yaml
frontend:
  build: ./frontend
  container_name: devprueba-frontend
  ports:
    - "8080:80"
  environment:
    - API_URL=http://backend:5000
  depends_on:
    - backend
  networks:
    - devprueba-net
```

---

## 🚀 Cómo Usar

### Desarrollo Local

```bash
# 1. Ir al directorio del frontend
cd frontend

# 2. Instalar dependencias
npm install

# 3. Ejecutar en modo desarrollo
npm run dev
```

Accede a: `http://localhost:8080`

### Con Docker

```bash
# Desde la raíz del proyecto
docker-compose up -d frontend

# O reconstruir si hay cambios
docker-compose up -d --build frontend
```

Accede a: `http://localhost:8080`

### Build de Producción

```bash
cd frontend
npm run build
```

Los archivos compilados estarán en `dist/spa/`

---

## 📊 Comparación: Antes vs Después

| Aspecto | Flask Templates (Antes) | Quasar (Ahora) |
|---------|------------------------|----------------|
| **Framework** | Jinja2 + jQuery | Vue 3 + Quasar |
| **Arquitectura** | Server-side rendering | SPA (Client-side) |
| **Estado** | Variables globales JS | Pinia stores |
| **Routing** | Flask routes | Vue Router |
| **UI/UX** | CSS custom | Material Design |
| **Reactividad** | Manual DOM manipulation | Vue reactivity |
| **Componentes** | HTML repetido | Componentes reutilizables |
| **Build** | Sin build process | Vite optimizado |
| **TypeScript** | No soportado | Soportado (opcional) |
| **Mobile** | Básico responsive | PWA ready |

---

## 🎯 Funcionalidades Clave del Chat IA

### Session Management
```javascript
// Genera ID único por conversación
sessionId: 'session_1234567890_abc123'

// Se envía en cada pregunta
POST /api/analysis/facturacion/pregunta
{
  "pregunta": "¿Cuál es el total facturado?",
  "session_id": "session_1234567890_abc123"
}
```

### Formateo de Respuestas
El componente ChatIA formatea automáticamente:
- **Saltos de línea** → `<br>`
- **Listas con -** → `<ul><li>...</li></ul>`
- **Montos $123,456** → Resaltado en verde

### Visualización de Datos
Si la IA devuelve datos estructurados:
```json
{
  "respuesta": "Aquí están los resultados:",
  "datos": [
    {"cliente": "ABC", "monto": 15000},
    {"cliente": "XYZ", "monto": 22000}
  ]
}
```

Se renderiza automáticamente como tabla HTML.

---

## 🔧 Configuración

### Variables de Entorno

Crea `.env` en `frontend/` (basado en `.env.example`):

```bash
API_URL=http://localhost:5000
```

En producción/Docker, se define en `docker-compose.yml`.

### Quasar Config

Archivo `quasar.config.js`:
- **Plugins**: Notify, Loading, Dialog, LocalStorage
- **Puerto dev**: 8080
- **Extras**: Material Icons, MDI, FontAwesome
- **Build target**: ES2019+, navegadores modernos

---

## 🐛 Troubleshooting

### Error: CORS al hacer login

Si ves errores CORS, verifica que nginx.conf tenga:
```nginx
location /login {
    proxy_pass http://backend:5000;
    ...
}
```

### Chat no muestra respuestas

1. Verifica que el backend esté corriendo: `http://localhost:5000/api/reportes`
2. Revisa la consola del navegador (F12)
3. Confirma que existe el endpoint: `/api/analysis/:codigo/pregunta`

### No se suben archivos

- Verifica `client_max_body_size 50M;` en nginx.conf
- Revisa que el FormData se envíe correctamente
- Chequea permisos del backend en `/upload`

### Frontend no carga en Docker

```bash
# Ver logs
docker logs devprueba-frontend

# Reconstruir
docker-compose up -d --build frontend
```

---

## 📚 Recursos y Documentación

- **Quasar Framework**: https://quasar.dev/
- **Vue 3**: https://vuejs.org/
- **Pinia**: https://pinia.vuejs.org/
- **Vue Router**: https://router.vuejs.org/

---

## 🎨 Personalización

### Cambiar Colores

Edita `src/css/app.scss`:
```scss
$primary: #667eea;
$secondary: #764ba2;
$accent: #9C27B0;
```

### Agregar Nuevas Páginas

1. Crea el componente en `src/pages/MiPagina.vue`
2. Añade la ruta en `src/router/routes.js`:
```javascript
{
  path: '/mi-pagina',
  component: () => import('pages/MiPagina.vue'),
  meta: { requiresAuth: true }
}
```
3. Agrega link en `MainLayout.vue`

### Crear Componentes

```vue
<!-- src/components/MiComponente.vue -->
<template>
  <q-card>
    <q-card-section>
      {{ mensaje }}
    </q-card-section>
  </q-card>
</template>

<script>
import { defineComponent, ref } from 'vue';

export default defineComponent({
  name: 'MiComponente',
  
  props: {
    mensaje: String
  },
  
  setup() {
    const contador = ref(0);
    
    return {
      contador
    };
  }
});
</script>
```

---

## ✨ Próximas Mejoras Sugeridas

- [ ] **Gráficos**: Integrar Chart.js para visualizaciones
- [ ] **Export PDF**: Exportar conversaciones del chat
- [ ] **Dark Mode**: Tema oscuro switcheable
- [ ] **WebSockets**: Notificaciones en tiempo real
- [ ] **PWA**: Installable Progressive Web App
- [ ] **i18n**: Soporte multi-idioma
- [ ] **Tests**: Unit tests con Vitest + E2E con Cypress
- [ ] **Analytics**: Google Analytics o Matomo
- [ ] **Drag & Drop**: Upload de archivos con drag & drop
- [ ] **Voice Input**: Hablar preguntas al IA

---

## 📄 Migración Completada

✅ **Frontend totalmente funcional en Quasar**  
✅ **Integración completa con backend Flask**  
✅ **Docker configurado con Nginx**  
✅ **Autenticación y autorización**  
✅ **Chat IA con memoria conversacional**  
✅ **Panel de administración completo**  
✅ **Responsive y optimizado**  

El sistema está listo para desarrollo y producción.

---

**Desarrollado para DevPrueba**  
**Versión:** 1.0.0  
**Fecha:** 2024
