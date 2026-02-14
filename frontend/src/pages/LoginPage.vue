<template>
  <div class="flex flex-center bg-gradient" style="min-height: 100vh">
    <q-card class="login-card">
      <q-card-section class="text-center">
        <q-icon name="analytics" size="64px" color="primary" />
        <div class="text-h5 q-mt-md">Sistema de Reportes IA</div>
        <div class="text-caption text-grey-7">Ingresa tus credenciales</div>
      </q-card-section>

      <q-card-section>
        <q-form @submit="handleLogin" class="q-gutter-md">
          <q-input
            v-model="username"
            filled
            label="Usuario"
            lazy-rules
            :rules="[(val) => (val && val.length > 0) || 'Campo requerido']"
            prepend-icon="person"
          >
            <template v-slot:prepend>
              <q-icon name="person" />
            </template>
          </q-input>

          <q-input
            v-model="password"
            filled
            :type="isPwd ? 'password' : 'text'"
            label="Contraseña"
            lazy-rules
            :rules="[(val) => (val && val.length > 0) || 'Campo requerido']"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
            <template v-slot:append>
              <q-icon
                :name="isPwd ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="isPwd = !isPwd"
              />
            </template>
          </q-input>

          <div>
            <q-btn
              unelevated
              type="submit"
              color="primary"
              label="Iniciar Sesión"
              class="full-width"
              :loading="loading"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </div>
</template>

<script>
import { defineComponent, ref } from "vue";
import { useAuthStore } from "src/stores/auth";
import { useRouter } from "vue-router";
import { useQuasar } from "quasar";

export default defineComponent({
  name: "LoginPage",

  setup() {
    const authStore = useAuthStore();
    const router = useRouter();
    const $q = useQuasar();

    const username = ref("");
    const password = ref("");
    const isPwd = ref(true);
    const loading = ref(false);

    const handleLogin = async () => {
      loading.value = true;

      const result = await authStore.login(username.value, password.value);

      loading.value = false;

      if (result.success) {
        $q.notify({
          type: "positive",
          message: "Sesión iniciada correctamente",
        });
        router.push("/");
      } else {
        $q.notify({
          type: "negative",
          message: result.message,
        });
      }
    };

    return {
      username,
      password,
      isPwd,
      loading,
      handleLogin,
    };
  },
});
</script>

<style scoped>
.bg-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
}
</style>
