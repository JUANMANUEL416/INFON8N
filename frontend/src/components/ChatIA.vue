<template>
  <q-card class="chat-container">
    <q-card-section class="bg-primary text-white">
      <div class="text-h6">
        <q-icon name="smart_toy" class="q-mr-sm" />
        Asistente IA
      </div>
      <div class="text-caption">{{ codigoReporte }}</div>
    </q-card-section>

    <!-- Área de mensajes -->
    <q-card-section class="chat-messages" ref="chatMessagesRef">
      <div v-if="mensajes.length === 0" class="text-center text-grey-6 q-pa-lg">
        <q-icon name="chat_bubble_outline" size="48px" />
        <div class="q-mt-md">Haz una pregunta sobre el reporte</div>
      </div>

      <div
        v-for="(mensaje, index) in mensajes"
        :key="index"
        class="mensaje-container"
      >
        <!-- Mensaje del usuario -->
        <div v-if="mensaje.rol === 'usuario'" class="mensaje mensaje-usuario">
          <div class="mensaje-bubble bg-primary text-white">
            {{ mensaje.texto }}
          </div>
          <q-icon name="person" size="32px" color="primary" class="q-ml-sm" />
        </div>

        <!-- Respuesta de la IA -->
        <div v-else class="mensaje mensaje-ia">
          <q-icon
            name="smart_toy"
            size="32px"
            color="secondary"
            class="q-mr-sm"
          />
          <div class="mensaje-bubble bg-grey-2">
            <div v-html="formatearRespuesta(mensaje.texto)"></div>

            <!-- Visualización de datos si existen -->
            <div v-if="mensaje.datos" class="q-mt-md">
              <q-separator class="q-mb-md" />
              <div class="text-caption text-grey-7 q-mb-sm">
                Datos obtenidos:
              </div>
              <q-markup-table dense flat bordered>
                <thead>
                  <tr>
                    <th v-for="(value, key) in mensaje.datos[0]" :key="key">
                      {{ key }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(item, idx) in mensaje.datos.slice(0, 10)"
                    :key="idx"
                  >
                    <td v-for="(value, key) in item" :key="key">
                      {{ value }}
                    </td>
                  </tr>
                </tbody>
              </q-markup-table>
              <div
                v-if="mensaje.datos.length > 10"
                class="text-caption text-grey-6 q-mt-sm"
              >
                Mostrando 10 de {{ mensaje.datos.length }} registros
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Indicador de escritura -->
      <div v-if="escribiendo" class="mensaje mensaje-ia">
        <q-icon
          name="smart_toy"
          size="32px"
          color="secondary"
          class="q-mr-sm"
        />
        <div class="mensaje-bubble bg-grey-2">
          <q-spinner-dots color="secondary" size="24px" />
        </div>
      </div>
    </q-card-section>

    <!-- Barra de entrada -->
    <q-card-section class="q-pt-none">
      <q-separator class="q-mb-md" />

      <div class="row items-center q-gutter-sm">
        <div class="col">
          <q-input
            v-model="pregunta"
            filled
            placeholder="Escribe tu pregunta..."
            @keyup.enter="enviarPregunta"
            :disable="escribiendo"
            dense
          >
            <template v-slot:prepend>
              <q-icon name="chat" />
            </template>
          </q-input>
        </div>

        <div>
          <q-btn
            round
            color="primary"
            icon="send"
            @click="enviarPregunta"
            :disable="!pregunta || escribiendo"
            :loading="escribiendo"
          />
        </div>

        <div>
          <q-btn
            round
            flat
            color="grey-7"
            icon="delete"
            @click="limpiarChat"
            :disable="mensajes.length === 0"
          >
            <q-tooltip>Limpiar conversación</q-tooltip>
          </q-btn>
        </div>
      </div>

      <div class="text-caption text-grey-6 q-mt-sm">
        Sesión: <code>{{ sessionId }}</code>
      </div>
    </q-card-section>
  </q-card>
</template>

<script>
import { defineComponent, ref, watch, nextTick, onMounted } from "vue";
import { api } from "src/boot/axios";
import { useQuasar } from "quasar";

export default defineComponent({
  name: "ChatIA",

  props: {
    codigoReporte: {
      type: String,
      required: true,
    },
  },

  setup(props) {
    const $q = useQuasar();
    const mensajes = ref([]);
    const pregunta = ref("");
    const escribiendo = ref(false);
    const sessionId = ref(generarSessionId());
    const chatMessagesRef = ref(null);

    function generarSessionId() {
      return (
        "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9)
      );
    }

    function formatearRespuesta(texto) {
      // Convertir saltos de línea a <br>
      let formateado = texto.replace(/\n/g, "<br>");

      // Convertir listas con - en elementos visuales
      formateado = formateado.replace(/- (.*?)<br>/g, "<li>$1</li>");
      if (formateado.includes("<li>")) {
        formateado = "<ul>" + formateado + "</ul>";
      }

      // Resaltar números grandes (formato de moneda)
      formateado = formateado.replace(
        /\$[\d,.]+/g,
        '<strong class="text-positive">$&</strong>',
      );

      return formateado;
    }

    async function enviarPregunta() {
      if (!pregunta.value.trim()) return;

      const preguntaTexto = pregunta.value;
      pregunta.value = "";

      // Agregar mensaje del usuario
      mensajes.value.push({
        rol: "usuario",
        texto: preguntaTexto,
      });

      scrollToBottom();
      escribiendo.value = true;

      try {
        const response = await api.post(
          `/api/analysis/${props.codigoReporte}/pregunta`,
          {
            pregunta: preguntaTexto,
            session_id: sessionId.value,
          },
        );

        // Agregar respuesta de la IA
        mensajes.value.push({
          rol: "ia",
          texto: response.data.respuesta,
          datos: response.data.datos || null,
        });

        scrollToBottom();
      } catch (error) {
        $q.notify({
          type: "negative",
          message:
            error.response?.data?.error || "Error al procesar la pregunta",
        });

        mensajes.value.push({
          rol: "ia",
          texto:
            "Lo siento, hubo un error al procesar tu pregunta. Por favor intenta de nuevo.",
        });
      } finally {
        escribiendo.value = false;
      }
    }

    async function limpiarChat() {
      $q.dialog({
        title: "Confirmar",
        message: "¿Deseas limpiar la conversación?",
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await api.delete(
            `/api/analysis/${props.codigoReporte}/session/${sessionId.value}/limpiar`,
          );

          mensajes.value = [];
          sessionId.value = generarSessionId();

          $q.notify({
            type: "positive",
            message: "Conversación limpiada",
          });
        } catch (error) {
          $q.notify({
            type: "warning",
            message: "Error al limpiar la sesión en el servidor",
          });

          // Limpiar localmente de todos modos
          mensajes.value = [];
          sessionId.value = generarSessionId();
        }
      });
    }

    function scrollToBottom() {
      nextTick(() => {
        if (chatMessagesRef.value) {
          const container = chatMessagesRef.value.$el || chatMessagesRef.value;
          container.scrollTop = container.scrollHeight;
        }
      });
    }

    // Limpiar al cambiar de reporte
    watch(
      () => props.codigoReporte,
      () => {
        mensajes.value = [];
        sessionId.value = generarSessionId();
      },
    );

    return {
      mensajes,
      pregunta,
      escribiendo,
      sessionId,
      chatMessagesRef,
      enviarPregunta,
      limpiarChat,
      formatearRespuesta,
    };
  },
});
</script>

<style scoped>
.chat-container {
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 350px);
}

.mensaje-container {
  margin-bottom: 16px;
}

.mensaje {
  display: flex;
  align-items: flex-start;
}

.mensaje-usuario {
  flex-direction: row-reverse;
}

.mensaje-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  max-width: 70%;
  word-wrap: break-word;
}

.mensaje-usuario .mensaje-bubble {
  border-bottom-right-radius: 4px;
}

.mensaje-ia .mensaje-bubble {
  border-bottom-left-radius: 4px;
}
</style>
