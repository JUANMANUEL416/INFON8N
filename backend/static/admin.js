// Variables globales
let reportesCargados = [];
let campoCounter = 0;
let relacionCounter = 0;

// Inicialización
document.addEventListener("DOMContentLoaded", function () {
  cargarReportes();
  setupNavigation();
  setupExcelUpload();

  // Form submit
  document
    .getElementById("form-nuevo-reporte")
    .addEventListener("submit", guardarNuevoReporte);
});

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
                        <strong>Campos:</strong> ${reporte.campos ? JSON.parse(reporte.campos).length : 0}
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
