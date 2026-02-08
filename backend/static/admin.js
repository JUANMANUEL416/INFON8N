// Variables globales
let reportesCargados = [];
let campoCounter = 0;
let relacionCounter = 0;
let usuarioActual = null;

// Inicialización
document.addEventListener("DOMContentLoaded", function () {
  // Verificar autenticación
  if (!verificarAutenticacion()) {
    window.location.href = "/login";
    return;
  }

  cargarReportes();
  setupNavigation();
  setupExcelUpload();
  mostrarInfoUsuario();

  // Form submit
  document
    .getElementById("form-nuevo-reporte")
    .addEventListener("submit", guardarNuevoReporte);
});

// Verificar autenticación
function verificarAutenticacion() {
  const usuarioStr = localStorage.getItem("usuario");
  if (!usuarioStr) {
    return false;
  }

  try {
    usuarioActual = JSON.parse(usuarioStr);

    // Verificar que sea admin
    if (usuarioActual.grupo_codigo !== "admin") {
      alert("⚠️ No tienes permisos de administrador");
      window.location.href = "/";
      return false;
    }

    return true;
  } catch (e) {
    return false;
  }
}

// Mostrar información del usuario
function mostrarInfoUsuario() {
  const userInfo = document.querySelector(".user-info p");
  if (userInfo && usuarioActual) {
    userInfo.textContent = `👤 ${usuarioActual.nombre}`;
  }
}

// Cerrar sesión
function cerrarSesion() {
  localStorage.removeItem("usuario");
  window.location.href = "/login";
}

// Navegación entre secciones
function setupNavigation() {
  document.querySelectorAll(".menu li").forEach((item) => {
    item.addEventListener("click", function () {
      const section = this.getAttribute("data-section");
      cambiarSeccion(section);
    });
  });
}

function cambiarSeccion(section) {
  // Actualizar menú
  document
    .querySelectorAll(".menu li")
    .forEach((li) => li.classList.remove("active"));
  document.querySelector(`[data-section="${section}"]`).classList.add("active");

  // Mostrar sección
  document
    .querySelectorAll(".section")
    .forEach((s) => s.classList.remove("active"));
  document.getElementById(`${section}-section`).classList.add("active");
}

// Cargar reportes
async function cargarReportes() {
  try {
    const response = await fetch("/api/admin/reportes");
    if (!response.ok) throw new Error("Error cargando reportes");

    reportesCargados = await response.json();
    mostrarReportes();
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al cargar reportes", "error");
  }
}

function mostrarReportes() {
  const grid = document.getElementById("reportes-grid");

  if (reportesCargados.length === 0) {
    grid.innerHTML = `
            <div class="empty-state">
                <h3>📊 No hay reportes creados</h3>
                <p>Crea tu primer reporte haciendo clic en "Crear Nuevo Reporte"</p>
            </div>
        `;
    return;
  }

  grid.innerHTML = reportesCargados
    .map(
      (reporte) => `
        <div class="reporte-card ${reporte.activo ? "" : "inactive"}">
            <div class="reporte-header">
                <span class="reporte-icono">${reporte.icono}</span>
                <div class="reporte-info">
                    <h3>${reporte.nombre}</h3>
                    <span class="badge">${reporte.categoria}</span>
                </div>
            </div>
            
            <div class="reporte-body">
                <p>${reporte.descripcion || "Sin descripción"}</p>
                
                <div class="reporte-meta">
                    <div>
                        <strong>Código:</strong> ${reporte.codigo}
                    </div>
                    <div>
                        <strong>Campos:</strong> ${reporte.campos ? (typeof reporte.campos === "string" ? JSON.parse(reporte.campos).length : reporte.campos.length) : 0}
                    </div>
                </div>
                
                ${
                  reporte.contexto
                    ? `
                    <div class="reporte-contexto">
                        <strong>Contexto:</strong>
                        <p>${reporte.contexto.substring(0, 150)}...</p>
                    </div>
                `
                    : ""
                }
            </div>
            
            <div class="reporte-actions">
                <button class="btn-icon" onclick="verDatos('${reporte.codigo}')" title="Ver datos">
                    📊
                </button>
                <button class="btn-icon" onclick="editarReporte('${reporte.codigo}')" title="Editar">
                    ✏️
                </button>
                <button class="btn-icon" onclick="descargarPlantilla('${reporte.codigo}')" title="Descargar plantilla">
                    ⬇️
                </button>
                <button class="btn-icon danger" onclick="eliminarReporte('${reporte.codigo}')" title="Eliminar">
                    🗑️
                </button>
            </div>
        </div>
    `,
    )
    .join("");
}

function abrirModalNuevoReporte() {
  document.getElementById("modal-nuevo-reporte").classList.add("show");
  document.getElementById("form-nuevo-reporte").reset();
  document.getElementById("campos-container").innerHTML = "";
  document.getElementById("relaciones-container").innerHTML = "";
  document.getElementById("excel-result").style.display = "none";
  campoCounter = 0;
  relacionCounter = 0;

  // Agregar primer campo por defecto
  agregarCampo();
}

// Configurar carga de Excel
function setupExcelUpload() {
  // Los elementos del modal se crean dinámicamente, usar event delegation
  document.addEventListener("click", function (e) {
    if (e.target.closest("#excel-dropzone")) {
      const fileInput = document.getElementById("excel-input");
      if (fileInput) fileInput.click();
    }
  });

  document.addEventListener("dragover", function (e) {
    const dropzone = e.target.closest("#excel-dropzone");
    if (dropzone) {
      e.preventDefault();
      dropzone.classList.add("dragover");
    }
  });

  document.addEventListener("dragleave", function (e) {
    const dropzone = e.target.closest("#excel-dropzone");
    if (dropzone) {
      dropzone.classList.remove("dragover");
    }
  });

  document.addEventListener("drop", function (e) {
    const dropzone = e.target.closest("#excel-dropzone");
    if (dropzone) {
      e.preventDefault();
      dropzone.classList.remove("dragover");

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        procesarExcel(files[0]);
      }
    }
  });

  document.addEventListener("change", function (e) {
    if (e.target.id === "excel-input" && e.target.files.length > 0) {
      procesarExcel(e.target.files[0]);
    }
  });
}

