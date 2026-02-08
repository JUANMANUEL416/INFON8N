// Variables globales
let reporteSeleccionado = null;
let selectedFile = null;
let reportesDisponibles = [];

// Verificar autenticación al cargar
document.addEventListener("DOMContentLoaded", function () {
  verificarAutenticacion();
  cargarReportes();
  setupDropzone();
  setupFileInput();
});

// Verificar autenticación
function verificarAutenticacion() {
  const usuario = JSON.parse(localStorage.getItem("usuario") || "{}");

  if (!usuario.id || !usuario.username) {
    // Redirigir al login si no está autenticado
    window.location.href = "/login";
    return;
  }

  // Mostrar información del usuario
  document.getElementById("user-name").textContent =
    `👤 ${usuario.nombre || usuario.username}`;
  document.getElementById("user-group").textContent =
    `📋 ${usuario.grupo_nombre || "Sin grupo"}`;

  // Si es admin, mostrar link al panel
  if (usuario.grupo_codigo === "admin") {
    const header = document.querySelector("header > div");
    const adminLink = document.createElement("a");
    adminLink.href = "/admin";
    adminLink.className = "btn btn-info";
    adminLink.style.cssText = "margin-left: 15px; font-size: 14px;";
    adminLink.innerHTML = "🔧 Panel Admin";
    header.appendChild(adminLink);
  }
}

// Cerrar sesión
function cerrarSesion() {
  localStorage.removeItem("usuario");
  window.location.href = "/login";
}

// Cargar reportes disponibles
async function cargarReportes() {
  const container = document.getElementById("reportes-disponibles");
  const usuario = JSON.parse(localStorage.getItem("usuario") || "{}");

  try {
    // Obtener todos los reportes
    const response = await fetch("/api/admin/reportes");
    if (!response.ok) throw new Error("Error al cargar reportes");

    const todosLosReportes = await response.json();

    // Si es admin, mostrar todos los reportes
    if (usuario.grupo_codigo === "admin") {
      reportesDisponibles = todosLosReportes;
    } else {
      // Obtener permisos del grupo del usuario
      const permisosResponse = await fetch(
        `/api/permisos/grupo/${usuario.grupo_id}`,
      );
      if (!permisosResponse.ok) throw new Error("Error al cargar permisos");

      const permisos = await permisosResponse.json();
      const reportesCodigos = permisos.map((p) => p.reporte_codigo);

      // Filtrar solo reportes permitidos
      reportesDisponibles = todosLosReportes.filter((r) =>
        reportesCodigos.includes(r.codigo),
      );
    }

    if (reportesDisponibles.length === 0) {
      container.innerHTML =
        '<p style="color: #666;">No tiene reportes asignados. Contacte al administrador.</p>';
      return;
    }

    // Renderizar reportes
    container.innerHTML = reportesDisponibles
      .map(
        (reporte) => `
        <div class="reporte-card" onclick="seleccionarReporte('${reporte.codigo}')">
          <div class="reporte-icono">${reporte.icono || "📊"}</div>
          <h3>${reporte.nombre}</h3>
          <p>${reporte.descripcion || ""}</p>
        </div>
      `,
      )
      .join("");
  } catch (error) {
    console.error("Error:", error);
    container.innerHTML = '<p style="color: red;">Error al cargar reportes</p>';
  }
}

// Seleccionar reporte
function seleccionarReporte(codigo) {
  reporteSeleccionado = reportesDisponibles.find((r) => r.codigo === codigo);
  if (!reporteSeleccionado) return;

  // Actualizar UI con información del reporte
  document.getElementById("reporte-icono").textContent =
    reporteSeleccionado.icono || "📊";
  document.getElementById("reporte-nombre").textContent =
    reporteSeleccionado.nombre;
  document.getElementById("reporte-descripcion").textContent =
    reporteSeleccionado.descripcion || "";
  document.getElementById("reporte-contexto").textContent =
    reporteSeleccionado.contexto || "Sin información adicional";

  // Mostrar pasos siguientes
  document.getElementById("paso2").style.display = "block";
  document.getElementById("paso3").style.display = "block";

  // Scroll suave al paso 2
  document.getElementById("paso2").scrollIntoView({ behavior: "smooth" });
}

