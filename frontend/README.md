# Frontend - Sistema de Reportes IA

Frontend moderno desarrollado con Quasar Framework (Vue 3) para el Sistema Dinámico de Reportes con IA.

## 🚀 Características

- **Interface moderna** con Material Design (Quasar Framework)
- **Vue 3 + Composition API** para código reactivo y mantenible
- **Pinia** para gestión de estado global
- **Vue Router** para navegación SPA
- **Axios** configurado con interceptores de autenticación
- **Chat IA interactivo** con memoria conversacional
- **Panel de administración** completo
- **Responsive design** - funciona en móvil, tablet y desktop

## 📂 Estructura del Proyecto

```
frontend/
├── src/
│   ├── boot/           # Configuración de plugins (axios)
│   ├── components/     # Componentes Vue reutilizables
│   │   └── ChatIA.vue  # Componente del chat IA
│   ├── css/            # Estilos globales
│   │   └── app.scss
│   ├── layouts/        # Layouts de la aplicación
│   │   └── MainLayout.vue
│   ├── pages/          # Páginas/Vistas
│   │   ├── LoginPage.vue
│   │   ├── UsuarioPage.vue
│   │   ├── AdminPage.vue
│   │   └── ErrorNotFound.vue
│   ├── router/         # Configuración de rutas
│   │   ├── index.js
│   │   └── routes.js
│   ├── stores/         # Stores de Pinia
│   │   └── auth.js     # Store de autenticación
│   ├── App.vue         # Componente raíz
│   └── main.js         # Punto de entrada
├── public/             # Archivos estáticos
├── Dockerfile          # Dockerfile para producción
├── nginx.conf          # Configuración de Nginx
├── package.json        # Dependencias
└── quasar.config.js    # Configuración de Quasar
```

## 🛠️ Desarrollo Local

### Requisitos

- Node.js 18+ y npm

### Instalación

```bash
cd frontend
npm install
```

### Ejecutar en desarrollo

```bash
npm run dev
```

La aplicación estará disponible en `http://localhost:8080`

### Build para producción

```bash
npm run build
```

Los archivos se generarán en `dist/spa/`

## 🐳 Docker

### Build de la imagen

```bash
docker build -t sistema-reportes-frontend .
```

### Ejecutar contenedor

```bash
docker run -p 8080:80 sistema-reportes-frontend
```

## 🔧 Configuración

### Variables de Entorno

El frontend se comunica con el backend a través de la variable `API_URL`:

- **Desarrollo**: Configurada en `quasar.config.js` (por defecto `http://localhost:5000`)
- **Producción**: Definida en `docker-compose.yml` o como variable de entorno

### Nginx

La configuración de Nginx (`nginx.conf`) incluye:

- Proxy reverso para peticiones `/api`, `/upload`, `/webhook` al backend
- Compresión gzip para mejor rendimiento
- Cache de assets estáticos
- Soporte para SPA (redirige todas las rutas a index.html)

## 📱 Funcionalidades

### Para Usuarios

1. **Login/Autenticación**
   - Inicio de sesión con usuario y contraseña
   - Persistencia de sesión con tokens
   - Logout seguro

2. **Chat IA**
   - Selección de reportes disponibles
   - Conversación natural con memoria de contexto
   - Visualización de datos en tablas
   - Formateado de respuestas con resaltado
   - Limpieza de conversaciones
   - Gestión de sesiones

### Para Administradores

3. **Panel de Administración**
   - **Reportes**: Crear, ver y eliminar reportes
   - **Upload**: Subir archivos Excel con auto-indexación
   - **Usuarios**: Gestionar usuarios del sistema

## 🎨 Componentes Principales

### ChatIA.vue

Componente del chat interactivo con IA:

- Gestión de sesiones
- Historial de mensajes
- Indicador de escritura
- Scroll automático
- Formateo de respuestas HTML
- Visualización de datos en tablas
- Integración con OpenAI Function Calling

### MainLayout.vue

Layout principal con:

- Header con información de usuario
- Drawer lateral con navegación
- Control de acceso por roles
- Logout confirmado

## 🔐 Autenticación

El sistema usa JWT tokens almacenados en localStorage:

- **Interceptor de Request**: Añade token a headers automáticamente
- **Interceptor de Response**: Redirige a login si token inválido (401)
- **Router Guards**: Protege rutas que requieren autenticación

## 📊 Integración con Backend

El frontend consume los siguientes endpoints del backend:

- `POST /login` - Autenticación
- `GET /api/reportes` - Listar reportes
- `POST /api/reportes` - Crear reporte
- `DELETE /api/reportes/:codigo` - Eliminar reporte
- `POST /upload` - Subir Excel
- `POST /api/analysis/:codigo/pregunta` - Consultar IA
- `DELETE /api/analysis/:codigo/session/:session_id/limpiar` - Limpiar sesión
- `GET /api/usuarios` - Listar usuarios
- `POST /api/usuarios` - Crear usuario

## 🎯 Próximas Mejoras

- [ ] Gráficos con Chart.js para visualización de datos
- [ ] Export de conversaciones a PDF
- [ ] Temas claro/oscuro
- [ ] Notificaciones en tiempo real
- [ ] PWA (Progressive Web App)
- [ ] Tests unitarios con Vitest
- [ ] Tests E2E con Cypress

## 📄 Licencia

Uso interno - DevPrueba

## 🤝 Contribución

Frontend desarrollado para integración con backend Flask + ChromaDB + OpenAI GPT-4o