// Procesar Excel y extraer campos
async function procesarExcel(file) {
  if (!file.name.endsWith(".xlsx")) {
    mostrarAlerta("Por favor selecciona un archivo .xlsx", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    // Mostrar loading
    const dropzone = document.getElementById("excel-dropzone");
    dropzone.innerHTML = '<p class="loading">📊 Analizando Excel...</p>';

    const response = await fetch("/api/admin/analizar-excel", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Error al analizar Excel");
    }

    const result = await response.json();

    // Limpiar campos existentes
    document.getElementById("campos-container").innerHTML = "";
    campoCounter = 0;

    // Agregar campos detectados
    result.campos.forEach((campo) => {
      agregarCampoDesdeExcel(campo);
    });

    // Mostrar resultado
    document.getElementById("excel-msg").textContent = result.message;
    document.getElementById("excel-result").style.display = "block";
    dropzone.style.display = "none";

    mostrarAlerta(
      `✅ ${result.total_campos} campos detectados automáticamente`,
      "success",
    );
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al procesar Excel: " + error.message, "error");

    // Restaurar dropzone
    const dropzone = document.getElementById("excel-dropzone");
    dropzone.innerHTML = `
            <span class="upload-icon">📁</span>
            <p>Arrastra tu Excel aquí o haz clic para seleccionar</p>
            <small>El archivo debe tener los encabezados y al menos una fila con datos de ejemplo</small>
        `;
  }
}

// Agregar campo desde datos del Excel
function agregarCampoDesdeExcel(campo) {
  const container = document.getElementById("campos-container");
  const id = campoCounter++;

  const campoHtml = `
        <div class="campo-item" data-id="${id}">
            <div class="campo-header">
                <span>Campo ${id + 1}: ${campo.etiqueta}</span>
                <button type="button" class="btn-remove" onclick="eliminarCampo(${id})">×</button>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>Nombre Técnico *</label>
                    <input type="text" name="campo_nombre_${id}" required value="${
                      campo.nombre
                    }">
                </div>
                <div class="form-group">
                    <label>Etiqueta *</label>
                    <input type="text" name="campo_etiqueta_${id}" required value="${
                      campo.etiqueta
                    }">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>Tipo de Dato</label>
                    <select name="campo_tipo_${id}">
                        <option value="texto" ${
                          campo.tipo_dato === "texto" ? "selected" : ""
                        }>Texto</option>
                        <option value="numero" ${
                          campo.tipo_dato === "numero" ? "selected" : ""
                        }>Número</option>
                        <option value="decimal" ${
                          campo.tipo_dato === "decimal" ? "selected" : ""
                        }>Decimal</option>
                        <option value="fecha" ${
                          campo.tipo_dato === "fecha" ? "selected" : ""
                        }>Fecha</option>
                        <option value="booleano" ${
                          campo.tipo_dato === "booleano" ? "selected" : ""
                        }>Sí/No</option>
                        <option value="email" ${
                          campo.tipo_dato === "email" ? "selected" : ""
                        }>Email</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="campo_obligatorio_${id}" ${
                          campo.obligatorio ? "checked" : ""
                        }>
                        Obligatorio
                    </label>
                </div>
            </div>
            
            <div class="form-group">
                <label>Descripción</label>
                <input type="text" name="campo_descripcion_${id}" value="${
                  campo.descripcion || ""
                }">
            </div>
            
            <div class="form-group">
                <label>Ejemplo</label>
                <input type="text" name="campo_ejemplo_${id}" value="${
                  campo.ejemplo || ""
                }">
            </div>
        </div>
    `;

  container.insertAdjacentHTML("beforeend", campoHtml);
}

// Limpiar Excel y volver a modo manual
function limpiarExcel() {
  document.getElementById("excel-result").style.display = "none";
  document.getElementById("excel-dropzone").style.display = "block";
  document.getElementById("excel-input").value = "";
  document.getElementById("campos-container").innerHTML = "";
  campoCounter = 0;

  // Agregar un campo vacío
  agregarCampo();
}

// Modal nuevo reporte
function abrirModalNuevoReporte() {
  document.getElementById("modal-nuevo-reporte").classList.add("show");
  document.getElementById("form-nuevo-reporte").reset();
  document.getElementById("campos-container").innerHTML = "";
  document.getElementById("relaciones-container").innerHTML = "";
  campoCounter = 0;
  relacionCounter = 0;

  // Agregar primer campo por defecto
  agregarCampo();
}

function cerrarModal() {
  document.getElementById("modal-nuevo-reporte").classList.remove("show");
}

// Gestión de campos
function agregarCampo() {
  const container = document.getElementById("campos-container");
  const id = campoCounter++;

  const campoHtml = `
        <div class="campo-item" data-id="${id}">
            <div class="campo-header">
                <span>Campo ${id + 1}</span>
                <button type="button" class="btn-remove" onclick="eliminarCampo(${id})">×</button>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>Nombre Técnico *</label>
                    <input type="text" name="campo_nombre_${id}" required placeholder="ej: numero_factura">
                </div>
                <div class="form-group">
                    <label>Etiqueta *</label>
                    <input type="text" name="campo_etiqueta_${id}" required placeholder="ej: Número de Factura">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>Tipo de Dato</label>
                    <select name="campo_tipo_${id}">
                        <option value="texto">Texto</option>
                        <option value="numero">Número</option>
                        <option value="decimal">Decimal</option>
                        <option value="fecha">Fecha</option>
                        <option value="booleano">Sí/No</option>
                        <option value="email">Email</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="campo_obligatorio_${id}">
                        Obligatorio
                    </label>
                </div>
            </div>
            
            <div class="form-group">
                <label>Descripción</label>
                <input type="text" name="campo_descripcion_${id}" placeholder="Descripción del campo">
            </div>
            
            <div class="form-group">
                <label>Ejemplo</label>
                <input type="text" name="campo_ejemplo_${id}" placeholder="Valor de ejemplo">
            </div>
        </div>
    `;

  container.insertAdjacentHTML("beforeend", campoHtml);
}

function eliminarCampo(id) {
  const campo = document.querySelector(`.campo-item[data-id="${id}"]`);
  if (campo) campo.remove();
}

// Gestión de relaciones
function agregarRelacion() {
  const container = document.getElementById("relaciones-container");
  const id = relacionCounter++;

  const relacionHtml = `
        <div class="relacion-item" data-id="${id}">
            <div class="campo-header">
                <span>Relación ${id + 1}</span>
                <button type="button" class="btn-remove" onclick="eliminarRelacion(${id})">×</button>
            </div>
            
            <div class="form-group">
                <label>Reporte Destino</label>
                <input type="text" name="rel_destino_${id}" placeholder="Código del reporte relacionado">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>Campo Origen</label>
                    <input type="text" name="rel_campo_origen_${id}" placeholder="Campo en este reporte">
                </div>
                <div class="form-group">
                    <label>Campo Destino</label>
                    <input type="text" name="rel_campo_destino_${id}" placeholder="Campo en reporte destino">
                </div>
            </div>
            
            <div class="form-group">
                <label>Descripción de la relación</label>
                <input type="text" name="rel_descripcion_${id}" placeholder="Ej: Relacionado por número de cliente">
            </div>
        </div>
    `;

  container.insertAdjacentHTML("beforeend", relacionHtml);
}

function eliminarRelacion(id) {
  const relacion = document.querySelector(`.relacion-item[data-id="${id}"]`);
  if (relacion) relacion.remove();
}

// Guardar nuevo reporte
async function guardarNuevoReporte(e) {
  e.preventDefault();

  const formData = new FormData(e.target);

  // Construir objeto de reporte
  const reporte = {
    nombre: formData.get("nombre"),
    codigo: formData.get("codigo"),
    categoria: formData.get("categoria"),
    icono: formData.get("icono"),
    descripcion: formData.get("descripcion"),
    contexto: formData.get("contexto"),
    api_endpoint: formData.get("api_endpoint") || null,
    query_template: formData.get("query_template") || null,
    campos: [],
    relaciones: [],
  };

  // Extraer campos
  document.querySelectorAll(".campo-item").forEach((campo) => {
    const id = campo.getAttribute("data-id");
    reporte.campos.push({
      nombre: formData.get(`campo_nombre_${id}`),
      etiqueta: formData.get(`campo_etiqueta_${id}`),
      tipo_dato: formData.get(`campo_tipo_${id}`),
      obligatorio: formData.get(`campo_obligatorio_${id}`) === "on",
      descripcion: formData.get(`campo_descripcion_${id}`) || "",
      ejemplo: formData.get(`campo_ejemplo_${id}`) || "",
      orden: parseInt(id),
    });
  });

  // Extraer relaciones
  document.querySelectorAll(".relacion-item").forEach((relacion) => {
    const id = relacion.getAttribute("data-id");
    const destino = formData.get(`rel_destino_${id}`);
    if (destino) {
      reporte.relaciones.push({
        reporte_destino: destino,
        campo_origen: formData.get(`rel_campo_origen_${id}`),
        campo_destino: formData.get(`rel_campo_destino_${id}`),
        descripcion: formData.get(`rel_descripcion_${id}`) || "",
      });
    }
  });

  try {
    const response = await fetch("/api/admin/reportes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(reporte),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Error al crear reporte");
    }

    const result = await response.json();
    mostrarAlerta(result.message, "success");
    cerrarModal();
    cargarReportes();
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta(error.message, "error");
  }
}