// Descargar plantilla
async function descargarPlantilla() {
  if (!reporteSeleccionado) {
    mostrarAlerta("Primero seleccione un reporte", "warning");
    return;
  }

  try {
    const response = await fetch(`/download/${reporteSeleccionado.codigo}`);

    if (!response.ok) {
      throw new Error("Error al descargar la plantilla");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `plantilla_${reporteSeleccionado.codigo}.xlsx`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    mostrarAlerta("✅ Plantilla descargada correctamente", "success");
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta(
      "❌ Error al descargar la plantilla: " + error.message,
      "error",
    );
  }
}

// Configurar dropzone
function setupDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");

  dropzone.addEventListener("click", () => {
    if (!reporteSeleccionado) {
      mostrarAlerta("Primero seleccione un reporte", "warning");
      return;
    }
    fileInput.click();
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (reporteSeleccionado) {
      dropzone.classList.add("dragover");
    }
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");

    if (!reporteSeleccionado) {
      mostrarAlerta("Primero seleccione un reporte", "warning");
      return;
    }

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  });
}

// Configurar input de archivo
function setupFileInput() {
  const fileInput = document.getElementById("fileInput");
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  });
}

// Manejar selección de archivo
function handleFileSelect(file) {
  if (!file.name.endsWith(".xlsx")) {
    mostrarAlerta("Por favor seleccione un archivo Excel (.xlsx)", "error");
    return;
  }

  selectedFile = file;
  document.getElementById("filename").textContent = file.name;
  document.getElementById("file-selected").style.display = "block";
  document.getElementById("dropzone").style.display = "none";
}

// Cancelar archivo
function cancelarArchivo() {
  selectedFile = null;
  document.getElementById("fileInput").value = "";
  document.getElementById("file-selected").style.display = "none";
  document.getElementById("dropzone").style.display = "block";
  ocultarResultado();
}

// Subir archivo
async function subirArchivo() {
  if (!selectedFile || !reporteSeleccionado) {
    mostrarAlerta("Error: Archivo o reporte no seleccionado", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("type", reporteSeleccionado.codigo);

  const resultDiv = document.getElementById("upload-result");
  resultDiv.className = "alert alert-info";
  resultDiv.innerHTML = "⏳ Procesando archivo...";
  resultDiv.style.display = "block";

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (response.ok) {
      mostrarAlerta(
        `✅ Archivo cargado correctamente<br>
        <strong>${result.records || 0}</strong> registros procesados<br>
        Archivo: ${result.file || selectedFile.name}`,
        "success",
      );
      cancelarArchivo();

      // Cargar estadísticas si están disponibles
      setTimeout(cargarEstadisticas, 1000);
    } else {
      mostrarAlerta(
        `❌ Error: ${result.error || "Error desconocido"}`,
        "error",
      );
    }
  } catch (error) {
    console.error("Error:", error);
    mostrarAlerta("❌ Error al subir el archivo: " + error.message, "error");
  }
}

// Cargar estadísticas
async function cargarEstadisticas() {
  if (!reporteSeleccionado) return;

  const statsSection = document.getElementById("estadisticas");
  const statsContent = document.getElementById("stats-content");

  statsSection.style.display = "block";
  statsContent.innerHTML = '<p class="loading">Cargando estadísticas...</p>';

  try {
    const response = await fetch(`/stats/${reporteSeleccionado.codigo}`);

    if (!response.ok) {
      throw new Error("Error al cargar estadísticas");
    }

    const stats = await response.json();

    if (stats.total === 0) {
      statsContent.innerHTML =
        '<p style="color: #666;">No hay datos cargados aún</p>';
      return;
    }

    statsContent.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <h3>📊 Total Registros</h3>
          <div class="stat-value">${stats.total || 0}</div>
        </div>
        ${
          stats.ultimo_registro
            ? `
        <div class="stat-card">
          <h3>🕒 Última Carga</h3>
          <div class="stat-value" style="font-size: 16px;">${new Date(stats.ultimo_registro).toLocaleString("es")}</div>
        </div>
        `
            : ""
        }
      </div>
    `;
  } catch (error) {
    console.error("Error:", error);
    statsContent.innerHTML =
      '<p style="color: #dc3545;">Error al cargar estadísticas</p>';
  }
}

// Mostrar alerta
function mostrarAlerta(mensaje, tipo) {
  const resultDiv = document.getElementById("upload-result");
  resultDiv.className = `alert alert-${tipo}`;
  resultDiv.innerHTML = mensaje;
  resultDiv.style.display = "block";

  if (tipo === "success") {
    setTimeout(ocultarResultado, 5000);
  }
}

// Ocultar resultado
function ocultarResultado() {
  const resultDiv = document.getElementById("upload-result");
  resultDiv.style.display = "none";
}
