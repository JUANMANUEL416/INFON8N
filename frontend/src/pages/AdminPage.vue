<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">
      <q-icon name="admin_panel_settings" class="q-mr-sm" />
      Administración de Reportes
    </div>

    <!-- Tabs para diferentes secciones -->
    <q-tabs
      v-model="tab"
      dense
      class="text-grey"
      active-color="primary"
      indicator-color="primary"
      align="justify"
      narrow-indicator
    >
      <q-tab name="reportes" icon="description" label="Reportes" />
      <q-tab name="upload" icon="cloud_upload" label="Subir Datos" />
      <q-tab name="usuarios" icon="people" label="Usuarios" />
    </q-tabs>

    <q-separator class="q-my-md" />

    <q-tab-panels v-model="tab" animated>
      <!-- Panel de Reportes -->
      <q-tab-panel name="reportes">
        <div class="row q-col-gutter-md">
          <div class="col-12">
            <q-btn
              color="primary"
              icon="add"
              label="Nuevo Reporte"
              @click="dialogNuevoReporte = true"
            />
          </div>

          <div class="col-12">
            <q-table
              :rows="reportes"
              :columns="columnasReportes"
              row-key="codigo"
              :loading="loadingReportes"
              flat
              bordered
            >
              <template v-slot:body-cell-estado="props">
                <q-td :props="props">
                  <q-badge
                    :color="props.row.activo ? 'positive' : 'grey'"
                    :label="props.row.activo ? 'Activo' : 'Inactivo'"
                  />
                </q-td>
              </template>

              <template v-slot:body-cell-acciones="props">
                <q-td :props="props">
                  <q-btn
                    flat
                    dense
                    round
                    icon="visibility"
                    color="primary"
                    size="sm"
                    @click="verDetalleReporte(props.row)"
                  >
                    <q-tooltip>Ver detalles</q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    round
                    icon="list_alt"
                    color="secondary"
                    size="sm"
                    @click="abrirCampos(props.row)"
                  >
                    <q-tooltip>Ver/Editar campos</q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    round
                    :icon="props.row.activo ? 'delete' : 'refresh'"
                    :color="props.row.activo ? 'negative' : 'positive'"
                    size="sm"
                    @click="toggleReporte(props.row)"
                  >
                    <q-tooltip>{{
                      props.row.activo ? "Desactivar" : "Activar"
                    }}</q-tooltip>
                  </q-btn>
                </q-td>
              </template>
            </q-table>
          </div>
        </div>
      </q-tab-panel>

      <!-- Panel de Upload -->
      <q-tab-panel name="upload">
        <q-card>
          <q-card-section>
            <div class="text-h6">Subir Datos a Reporte Existente</div>
            <div class="text-caption text-grey-7">
              Selecciona un reporte y carga archivo Excel (.xlsx, .xls)
            </div>
          </q-card-section>

          <q-card-section>
            <q-form @submit="subirArchivo" class="q-gutter-md">
              <q-select
                v-model="uploadForm.reporteSeleccionado"
                filled
                :options="reportesActivos"
                option-label="nombre"
                option-value="codigo"
                label="Seleccionar Reporte"
                hint="Elige el reporte al que deseas agregar datos"
                emit-value
                map-options
                :rules="[(val) => !!val || 'Debes seleccionar un reporte']"
              >
                <template v-slot:prepend>
                  <q-icon name="description" />
                </template>
                <template v-slot:selected-item="{ opt }">
                  <div class="flex items-center">
                    <q-icon name="description" size="xs" class="q-mr-sm" />
                    {{ opt.nombre }} ({{ opt.codigo }})
                  </div>
                </template>
                <template v-slot:option="{ opt, itemProps }">
                  <q-item v-bind="itemProps">
                    <q-item-section avatar>
                      <q-icon name="description" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label>{{ opt.nombre }}</q-item-label>
                      <q-item-label caption>{{ opt.codigo }}</q-item-label>
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>

              <q-file
                v-model="uploadForm.archivo"
                filled
                label="Seleccionar archivo"
                accept=".xlsx,.xls"
                :rules="[(val) => !!val || 'Selecciona un archivo']"
              >
                <template v-slot:prepend>
                  <q-icon name="attach_file" />
                </template>
              </q-file>

              <div>
                <q-btn
                  type="submit"
                  color="primary"
                  label="Subir y Procesar"
                  icon="cloud_upload"
                  :loading="loadingUpload"
                />
              </div>
            </q-form>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <!-- Panel de Usuarios -->
      <q-tab-panel name="usuarios">
        <div class="row q-col-gutter-md">
          <div class="col-12">
            <q-btn
              color="primary"
              icon="person_add"
              label="Nuevo Usuario"
              @click="dialogNuevoUsuario = true"
            />
          </div>

          <div class="col-12">
            <q-table
              :rows="usuarios"
              :columns="columnasUsuarios"
              row-key="id"
              :loading="loadingUsuarios"
              flat
              bordered
            >
              <template v-slot:body-cell-role="props">
                <q-td :props="props">
                  <q-badge
                    :color="
                      props.row.role === 'admin' ? 'primary' : 'secondary'
                    "
                  >
                    {{ props.row.role }}
                  </q-badge>
                </q-td>
              </template>
            </q-table>
          </div>
        </div>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Diálogos -->
    <q-dialog v-model="dialogNuevoReporte">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Crear Nuevo Reporte</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="crearReporte" class="q-gutter-md">
            <q-input v-model="nuevoReporte.codigo" filled label="Código" />
            <q-input v-model="nuevoReporte.nombre" filled label="Nombre" />
            <q-input
              v-model="nuevoReporte.contexto"
              filled
              type="textarea"
              label="Contexto"
            />

            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancelar" color="grey" v-close-popup />
              <q-btn type="submit" label="Crear" color="primary" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="dialogNuevoUsuario">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Crear Nuevo Usuario</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="crearUsuario" class="q-gutter-md">
            <q-input v-model="nuevoUsuario.username" filled label="Usuario" />
            <q-input
              v-model="nuevoUsuario.nombre"
              filled
              label="Nombre completo"
            />
            <q-input
              v-model="nuevoUsuario.password"
              filled
              type="password"
              label="Contraseña"
            />
            <q-select
              v-model="nuevoUsuario.role"
              filled
              :options="['user', 'admin']"
              label="Rol"
            />

            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancelar" color="grey" v-close-popup />
              <q-btn type="submit" label="Crear" color="primary" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Diálogo de Campos del Reporte -->
    <q-dialog v-model="dialogCampos">
      <q-card style="min-width: 900px; max-width: 95vw">
        <q-card-section class="row items-center q-gutter-sm">
          <q-icon name="view_list" size="md" />
          <div class="text-h6">
            Campos de {{ reporteCampos?.nombre }} ({{ reporteCampos?.codigo }})
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            @click="cargarCampos(reporteCampos.codigo)"
          />
        </q-card-section>

        <q-separator />

        <q-card-section>
          <q-table
            :rows="campos"
            :columns="columnasCampos"
            row-key="nombre"
            flat
            bordered
          >
            <template v-slot:body-cell-nombre="props">
              <q-td :props="props">
                <q-input v-model="props.row.nombre" dense />
              </q-td>
            </template>
            <template v-slot:body-cell-etiqueta="props">
              <q-td :props="props">
                <q-input v-model="props.row.etiqueta" dense />
              </q-td>
            </template>
            <template v-slot:body-cell-tipo="props">
              <q-td :props="props">
                <q-select
                  v-model="props.row.tipo"
                  :options="tiposCampo"
                  dense
                />
              </q-td>
            </template>
            <template v-slot:body-cell-obligatorio="props">
              <q-td :props="props">
                <q-toggle v-model="props.row.obligatorio" color="primary" />
              </q-td>
            </template>
            <template v-slot:body-cell-descripcion="props">
              <q-td :props="props">
                <q-input
                  v-model="props.row.descripcion"
                  dense
                  type="textarea"
                  autogrow
                />
              </q-td>
            </template>
            <template v-slot:body-cell-acciones="props">
              <q-td :props="props">
                <q-btn
                  flat
                  dense
                  round
                  icon="help"
                  size="sm"
                  @click="generarAclaracion(props.row)"
                >
                  <q-tooltip>Generar aclaración con IA</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>

        <q-separator />

        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Importar campos desde Excel</div>
          <div class="row q-col-gutter-md items-center q-mb-md">
            <div class="col-12 col-md-6">
              <q-file
                v-model="uploadCampos.archivo"
                filled
                label="Seleccionar Excel de esquema (.xlsx/.xls)"
                accept=".xlsx,.xls"
              >
                <template v-slot:prepend>
                  <q-icon name="description" />
                </template>
              </q-file>
            </div>
            <div class="col-12 col-md-6">
              <div class="row q-gutter-sm">
                <q-btn
                  color="primary"
                  icon="file_upload"
                  label="Importar"
                  @click="importarCampos(false)"
                />
                <q-btn
                  color="secondary"
                  icon="save"
                  label="Importar y Guardar"
                  @click="importarCampos(true)"
                />
              </div>
              <div class="text-caption text-grey-7 q-mt-xs">
                Prefiere hoja "Campos" (nombre, etiqueta, tipo, obligatorio,
                descripción). Si no existe, usa encabezados de "Datos".
              </div>
            </div>
          </div>

          <div class="text-subtitle2 q-mb-sm">Agregar nuevo campo</div>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-3">
              <q-input v-model="campoNuevo.nombre" label="Nombre" dense />
            </div>
            <div class="col-12 col-md-3">
              <q-input v-model="campoNuevo.etiqueta" label="Etiqueta" dense />
            </div>
            <div class="col-12 col-md-3">
              <q-select
                v-model="campoNuevo.tipo"
                :options="tiposCampo"
                label="Tipo"
                dense
              />
            </div>
            <div class="col-12 col-md-3 flex items-center">
              <q-toggle
                v-model="campoNuevo.obligatorio"
                label="Obligatorio"
                color="primary"
              />
            </div>
            <div class="col-12">
              <q-input
                v-model="campoNuevo.descripcion"
                label="Descripción"
                type="textarea"
                autogrow
                dense
              />
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cerrar" v-close-popup />
          <q-btn
            color="secondary"
            label="Agregar campo"
            icon="add"
            @click="agregarCampo"
          />
          <q-btn
            color="primary"
            label="Guardar cambios"
            icon="save"
            @click="guardarCampos"
          />
        </q-card-actions>

        <q-separator />

        <!-- Aclaraciones pendientes -->
        <q-card-section>
          <div class="text-h6">Aclaraciones pendientes</div>
          <q-table
            :rows="aclaraciones"
            :columns="columnasAclaraciones"
            row-key="id"
            flat
            bordered
          >
            <template v-slot:body-cell-pregunta="props">
              <q-td :props="props">
                <div class="text-body2">{{ props.row.pregunta_ia }}</div>
                <div class="text-caption text-grey-7">
                  Campo: {{ props.row.nombre_campo }}
                </div>
              </q-td>
            </template>
            <template v-slot:body-cell-estado="props">
              <q-td :props="props">
                <q-badge
                  :label="props.row.estado"
                  :color="props.row.estado === 'pendiente' ? 'warning' : 'info'"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-acciones="props">
              <q-td :props="props" class="q-gutter-xs">
                <q-btn
                  dense
                  flat
                  icon="reply"
                  label="Responder"
                  @click="promptResponder(props.row)"
                />
                <q-btn
                  dense
                  flat
                  icon="verified"
                  label="Validar"
                  color="primary"
                  @click="promptValidar(props.row)"
                />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { defineComponent, ref, onMounted, computed } from "vue";