// Acciones sobre reportes
async function descargarPlantilla(codigo) {
  window.location.href = `/api/reportes/${codigo}/descargar`;
}

async function verDatos(codigo) {
  cambiarSeccion("datos");

  try {
    const [datosResp, statsResp] = await Promise.all([
      fetch(`/api/reportes/${codigo}/datos?limite=50`),
      fetch(`/api/reportes/${codigo}/estadisticas`),
    ]);

    const datos = await datosResp.json();
    const stats = await statsResp.json();

    const content = document.getElementById("datos-content");
    content.innerHTML = `
            <div class="stats-panel">
                <div class="stat-item">
                    <h3>${stats.total_registros || 0}</h3>
                    <p>Registros Totales</p>
                </div>
                <div class="stat-item">
                    <h3>${stats.primera_carga ? new Date(stats.primera_carga).toLocaleDateString() : "N/A"}</h3>
                    <p>Primera Carga</p>
                </div>
                <div class="stat-item">
                    <h3>${stats.ultima_carga ? new Date(stats.ultima_carga).toLocaleDateString() : "N/A"}</h3>
                    <p>Última Carga</p>
                </div>
            </div>
            
            <div class="datos-table">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Fecha</th>
                            <th>Datos</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${datos
                          .map(
                            (d) => `
                            <tr>
                                <td>${d.id}</td>
                                <td>${new Date(d.created_at).toLocaleString()}</td>
                                <td><pre>${JSON.stringify(d.datos, null, 2)}</pre></td>
                            </tr>
                        `,
                          )
                          .join("")}
                    </tbody>
                </table>
            </div>
        `;
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al cargar datos", "error");
  }
}

async function eliminarReporte(codigo) {
  if (!confirm("¿Estás seguro de que deseas desactivar este reporte?")) return;

  try {
    const response = await fetch(`/api/admin/reportes/${codigo}`, {
      method: "DELETE",
    });

    if (!response.ok) throw new Error("Error al eliminar");

    const result = await response.json();
    mostrarAlerta(result.message, "success");
    cargarReportes();
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al eliminar reporte", "error");
  }
}

// Utilidades
function mostrarAlerta(mensaje, tipo = "info") {
  // Implementar sistema de alertas
  alert(mensaje);
}

// ============================================
// GESTIÓN DE USUARIOS Y GRUPOS
// ============================================

