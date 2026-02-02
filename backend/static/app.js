// Variables globales
let selectedFile = null;
const API_BASE = "";

// Mapeo de tipos de plantillas a archivos
const TEMPLATE_FILES = {
  facturas: "plantilla_facturacion_diaria.xlsx",
  cartera: "plantilla_cartera_vencida.xlsx",
  productos: "plantilla_ventas_productos.xlsx",
  gastos: "plantilla_gastos_operativos.xlsx",
};

// Inicialización
document.addEventListener("DOMContentLoaded", function () {
  setupDropzone();
  setupFileInput();
});

// Configurar dropzone
function setupDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");

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
    showAlert("Por favor seleccione un archivo Excel (.xlsx)", "error");
    return;
  }

  selectedFile = file;
  document.getElementById("fileName").textContent = file.name;
  document.getElementById("fileInfo").style.display = "block";
  document.getElementById("dropzone").style.display = "none";
  hideAlert();
}

// Limpiar archivo seleccionado
function clearFile() {
  selectedFile = null;
  document.getElementById("fileInput").value = "";
  document.getElementById("fileInfo").style.display = "none";
  document.getElementById("dropzone").style.display = "block";
  hideAlert();
}

// Descargar plantilla
async function downloadTemplate(type) {
  const filename = TEMPLATE_FILES[type];
  if (!filename) {
    showAlert("Plantilla no encontrada", "error");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/download/${type}`);

    if (!response.ok) {
      throw new Error("Error al descargar la plantilla");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showAlert("Plantilla descargada correctamente", "success");
  } catch (error) {
    console.error("Error:", error);
    showAlert("Error al descargar la plantilla: " + error.message, "error");
  }
}

// Subir archivo
async function uploadFile() {
  if (!selectedFile) {
    showAlert("Por favor seleccione un archivo", "warning");
    return;
  }

  const dataType = document.getElementById("dataType").value;
  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("type", dataType);

  // Mostrar progress bar
  document.getElementById("uploadProgress").style.display = "block";
  document.getElementById("fileInfo").style.display = "none";

  try {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (response.ok) {
      showAlert(
        `✅ Archivo cargado correctamente<br>
                <strong>${result.records}</strong> registros insertados<br>
                Archivo: ${result.file}`,
        "success",
      );
      clearFile();
      // Actualizar estadísticas automáticamente
      setTimeout(loadStats, 1000);
    } else {
      showAlert(`❌ Error: ${result.error}`, "error");
    }
  } catch (error) {
    console.error("Error:", error);
    showAlert("Error al subir el archivo: " + error.message, "error");
  } finally {
    document.getElementById("uploadProgress").style.display = "none";
  }
}

// Cargar estadísticas
async function loadStats() {
  const container = document.getElementById("statsContainer");
  container.innerHTML = '<p class="loading-text">Cargando estadísticas...</p>';

  try {
    const response = await fetch(`${API_BASE}/stats`);

    if (!response.ok) {
      throw new Error("Error al cargar estadísticas");
    }

    const stats = await response.json();

    container.innerHTML = `
            <div class="stat-card">
                <h3>📊 Total Facturas</h3>
                <div class="stat-value">${stats.facturas.total || 0}</div>
                <div class="stat-label">Monto: $${formatNumber(stats.facturas.monto_total || 0)}</div>
            </div>

            <div class="stat-card">
                <h3>💰 Cartera Vencida</h3>
                <div class="stat-value">${stats.cartera_vencida.vencidas || 0}</div>
                <div class="stat-label">Monto: $${formatNumber(stats.cartera_vencida.monto_vencido || 0)}</div>
            </div>

            <div class="stat-card">
                <h3>📦 Productos</h3>
                <div class="stat-value">${stats.productos?.total || 0}</div>
                <div class="stat-label">Registrados</div>
            </div>

            <div class="stat-card">
                <h3>💸 Gastos</h3>
                <div class="stat-value">$${formatNumber(stats.gastos?.total_monto || 0)}</div>
                <div class="stat-label">${stats.gastos?.total || 0} registros</div>
            </div>
        `;
  } catch (error) {
    console.error("Error:", error);
    container.innerHTML = `<p class="loading-text" style="color: #dc3545;">Error al cargar estadísticas: ${error.message}</p>`;
  }
}

// Mostrar alerta
function showAlert(message, type) {
  const alertDiv = document.getElementById("uploadResult");
  alertDiv.className = `alert alert-${type}`;
  alertDiv.innerHTML = message;
  alertDiv.style.display = "block";

  // Auto-ocultar después de 5 segundos para mensajes de éxito
  if (type === "success") {
    setTimeout(hideAlert, 5000);
  }
}

// Ocultar alerta
function hideAlert() {
  const alertDiv = document.getElementById("uploadResult");
  alertDiv.style.display = "none";
}

// Formatear números
function formatNumber(num) {
  return new Intl.NumberFormat("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}
