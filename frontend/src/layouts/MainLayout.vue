<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn dense flat round icon="menu" @click="toggleLeftDrawer" />

        <q-toolbar-title>
          <q-icon name="analytics" size="sm" class="q-mr-sm" />
          Sistema de Reportes IA
        </q-toolbar-title>

        <div class="q-mr-md text-caption">
          {{ authStore.userName }}
        </div>

        <q-btn flat round dense icon="logout" @click="handleLogout">
          <q-tooltip>Cerrar sesión</q-tooltip>
        </q-btn>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      :width="250"
      :breakpoint="500"
      elevated
    >
      <q-scroll-area class="fit">
        <q-list padding>
          <q-item-label header>Menú Principal</q-item-label>

          <q-item
            clickable
            v-ripple
            :active="$route.path === '/'"
            @click="$router.push('/')"
          >
            <q-item-section avatar>
              <q-icon name="chat" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Chat IA</q-item-label>
              <q-item-label caption>Consultar reportes</q-item-label>
            </q-item-section>
          </q-item>

          <q-item
            v-if="authStore.isAdmin"
            clickable
            v-ripple
            :active="$route.path === '/admin'"
            @click="$router.push('/admin')"
          >
            <q-item-section avatar>
              <q-icon name="admin_panel_settings" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Administración</q-item-label>
              <q-item-label caption>Gestionar reportes</q-item-label>
            </q-item-section>
          </q-item>

          <q-separator class="q-my-md" />

          <q-item-label header>Información</q-item-label>

          <q-item>
            <q-item-section>
              <q-item-label caption>Versión 1.0.0</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script>
import { defineComponent, ref } from "vue";
import { useAuthStore } from "src/stores/auth";
import { useRouter } from "vue-router";
import { useQuasar } from "quasar";

export default defineComponent({
  name: "MainLayout",

  setup() {
    const authStore = useAuthStore();
    const router = useRouter();
    const $q = useQuasar();
    const leftDrawerOpen = ref(false);

    const toggleLeftDrawer = () => {
      leftDrawerOpen.value = !leftDrawerOpen.value;
    };

    const handleLogout = () => {
      $q.dialog({
        title: "Confirmar",
        message: "¿Deseas cerrar sesión?",
        cancel: true,
        persistent: true,
      }).onOk(() => {
        authStore.logout();
        router.push("/login");
        $q.notify({
          type: "positive",
          message: "Sesión cerrada correctamente",
        });
      });
    };

    return {
      authStore,
      leftDrawerOpen,
      toggleLeftDrawer,
      handleLogout,
    };
  },
});
</script>