// Tabs
function cambiarTab(tab) {
  document
    .querySelectorAll(".tab-btn")
    .forEach((btn) => btn.classList.remove("active"));
  document
    .querySelectorAll(".tab-content")
    .forEach((content) => content.classList.remove("active"));

  event.target.classList.add("active");
  document.getElementById(`tab-${tab}`).classList.add("active");

  if (tab === "usuarios") cargarUsuarios();
  else if (tab === "grupos") cargarGrupos();
  else if (tab === "permisos") cargarGruposParaPermisos();
}

// Usuarios
async function cargarUsuarios() {
  try {
    const response = await fetch("/api/usuarios");

    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    const usuarios = await response.json();

    const tbody = document.getElementById("usuarios-list");
    if (usuarios.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6">No hay usuarios registrados</td></tr>';
      return;
    }

    tbody.innerHTML = usuarios
      .map(
        (u) => `
      <tr>
        <td><strong>${u.username}</strong></td>
        <td>${u.nombre}</td>
        <td>${u.grupo_nombre || "Sin grupo"}</td>
        <td><span class="badge ${u.estado === "activo" ? "badge-success" : "badge-danger"}">${u.estado}</span></td>
        <td>${new Date(u.created_at).toLocaleDateString()}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="editarUsuario(${u.id})">Editar</button>
        </td>
      </tr>
    `,
      )
      .join("");
  } catch (error) {
    console.error("Error:", error);
    const tbody = document.getElementById("usuarios-list");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="6" style="color: red;">Error al cargar usuarios: ${error.message}</td></tr>`;
    }
    mostrarAlerta("Error al cargar usuarios", "error");
  }
}

function abrirModalNuevoUsuario() {
  cargarGruposSelect("usuario-grupo-select");
  document.getElementById("modal-nuevo-usuario").style.display = "flex";
}

function cerrarModalUsuario() {
  document.getElementById("modal-nuevo-usuario").style.display = "none";
  document.getElementById("form-nuevo-usuario").reset();
}

async function guardarUsuario(e) {
  e.preventDefault();
  const formData = new FormData(e.target);

  const usuario = {
    username: formData.get("username"),
    password: formData.get("password"),
    nombre: formData.get("nombre"),
    grupo_id: parseInt(formData.get("grupo_id")),
    estado: formData.get("estado"),
  };

  try {
    const response = await fetch("/api/usuarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(usuario),
    });

    const result = await response.json();

    if (response.ok) {
      mostrarAlerta(result.message, "success");
      cerrarModalUsuario();
      cargarUsuarios();
    } else {
      mostrarAlerta(result.error, "error");
    }
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al guardar usuario", "error");
  }
}

// Grupos
async function cargarGrupos() {
  try {
    const response = await fetch("/api/grupos");
    const grupos = await response.json();

    const tbody = document.getElementById("grupos-list");
    if (grupos.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6">No hay grupos registrados</td></tr>';
      return;
    }

    tbody.innerHTML = grupos
      .map(
        (g) => `
      <tr>
        <td><code>${g.codigo}</code></td>
        <td><strong>${g.nombre}</strong></td>
        <td>${g.descripcion || "-"}</td>
        <td>${g.total_usuarios || 0}</td>
        <td><span class="badge ${g.estado === "activo" ? "badge-success" : "badge-danger"}">${g.estado}</span></td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="editarGrupo(${g.id})">Editar</button>
        </td>
      </tr>
    `,
      )
      .join("");
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al cargar grupos", "error");
  }
}

function abrirModalNuevoGrupo() {
  document.getElementById("modal-nuevo-grupo").style.display = "flex";
}

function cerrarModalGrupo() {
  document.getElementById("modal-nuevo-grupo").style.display = "none";
  document.getElementById("form-nuevo-grupo").reset();
}

async function guardarGrupo(e) {
  e.preventDefault();
  const formData = new FormData(e.target);

  const grupo = {
    codigo: formData.get("codigo"),
    nombre: formData.get("nombre"),
    descripcion: formData.get("descripcion"),
    estado: formData.get("estado"),
  };

  try {
    const response = await fetch("/api/grupos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(grupo),
    });

    const result = await response.json();

    if (response.ok) {
      mostrarAlerta(result.message, "success");
      cerrarModalGrupo();
      cargarGrupos();
    } else {
      mostrarAlerta(result.error, "error");
    }
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al guardar grupo", "error");
  }
}

// Permisos
async function cargarGruposParaPermisos() {
  try {
    const response = await fetch("/api/grupos");
    const grupos = await response.json();

    const select = document.getElementById("grupo-permisos-select");
    select.innerHTML =
      '<option value="">Seleccione un grupo...</option>' +
      grupos
        .map((g) => `<option value="${g.id}">${g.nombre}</option>`)
        .join("");
  } catch (error) {
    console.error("Error:", error);
  }
}

async function cargarPermisosGrupo() {
  const grupoId = document.getElementById("grupo-permisos-select").value;
  if (!grupoId) {
    document.getElementById("permisos-grid").innerHTML = "";
    return;
  }

  try {
    const [permisosRes, reportesRes] = await Promise.all([
      fetch(`/api/permisos/grupo/${grupoId}`),
      fetch("/api/admin/reportes"),
    ]);

    const permisos = await permisosRes.json();
    const reportes = await reportesRes.json();

    const permisosMap = {};
    permisos.forEach((p) => {
      permisosMap[p.reporte_codigo] = p;
    });

    const grid = document.getElementById("permisos-grid");
    grid.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th>Reporte</th>
            <th>Ver</th>
            <th>Crear</th>
            <th>Editar</th>
            <th>Eliminar</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${reportes
            .map((r) => {
              const p = permisosMap[r.codigo] || {};
              return `
              <tr>
                <td><strong>${r.nombre}</strong></td>
                <td><input type="checkbox" ${p.puede_ver ? "checked" : ""} onchange="actualizarPermiso(${grupoId}, '${r.codigo}', 'puede_ver', this.checked)"></td>
                <td><input type="checkbox" ${p.puede_crear ? "checked" : ""} onchange="actualizarPermiso(${grupoId}, '${r.codigo}', 'puede_crear', this.checked)"></td>
                <td><input type="checkbox" ${p.puede_editar ? "checked" : ""} onchange="actualizarPermiso(${grupoId}, '${r.codigo}', 'puede_editar', this.checked)"></td>
                <td><input type="checkbox" ${p.puede_eliminar ? "checked" : ""} onchange="actualizarPermiso(${grupoId}, '${r.codigo}', 'puede_eliminar', this.checked)"></td>
                <td>
                  ${p.id ? `<button class="btn btn-sm btn-danger" onclick="eliminarPermiso(${grupoId}, '${r.codigo}')">Quitar</button>` : ""}
                </td>
              </tr>
            `;
            })
            .join("")}
        </tbody>
      </table>
    `;
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al cargar permisos", "error");
  }
}