import { api } from "src/boot/axios";
import { useQuasar } from "quasar";
import * as XLSX from "xlsx";

export default defineComponent({
  name: "AdminPage",

  setup() {
    const $q = useQuasar();
    const tab = ref("reportes");

    const reportes = ref([]);
    const loadingReportes = ref(false);

    const usuarios = ref([]);
    const loadingUsuarios = ref(false);

    const dialogNuevoReporte = ref(false);
    const dialogNuevoUsuario = ref(false);

    const loadingUpload = ref(false);

    const uploadForm = ref({
      reporteSeleccionado: null,
      archivo: null,
    });

    const reportesActivos = computed(() => {
      return reportes.value.filter((r) => r.activo === true);
    });

    const nuevoReporte = ref({
      codigo: "",
      nombre: "",
      contexto: "",
    });

    const nuevoUsuario = ref({
      username: "",
      nombre: "",
      password: "",
      role: "user",
    });

    const columnasReportes = [
      { name: "codigo", label: "Código", field: "codigo", align: "left" },
      { name: "nombre", label: "Nombre", field: "nombre", align: "left" },
      { name: "estado", label: "Estado", field: "activo", align: "center" },
      {
        name: "fecha_creacion",
        label: "Fecha Creación",
        field: "created_at",
        align: "left",
      },
      {
        name: "acciones",
        label: "Acciones",
        field: "acciones",
        align: "center",
      },
    ];

    // Gestión de campos
    const dialogCampos = ref(false);
    const reporteCampos = ref(null);
    const campos = ref([]);
    const tiposCampo = ["texto", "numero", "decimal", "fecha", "boolean"];
    const campoNuevo = ref({
      nombre: "",
      etiqueta: "",
      tipo: "texto",
      obligatorio: false,
      descripcion: "",
    });

    const columnasCampos = [
      { name: "nombre", label: "Nombre", field: "nombre", align: "left" },
      { name: "etiqueta", label: "Etiqueta", field: "etiqueta", align: "left" },
      { name: "tipo", label: "Tipo", field: "tipo", align: "left" },
      {
        name: "obligatorio",
        label: "Obligatorio",
        field: "obligatorio",
        align: "center",
      },
      {
        name: "descripcion",
        label: "Descripción",
        field: "descripcion",
        align: "left",
      },
      {
        name: "acciones",
        label: "Acciones",
        field: "acciones",
        align: "center",
      },
    ];

    const abrirCampos = async (reporte) => {
      reporteCampos.value = reporte;
      await cargarCampos(reporte.codigo);
      await cargarAclaraciones(reporte.codigo);
      dialogCampos.value = true;
    };

    // Upload de esquema de campos desde Excel
    const uploadCampos = ref({ archivo: null });
    const importarCampos = async (guardar = false) => {
      try {
        const file = uploadCampos.value.archivo;
        if (!file) {
          $q.notify({
            type: "negative",
            message: "Selecciona un Excel de esquema",
          });
          return;
        }
        const data = await file.arrayBuffer();
        const wb = XLSX.read(data, { type: "array" });
        const sheets = wb.SheetNames.map((s) => s.trim().toLowerCase());
        let hoja = null;
        // Preferir hoja 'campos'; si no, usar 'datos'; si no, primera
        if (sheets.includes("campos")) {
          hoja = wb.Sheets[wb.SheetNames[sheets.indexOf("campos")]];
          const rows = XLSX.utils.sheet_to_json(hoja, { defval: "" });
          const posibles = [
            "nombre",
            "etiqueta",
            "tipo",
            "obligatorio",
            "descripcion",
          ];
          const camposImportados = rows
            .map((r) => ({
              nombre: r["nombre"] || r["Nombre"] || "",
              etiqueta:
                r["etiqueta"] ||
                r["Etiqueta"] ||
                r["label"] ||
                r["Label"] ||
                "",
              tipo: (r["tipo"] || r["Tipo"] || "texto")
                .toString()
                .toLowerCase(),
              obligatorio: !!(r["obligatorio"] || r["Obligatorio"]),
              descripcion:
                r["descripcion"] || r["Descripción"] || r["Descripcion"] || "",
            }))
            .filter((c) => c.nombre);
          if (camposImportados.length === 0) {
            $q.notify({
              type: "negative",
              message: "Hoja 'Campos' sin filas válidas",
            });
            return;
          }
          campos.value = camposImportados;
        } else {
          // Usar encabezados de la hoja 'Datos' o primera
          hoja =
            wb.Sheets[
              wb.SheetNames[
                sheets.includes("datos") ? sheets.indexOf("datos") : 0
              ]
            ];
          const matriz = XLSX.utils.sheet_to_json(hoja, {
            header: 1,
            blankrows: false,
          });
          if (!matriz || matriz.length === 0) {
            $q.notify({ type: "negative", message: "Excel sin encabezados" });
            return;
          }
          const headers = (matriz[0] || []).map((h) => (h || "").toString());
          const sampleRow = matriz.length > 1 ? matriz[1] : [];
          const detectarTipo = (val) => {
            if (val === null || val === undefined || val === "") return "texto";
            if (typeof val === "number")
              return Number.isInteger(val) ? "numero" : "decimal";
            const s = String(val).trim().toLowerCase();
            if (
              s === "true" ||
              s === "false" ||
              s === "si" ||
              s === "no" ||
              s === "1" ||
              s === "0"
            )
              return "boolean";
            const d = Date.parse(String(val));
            if (!Number.isNaN(d)) return "fecha";
            return "texto";
          };
          const camposImportados = headers
            .filter((h) => h)
            .map((h, idx) => ({
              nombre: h,
              etiqueta: h,
              tipo: detectarTipo(sampleRow ? sampleRow[idx] : ""),
              obligatorio: false,
              descripcion: "",
            }));
          if (camposImportados.length === 0) {
            $q.notify({
              type: "negative",
              message: "No se detectaron columnas",
            });
            return;
          }
          campos.value = camposImportados;
        }
        $q.notify({
          type: "positive",
          message: `Importados ${campos.value.length} campos`,
        });
        if (guardar) {
          await guardarCampos();
        }
      } catch (error) {
        console.error("Error importando campos:", error);
        $q.notify({
          type: "negative",
          message: error.message || "Error importando campos",
        });
      }
    };

    const cargarCampos = async (codigo) => {
      try {
        const resp = await api.get(`/api/admin/reportes/${codigo}/campos`);
        campos.value = resp.data.campos || [];
      } catch (error) {
        console.error("Error listando campos:", error);
        $q.notify({
          type: "negative",
          message: error.response?.data?.error || "Error listando campos",
        });
      }
    };

    // Aclaraciones
    const aclaraciones = ref([]);
    const columnasAclaraciones = [
      {
        name: "pregunta",
        label: "Pregunta IA",
        field: "pregunta_ia",
        align: "left",
      },
      { name: "estado", label: "Estado", field: "estado", align: "center" },
      {
        name: "acciones",
        label: "Acciones",
        field: "acciones",
        align: "center",
      },
    ];
    const cargarAclaraciones = async (codigo) => {
      try {
        const resp = await api.get(`/api/aclaraciones/${codigo}`);
        aclaraciones.value = resp.data.aclaraciones || [];
      } catch (error) {
        console.error("Error cargando aclaraciones:", error);
      }
    };
    const promptResponder = (item) => {
      $q.dialog({
        title: "Responder aclaración",
        message: `Campo: ${item.nombre_campo}`,
        prompt: { model: "", type: "text", label: "Tu respuesta" },
        cancel: true,
      }).onOk(async (respuesta) => {
        try {
          await api.post(`/api/aclaraciones/${item.id}/responder`, {
            respuesta,
            usuario: "admin",
          });
          $q.notify({
            type: "positive",
            message: "Respuesta enviada. Pendiente de validación.",
          });
          await cargarAclaraciones(reporteCampos.value.codigo);
        } catch (error) {
          $q.notify({
            type: "negative",
            message: error.response?.data?.error || "Error enviando respuesta",
          });
        }
      });
    };
    const promptValidar = (item) => {
      $q.dialog({
        title: "Validar aclaración",
        message: `Campo: ${item.nombre_campo}`,
        prompt: {
          model: item.respuesta_usuario || "",
          type: "text",
          label: "Respuesta final",
        },
        options: {
          type: "toggle",
          items: [{ label: "Aprobar", value: true }],
        },
        cancel: true,
      }).onOk(async (respuesta_final) => {
        try {
          await api.post(`/api/admin/aclaraciones/${item.id}/validar`, {
            respuesta_final,
            admin: "admin",
            aprobar: true,
          });
          $q.notify({ type: "positive", message: "Aclaración validada" });
          await cargarAclaraciones(reporteCampos.value.codigo);
        } catch (error) {
          $q.notify({
            type: "negative",
            message:
              error.response?.data?.error || "Error validando aclaración",
          });
        }
      });
    };

    const guardarCampos = async () => {
      try {
        const resp = await api.put(
          `/api/admin/reportes/${reporteCampos.value.codigo}/campos`,
          { campos: campos.value },
        );
        $q.notify({ type: "positive", message: "Campos actualizados" });
        if (resp.data?.requiere_aclaraciones) {
          $q.notify({
            type: "warning",
            message: "Se requieren aclaraciones. El reporte quedó inactivo.",
          });
        }
        await cargarCampos(reporteCampos.value.codigo);
      } catch (error) {
        console.error("Error guardando campos:", error);
        $q.notify({
          type: "negative",
          message: error.response?.data?.error || "Error guardando campos",
        });
      }
    };

    const agregarCampo = async () => {
      try {
        if (!campoNuevo.value.nombre || !campoNuevo.value.tipo) {
          $q.notify({
            type: "negative",
            message: "Nombre y tipo son obligatorios",
          });
          return;
        }
        const resp = await api.post(
          `/api/admin/reportes/${reporteCampos.value.codigo}/campos`,
          { campo: campoNuevo.value },
        );
        $q.notify({ type: "positive", message: "Campo agregado" });
        if (resp.data?.requiere_aclaraciones) {
          $q.notify({
            type: "warning",
            message: "Se generaron aclaraciones y el reporte fue desactivado.",
          });
        }
        campoNuevo.value = {
          nombre: "",
          etiqueta: "",
          tipo: "texto",
          obligatorio: false,
          descripcion: "",
        };
        await cargarCampos(reporteCampos.value.codigo);
      } catch (error) {
        console.error("Error agregando campo:", error);
        $q.notify({
          type: "negative",
          message: error.response?.data?.error || "Error agregando campo",
        });
      }
    };

    const generarAclaracion = async (campo) => {
      try {
        const resp = await api.post(
          `/api/admin/reportes/${reporteCampos.value.codigo}/campos/${campo.nombre}/aclaracion`,
          {
            descripcion: campo.descripcion,
            tipo: campo.tipo,
            razon: "Generada manualmente por administrador",
          },
        );
        $q.notify({
          type: "positive",
          message: "Aclaración generada: " + (resp.data?.pregunta || ""),
        });
      } catch (error) {
        console.error("Error creando aclaración:", error);
        $q.notify({
          type: "negative",
          message: error.response?.data?.error || "Error creando aclaración",
        });
      }
    };

    const columnasUsuarios = [
      { name: "username", label: "Usuario", field: "username", align: "left" },
      { name: "nombre", label: "Nombre", field: "nombre", align: "left" },
      { name: "role", label: "Rol", field: "role", align: "center" },
    ];

    const cargarReportes = async () => {
      loadingReportes.value = true;
      try {
        const response = await api.get("/api/admin/reportes");
        reportes.value = response.data;
      } catch (error) {
        console.error("Error al cargar reportes:", error);
        $q.notify({ type: "negative", message: "Error al cargar reportes" });
      } finally {
        loadingReportes.value = false;
      }
    };

    const cargarUsuarios = async () => {
      loadingUsuarios.value = true;
      try {
        const response = await api.get("/api/usuarios");
        usuarios.value = response.data;
      } catch (error) {
        $q.notify({ type: "negative", message: "Error al cargar usuarios" });
      } finally {
        loadingUsuarios.value = false;
      }
    };

    const subirArchivo = async () => {
      loadingUpload.value = true;
      try {
        const reporte = reportes.value.find(
          (r) => r.codigo === uploadForm.value.reporteSeleccionado,
        );

        if (!reporte) {
          $q.notify({
            type: "negative",
            message: "Reporte no encontrado",
          });
          return;
        }

        const formData = new FormData();
        formData.append("file", uploadForm.value.archivo);

        await api.post(`/api/reportes/${reporte.codigo}/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        $q.notify({
          type: "positive",
          message: `Datos agregados al reporte "${reporte.nombre}" correctamente`,
        });

        uploadForm.value = {
          reporteSeleccionado: null,
          archivo: null,
        };
      } catch (error) {
        console.error("Error al subir archivo:", error);
        $q.notify({
          type: "negative",
          message: error.response?.data?.error || "Error al subir archivo",
        });
      } finally {
        loadingUpload.value = false;
      }
    };

    const crearReporte = async () => {
      try {
        await api.post("/api/admin/reportes", nuevoReporte.value);
        $q.notify({ type: "positive", message: "Reporte creado exitosamente" });
        dialogNuevoReporte.value = false;
        nuevoReporte.value = { codigo: "", nombre: "", contexto: "" };
        cargarReportes();
      } catch (error) {
        console.error("Error al crear reporte:", error);
        const mensaje =
          error.response?.data?.error ||
          error.message ||
          "Error al crear reporte";
        $q.notify({ type: "negative", message: mensaje });
      }
    };

    const crearUsuario = async () => {
      try {
        await api.post("/api/usuarios", nuevoUsuario.value);
        $q.notify({ type: "positive", message: "Usuario creado" });
        dialogNuevoUsuario.value = false;
        nuevoUsuario.value = {
          username: "",
          nombre: "",
          password: "",
          role: "user",
        };
        cargarUsuarios();
      } catch (error) {
        $q.notify({ type: "negative", message: "Error al crear usuario" });
      }
    };

    const toggleReporte = async (reporte) => {
      const accion = reporte.activo ? "desactivar" : "activar";

      $q.dialog({
        title: "Confirmar",
        message: `¿Seguro que deseas ${accion} el reporte "${reporte.nombre}"?`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          if (reporte.activo) {
            // Desactivar
            await api.delete(`/api/admin/reportes/${reporte.codigo}`);
            $q.notify({
              type: "positive",
              message: "Reporte desactivado exitosamente",
            });
          } else {
            // Activar
            await api.put(`/api/admin/reportes/${reporte.codigo}`, {
              activo: true,
            });
            $q.notify({
              type: "positive",
              message: "Reporte activado exitosamente",
            });
          }

          // Recargar la lista de reportes
          await cargarReportes();
        } catch (error) {
          console.error("Error al cambiar estado del reporte:", error);
          const mensaje =
            error.response?.data?.error || "Error al cambiar estado";
          $q.notify({ type: "negative", message: mensaje });
        }
      });
    };

    const verDetalleReporte = (reporte) => {
      $q.dialog({
        title: reporte.nombre,
        message: `Código: ${reporte.codigo}\n\nContexto: ${reporte.contexto || "Sin contexto"}`,
      });
    };

    onMounted(() => {
      cargarReportes();
      cargarUsuarios();
    });

    return {
      tab,
      reportes,
      reportesActivos,
      usuarios,
      loadingReportes,
      loadingUsuarios,
      loadingUpload,
      columnasReportes,
      columnasUsuarios,
      uploadForm,
      nuevoReporte,
      nuevoUsuario,
      dialogNuevoReporte,
      dialogNuevoUsuario,
      subirArchivo,
      crearReporte,
      crearUsuario,
      toggleReporte,
      verDetalleReporte,
      dialogCampos,
      reporteCampos,
      campos,
      columnasCampos,
      tiposCampo,
      campoNuevo,
      uploadCampos,
      importarCampos,
      abrirCampos,
      cargarCampos,
      guardarCampos,
      agregarCampo,
      generarAclaracion,
      aclaraciones,
      columnasAclaraciones,
      cargarAclaraciones,
      promptResponder,
      promptValidar,
    };
  },
});
</script>
