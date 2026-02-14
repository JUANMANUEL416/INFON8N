<template>
  <q-page class="q-pa-md">
    <div class="row q-col-gutter-md">
      <!-- Selector de Reporte -->
      <div class="col-12">
        <q-card>
          <q-card-section>
            <div class="text-h6">
              <q-icon name="description" class="q-mr-sm" />
              Seleccionar Reporte
            </div>
          </q-card-section>

          <q-card-section>
            <q-select
              v-model="reporteSeleccionado"
              :options="reportes"
              option-value="codigo"
              option-label="nombre"
              filled
              label="Selecciona un reporte para consultar"
              @update:model-value="cambiarReporte"
            >
              <template v-slot:prepend>
                <q-icon name="folder_open" />
              </template>
            </q-select>
          </q-card-section>
        </q-card>
      </div>

      <!-- Chat IA -->
      <div class="col-12">
        <ChatIA
          v-if="reporteSeleccionado"
          :codigo-reporte="reporteSeleccionado.codigo"
        />
        <q-card v-else class="text-center">
          <q-card-section>
            <q-icon name="info" size="64px" color="grey-5" />
            <div class="text-h6 text-grey-7 q-mt-md">
              Selecciona un reporte para comenzar a consultar
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script>
import { defineComponent, ref, onMounted } from "vue";
import { api } from "src/boot/axios";
import { useQuasar } from "quasar";
import ChatIA from "src/components/ChatIA.vue";

export default defineComponent({
  name: "UsuarioPage",

  components: {
    ChatIA,
  },

  setup() {
    const $q = useQuasar();
    const reportes = ref([]);
    const reporteSeleccionado = ref(null);

    const cargarReportes = async () => {
      try {
        $q.loading.show({ message: "Cargando reportes..." });
        const response = await api.get("/api/reportes");
        reportes.value = response.data;

        if (reportes.value.length > 0) {
          reporteSeleccionado.value = reportes.value[0];
        }
      } catch (error) {
        $q.notify({
          type: "negative",
          message: "Error al cargar reportes",
        });
      } finally {
        $q.loading.hide();
      }
    };

    const cambiarReporte = () => {
      // Se reiniciará el componente ChatIA automáticamente
    };

    onMounted(() => {
      cargarReportes();
    });

    return {
      reportes,
      reporteSeleccionado,
      cambiarReporte,
    };
  },
});
</script>