async function actualizarPermiso(grupoId, reporteCodigo, campo, valor) {
  try {
    const permisos = {
      puede_ver: false,
      puede_crear: false,
      puede_editar: false,
      puede_eliminar: false,
    };
    permisos[campo] = valor;

    const response = await fetch(
      `/api/permisos/grupo/${grupoId}/reporte/${reporteCodigo}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(permisos),
      },
    );

    if (response.ok) {
      cargarPermisosGrupo();
    }
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al actualizar permiso", "error");
  }
}

async function eliminarPermiso(grupoId, reporteCodigo) {
  if (!confirm("¿Quitar todos los permisos de este reporte?")) return;

  try {
    const response = await fetch(
      `/api/permisos/grupo/${grupoId}/reporte/${reporteCodigo}`,
      {
        method: "DELETE",
      },
    );

    if (response.ok) {
      mostrarAlerta("Permiso eliminado", "success");
      cargarPermisosGrupo();
    }
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("Error al eliminar permiso", "error");
  }
}

async function cargarGruposSelect(selectId) {
  try {
    const response = await fetch("/api/grupos");
    const grupos = await response.json();

    const select = document.getElementById(selectId);
    select.innerHTML =
      '<option value="">Seleccione un grupo...</option>' +
      grupos
        .map((g) => `<option value="${g.id}">${g.nombre}</option>`)
        .join("");
  } catch (error) {
    console.error("Error:", error);
  }
}

// Cargar usuarios al cambiar a esa sección
document.addEventListener("DOMContentLoaded", function () {
  const menuUsuarios = document.querySelector('[data-section="usuarios"]');
  if (menuUsuarios) {
    menuUsuarios.addEventListener("click", function () {
      cargarUsuarios();
    });
  }

  // Cargar reportes en el select de datos
  const menuDatos = document.querySelector('[data-section="datos"]');
  if (menuDatos) {
    menuDatos.addEventListener("click", function () {
      cargarReportesEnSelect();
    });
  }
});

// ============================================
// SECCIÓN: CONSULTA DE DATOS
// ============================================

let reporteSeleccionadoDatos = null;

async function cargarReportesEnSelect() {
  try {
    const response = await fetch("/api/admin/reportes");
    const reportes = await response.json();

    const select = document.getElementById("select-reporte-datos");
    select.innerHTML =
      '<option value="">-- Seleccione un reporte --</option>' +
      reportes
        .map((r) => `<option value="${r.codigo}">${r.nombre}</option>`)
        .join("");
  } catch (error) {
    console.error("Error:", error);
  }
}

async function cargarDatosReporte() {
  const codigo = document.getElementById("select-reporte-datos").value;

  if (!codigo) {
    document.getElementById("filtros-consulta").style.display = "none";
    document.getElementById("datos-estadisticas").style.display = "none";
    document.getElementById("datos-tabla-container").innerHTML =
      '<p style="color: #999; text-align: center; padding: 40px;">Seleccione un reporte para ver los datos</p>';
    return;
  }

  reporteSeleccionadoDatos = codigo;
  document.getElementById("filtros-consulta").style.display = "block";

  // Cargar estadísticas
  await cargarEstadisticasDatos(codigo);

  // Cargar datos
  await buscarDatos();
}

async function cargarEstadisticasDatos(codigo) {
  try {
    const response = await fetch(`/stats/${encodeURIComponent(codigo)}`);
    const stats = await response.json();

    document.getElementById("datos-estadisticas").style.display = "block";
    document.getElementById("stat-total").textContent = stats.total || 0;
    document.getElementById("stat-fecha").textContent = stats.ultimo_registro
      ? new Date(stats.ultimo_registro).toLocaleString("es")
      : "Sin datos";
  } catch (error) {
    console.error("Error:", error);
  }
}

async function buscarDatos() {
  if (!reporteSeleccionadoDatos) return;

  const limite = document.getElementById("limite-registros").value;
  const fechaDesde = document.getElementById("fecha-desde").value;
  const fechaHasta = document.getElementById("fecha-hasta").value;

  const container = document.getElementById("datos-tabla-container");
  container.innerHTML =
    '<p style="text-align: center; padding: 20px;">⏳ Cargando datos...</p>';

  try {
    let url = `/api/reportes/${encodeURIComponent(reporteSeleccionadoDatos)}/datos?limite=${limite}`;

    if (fechaDesde) url += `&fecha_desde=${fechaDesde}`;
    if (fechaHasta) url += `&fecha_hasta=${fechaHasta}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error("Error al cargar datos");

    const data = await response.json();

    if (data.length === 0) {
      container.innerHTML =
        '<p style="text-align: center; color: #999; padding: 40px;">No hay datos para mostrar</p>';
      return;
    }

    // Obtener todas las columnas
    const columnas = Object.keys(data[0].datos || {});

    // Crear tabla
    let html = `
      <table class="data-table">
        <thead>
          <tr>
            <th>#</th>
            ${columnas.map((col) => `<th>${col}</th>`).join("")}
            <th>Fecha Carga</th>
          </tr>
        </thead>
        <tbody>
          ${data
            .map(
              (registro, idx) => `
            <tr>
              <td>${idx + 1}</td>
              ${columnas.map((col) => `<td>${registro.datos[col] !== null && registro.datos[col] !== undefined ? registro.datos[col] : ""}</td>`).join("")}
              <td>${new Date(registro.created_at).toLocaleString("es")}</td>
            </tr>
          `,
            )
            .join("")}
        </tbody>
      </table>
    `;

    container.innerHTML = html;
  } catch (error) {
    console.error("Error:", error);
    container.innerHTML =
      '<p style="text-align: center; color: red; padding: 20px;">Error al cargar datos</p>';
  }
}

async function exportarDatos() {
  if (!reporteSeleccionadoDatos) {
    mostrarAlerta("Seleccione un reporte primero", "warning");
    return;
  }

  const fechaDesde = document.getElementById("fecha-desde").value;
  const fechaHasta = document.getElementById("fecha-hasta").value;

  let url = `/api/query/${encodeURIComponent(reporteSeleccionadoDatos)}/export?`;

  if (fechaDesde) url += `fecha_inicio=${fechaDesde}&`;
  if (fechaHasta) url += `fecha_fin=${fechaHasta}&`;

  window.open(url, "_blank");
  mostrarAlerta("Descargando archivo...", "success");
}

function mostrarWebhookInfo() {
  if (!reporteSeleccionadoDatos) {
    mostrarAlerta("Seleccione un reporte primero", "warning");
    return;
  }

  const baseUrl = window.location.origin;
  const webhookUrl = `${baseUrl}/api/query/${encodeURIComponent(reporteSeleccionadoDatos)}`;
  const webhookUpload = `${baseUrl}/webhook/upload/${encodeURIComponent(reporteSeleccionadoDatos)}`;

  const mensaje = `
    <div style="text-align: left;">
      <h3>🔗 Endpoints para n8n</h3>
      
      <div style="margin: 15px 0;">
        <strong>Consultar Datos (GET):</strong><br>
        <code style="background: #f4f4f4; padding: 8px; display: block; margin-top: 5px; word-break: break-all;">
          ${webhookUrl}
        </code>
        <p style="font-size: 0.9em; color: #666; margin-top: 5px;">
          Parámetros opcionales: ?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD&limite=100
        </p>
      </div>

      <div style="margin: 15px 0;">
        <strong>Subir Datos via Webhook (POST):</strong><br>
        <code style="background: #f4f4f4; padding: 8px; display: block; margin-top: 5px; word-break: break-all;">
          ${webhookUpload}
        </code>
        <p style="font-size: 0.9em; color: #666; margin-top: 5px;">
          Enviar JSON: { "datos": [{"campo1": "valor1", ...}] }
        </p>
      </div>

      <button onclick="copiarAlPortapapeles('${webhookUrl}')" class="btn btn-sm btn-info" style="margin-top: 10px;">
        📋 Copiar URL de Consulta
      </button>
    </div>
  `;

  const modal = document.createElement("div");
  modal.className = "modal";
  modal.innerHTML = `
    <div class="modal-content" style="max-width: 700px;">
      ${mensaje}
      <button onclick="this.closest('.modal').remove()" class="btn btn-secondary" style="margin-top: 20px;">
        Cerrar
      </button>
    </div>
  `;
  document.body.appendChild(modal);
  modal.style.display = "flex";
}

function copiarAlPortapapeles(texto) {
  navigator.clipboard.writeText(texto).then(() => {
    mostrarAlerta("URL copiada al portapapeles", "success");
  });
}
// ============================================
// SECCIÓN: ANÁLISIS IA Y CHAT
// ============================================

let reporteSeleccionadoAnalisis = null;

// Cargar reportes en el select de análisis
document.addEventListener("DOMContentLoaded", function () {
  const menuAnalisis = document.querySelector('[data-section="analisis"]');
  if (menuAnalisis) {
    menuAnalisis.addEventListener("click", function () {
      cargarReportesEnSelectAnalisis();
    });
  }
});

async function cargarReportesEnSelectAnalisis() {
  try {
    const response = await fetch("/api/admin/reportes");
    const reportes = await response.json();

    const select = document.getElementById("select-reporte-analisis");
    select.innerHTML =
      '<option value="">-- Seleccione un reporte --</option>' +
      reportes
        .map((r) => `<option value="${r.codigo}">${r.nombre}</option>`)
        .join("");
  } catch (error) {
    console.error("Error:", error);
  }
}

function cargarReporteAnalisis() {
  const codigo = document.getElementById("select-reporte-analisis").value;

  if (!codigo) {
    document.getElementById("analisis-container").style.display = "none";
    return;
  }

  reporteSeleccionadoAnalisis = codigo;
  document.getElementById("analisis-container").style.display = "block";

  // Limpiar chat
  const chatMessages = document.getElementById("chat-messages");
  chatMessages.innerHTML = `
    <div class="chat-message system">
      <strong>🤖 Asistente IA:</strong>
      <p>Listo para analizar "${codigo}". ¿Qué te gustaría saber?</p>
    </div>
  `;
}

function cambiarTabAnalisis(tab) {
  // Cambiar tabs activos
  document
    .querySelectorAll("#analisis-container .tab-btn")
    .forEach((btn) => btn.classList.remove("active"));
  document
    .querySelectorAll("#analisis-container .tab-content")
    .forEach((content) => content.classList.remove("active"));

  event.target.classList.add("active");

  if (tab === "chat") {
    document.getElementById("tab-chat-ia").classList.add("active");
  } else if (tab === "informes") {
    document.getElementById("tab-informes-ia").classList.add("active");
  } else if (tab === "busqueda") {
    document.getElementById("tab-busqueda-ia").classList.add("active");
  }
}

// Chat con IA
async function enviarPregunta() {
  if (!reporteSeleccionadoAnalisis) {
    mostrarAlerta("Seleccione un reporte primero", "warning");
    return;
  }

  const input = document.getElementById("chat-input");
  const pregunta = input.value.trim();

  if (!pregunta) return;

  const chatMessages = document.getElementById("chat-messages");

  // Mostrar pregunta del usuario
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.innerHTML = `<strong>👤 Tú:</strong><p>${pregunta}</p>`;
  chatMessages.appendChild(userMsg);

  // Limpiar input
  input.value = "";

  // Mostrar indicador de carga
  const loadingMsg = document.createElement("div");
  loadingMsg.className = "chat-message system loading";
  loadingMsg.innerHTML = `<strong>🤖 Asistente IA:</strong><p>Pensando...</p>`;
  chatMessages.appendChild(loadingMsg);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const response = await fetch(
      `/api/analysis/${encodeURIComponent(reporteSeleccionadoAnalisis)}/pregunta`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pregunta }),
      },
    );

    if (!response.ok) throw new Error("Error al procesar pregunta");

    const data = await response.json();

    // Quitar loading y mostrar respuesta
    loadingMsg.remove();

    const aiMsg = document.createElement("div");
    aiMsg.className = "chat-message system";

    const chartId = `chat-chart-${Date.now()}`;
    let contenido = `
      <strong>🤖 Asistente IA:</strong>
      <p style="white-space: pre-wrap;">${data.respuesta}</p>
    `;

    // Si hay un gráfico, agregarlo
    if (data.grafico) {
      contenido += `
        <div style="margin-top: 15px; background: white; padding: 15px; border-radius: 8px;">
          <h4 style="margin-bottom: 10px; font-size: 14px; color: #333;">${data.grafico.titulo}</h4>
          <canvas id="${chartId}" style="max-height: 300px;"></canvas>
        </div>
      `;
    }

    contenido += `<small style="color: #999;">Contexto usado: ${data.contexto_usado} registros relevantes</small>`;

    aiMsg.innerHTML = contenido;
    chatMessages.appendChild(aiMsg);

    // Renderizar gráfico si existe
    if (data.grafico) {
      setTimeout(() => {
        const canvas = document.getElementById(chartId);
        if (canvas) {
          renderizarGraficoChat(canvas, data.grafico);
        }
      }, 100);
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
  } catch (error) {
    console.error("Error:", error);
    loadingMsg.remove();

    const errorMsg = document.createElement("div");
    errorMsg.className = "chat-message error";
    errorMsg.innerHTML = `<strong>❌ Error:</strong><p>No pude procesar tu pregunta. ${error.message}</p>`;
    chatMessages.appendChild(errorMsg);
  }
}

// Renderizar gráfico en el chat
function renderizarGraficoChat(canvas, grafico) {
  const colores = generarColores(grafico.datos.length);

  const config = {
    type: grafico.tipo,
    data: {
      labels: grafico.labels,
      datasets: [
        {
          label: grafico.columna,
          data: grafico.datos,
          backgroundColor: colores.background,
          borderColor: colores.border,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: grafico.tipo === "pie",
          position: "bottom",
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.label || "";
              if (label) {
                label += ": ";
              }
              if (grafico.tipo === "pie") {
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percent = ((context.parsed / total) * 100).toFixed(1);
                label +=
                  context.parsed.toLocaleString() + " (" + percent + "%)";
              } else {
                label += (
                  context.parsed.y !== undefined
                    ? context.parsed.y
                    : context.parsed
                ).toLocaleString();
              }
              return label;
            },
          },
        },
      },
      scales:
        grafico.tipo === "bar"
          ? {
              y: {
                beginAtZero: true,
                ticks: {
                  callback: function (value) {
                    return value.toLocaleString();
                  },
                },
              },
            }
          : {},
    },
  };

  new Chart(canvas, config);
}

// Indexar datos
async function indexarDatos() {
  if (!reporteSeleccionadoAnalisis) return;

  const statusEl = document.getElementById("indexar-status");
  statusEl.textContent = "⏳ Indexando...";

  try {
    const response = await fetch(
      `/api/analysis/${encodeURIComponent(reporteSeleccionadoAnalisis)}/indexar`,
      {
        method: "POST",
      },
    );

    if (!response.ok) throw new Error("Error al indexar");

    const data = await response.json();
    statusEl.textContent = `✅ ${data.indexed} registros indexados`;
    mostrarAlerta("Datos indexados correctamente", "success");
  } catch (error) {
    console.error("Error:", error);
    statusEl.textContent = "❌ Error al indexar";
    mostrarAlerta("Error al indexar datos", "error");
  }
}

// Generar análisis
async function generarAnalisis(tipo) {
  if (!reporteSeleccionadoAnalisis) return;

  const resultadoDiv = document.getElementById("informe-resultado");
  const contenidoDiv = document.getElementById("informe-contenido");
  const tituloDiv = document.getElementById("informe-titulo");
  const graficosContainer = document.getElementById("graficos-container");

  resultadoDiv.style.display = "block";

  const titulos = {
    general: "📊 Análisis General",
    tendencias: "📈 Análisis de Tendencias",
    anomalias: "⚠️ Detección de Anomalías",
  };

  tituloDiv.textContent = titulos[tipo] || "Análisis";
  contenidoDiv.textContent = "⏳ Generando análisis con IA...";
  graficosContainer.innerHTML = "";

  try {
    const response = await fetch(
      `/api/analysis/${encodeURIComponent(reporteSeleccionadoAnalisis)}/analisis?tipo=${tipo}`,
    );

    if (!response.ok) throw new Error("Error al generar análisis");

    const data = await response.json();
    contenidoDiv.textContent = data.analisis;

    // Renderizar gráficos si existen
    if (data.graficos && data.graficos.length > 0) {
      renderizarGraficos(data.graficos);
    }
  } catch (error) {
    console.error("Error:", error);
    contenidoDiv.textContent = `❌ Error: ${error.message}`;
  }
}

// Función para renderizar gráficos
function renderizarGraficos(graficos) {
  const container = document.getElementById("graficos-container");
  container.innerHTML = "";

  graficos.forEach((grafico, index) => {
    // Crear contenedor para cada gráfico
    const chartDiv = document.createElement("div");
    chartDiv.style.background = "white";
    chartDiv.style.padding = "20px";
    chartDiv.style.borderRadius = "8px";
    chartDiv.style.boxShadow = "0 2px 8px rgba(0,0,0,0.1)";

    const canvas = document.createElement("canvas");
    canvas.id = `chart-${index}`;
    canvas.style.maxHeight = "300px";

    const titulo = document.createElement("h4");
    titulo.textContent = grafico.titulo;
    titulo.style.marginBottom = "15px";
    titulo.style.fontSize = "16px";
    titulo.style.color = "#333";

    chartDiv.appendChild(titulo);
    chartDiv.appendChild(canvas);
    container.appendChild(chartDiv);

    // Configurar colores
    const colores = generarColores(grafico.datos.length);

    // Configuración del gráfico
    const config = {
      type: grafico.tipo,
      data: {
        labels: grafico.labels,
        datasets: [
          {
            label: grafico.columna,
            data: grafico.datos,
            backgroundColor: colores.background,
            borderColor: colores.border,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: grafico.tipo === "pie",
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                let label = context.label || "";
                if (label) {
                  label += ": ";
                }
                if (grafico.tipo === "pie") {
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percent = ((context.parsed / total) * 100).toFixed(1);
                  label += context.parsed + " (" + percent + "%)";
                } else {
                  label +=
                    context.parsed.y !== undefined
                      ? context.parsed.y
                      : context.parsed;
                }
                return label;
              },
            },
          },
        },
        scales:
          grafico.tipo === "bar"
            ? {
                y: {
                  beginAtZero: true,
                  ticks: {
                    callback: function (value) {
                      return value.toLocaleString();
                    },
                  },
                },
              }
            : {},
      },
    };

    // Crear el gráfico
    new Chart(canvas, config);
  });
}

// Generar paleta de colores
function generarColores(cantidad) {
  const coloresBase = [
    "#4285F4",
    "#34A853",
    "#FBBC04",
    "#EA4335",
    "#9C27B0",
    "#00BCD4",
    "#FF9800",
    "#795548",
    "#607D8B",
    "#E91E63",
  ];

  const background = [];
  const border = [];

  for (let i = 0; i < cantidad; i++) {
    const color = coloresBase[i % coloresBase.length];
    background.push(color + "80"); // 50% transparencia
    border.push(color);
  }

  return { background, border };
}

// Generar informe completo
async function generarInformeCompleto() {
  if (!reporteSeleccionadoAnalisis) return;

  const resultadoDiv = document.getElementById("informe-resultado");
  const contenidoDiv = document.getElementById("informe-contenido");
  const tituloDiv = document.getElementById("informe-titulo");
  const graficosContainer = document.getElementById("graficos-container");

  resultadoDiv.style.display = "block";
  tituloDiv.textContent = "📑 Informe Completo";
  contenidoDiv.innerHTML =
    "⏳ Generando informe completo... Esto puede tomar varios minutos.";
  graficosContainer.innerHTML = "";

  try {
    const response = await fetch(
      `/api/analysis/${encodeURIComponent(reporteSeleccionadoAnalisis)}/informe`,
    );

    if (!response.ok) throw new Error("Error al generar informe");

    const data = await response.json();

    // Renderizar gráficos primero si existen
    if (data.secciones?.analisis_general?.graficos) {
      renderizarGraficos(data.secciones.analisis_general.graficos);
    }

    // Formatear informe
    let html = `<h3>Informe de: ${data.reporte}</h3>`;
    html += `<p><strong>Generado:</strong> ${new Date(data.fecha_generacion).toLocaleString("es")}</p>`;
    html += `<hr>`;

    if (data.estadisticas) {
      html += `<h4>📊 Estadísticas</h4>`;
      html += `<p><strong>Total registros:</strong> ${data.estadisticas.total_registros}</p>`;
      html += `<p><strong>Columnas:</strong> ${data.estadisticas.columnas.join(", ")}</p>`;
      html += `<hr>`;
    }

    if (data.secciones) {
      if (data.secciones.analisis_general) {
        html += `<h4>📊 Análisis General</h4>`;
        html += `<p style="white-space: pre-wrap;">${data.secciones.analisis_general.analisis}</p>`;
        html += `<hr>`;
      }

      if (data.secciones.tendencias) {
        html += `<h4>📈 Tendencias</h4>`;
        html += `<p style="white-space: pre-wrap;">${data.secciones.tendencias.analisis}</p>`;
        html += `<hr>`;
      }

      if (data.secciones.anomalias) {
        html += `<h4>⚠️ Anomalías</h4>`;
        html += `<p style="white-space: pre-wrap;">${data.secciones.anomalias.analisis}</p>`;
      }
    }

    contenidoDiv.innerHTML = html;
  } catch (error) {
    console.error("Error:", error);
    contenidoDiv.textContent = `❌ Error: ${error.message}`;
  }
}

// Búsqueda semántica
async function buscarSemantico() {
  if (!reporteSeleccionadoAnalisis) return;

  const consulta = document.getElementById("busqueda-input").value.trim();
  const limite = document.getElementById("busqueda-limite").value;

  if (!consulta) {
    mostrarAlerta("Escribe algo para buscar", "warning");
    return;
  }

  const resultadosDiv = document.getElementById("busqueda-resultados");
  const contenidoDiv = document.getElementById("busqueda-contenido");

  resultadosDiv.style.display = "block";
  contenidoDiv.innerHTML = "⏳ Buscando...";

  try {
    const response = await fetch(
      `/api/analysis/${encodeURIComponent(reporteSeleccionadoAnalisis)}/buscar`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consulta, limite: parseInt(limite) }),
      },
    );

    if (!response.ok) throw new Error("Error en búsqueda");

    const data = await response.json();

    if (data.resultados.length === 0) {
      contenidoDiv.innerHTML = "<p>No se encontraron resultados</p>";
      return;
    }

    let html = `<p><strong>Encontrados ${data.resultados.length} resultados relevantes:</strong></p>`;

    data.resultados.forEach((resultado, idx) => {
      html += `
        <div class="card" style="margin: 15px 0; padding: 15px; background: #f9f9f9;">
          <h4>Resultado ${idx + 1}</h4>
          <p style="white-space: pre-wrap;">${resultado}</p>
        </div>
      `;
    });

    contenidoDiv.innerHTML = html;
  } catch (error) {
    console.error("Error:", error);
    contenidoDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
  }
}

// Copiar informe
function copiarInforme() {
  const contenido = document.getElementById("informe-contenido").innerText;
  navigator.clipboard.writeText(contenido).then(() => {
    mostrarAlerta("Informe copiado al portapapeles", "success");
  });
}
