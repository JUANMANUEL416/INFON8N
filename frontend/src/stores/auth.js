import { defineStore } from "pinia";
import { api } from "src/boot/axios";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("auth_token") || null,
    user: JSON.parse(localStorage.getItem("user_data") || "{}"),
    isAuthenticated: !!localStorage.getItem("auth_token"),
  }),

  getters: {
    isAdmin: (state) => {
      // Considerar admin si el username es 'admin' o si tiene grupo_codigo admin
      return (
        state.user?.username === "admin" || state.user?.grupo_codigo === "admin"
      );
    },
    userName: (state) =>
      state.user?.nombre || state.user?.username || "Usuario",
  },

  actions: {
    async login(username, password) {
      try {
        const response = await api.post("/api/auth/login", {
          username,
          password,
        });

        if (response.data.success) {
          this.user = response.data.usuario;
          this.isAuthenticated = true;
          // Generar un token simple (el backend no usa JWT aún)
          this.token = btoa(`${username}:${Date.now()}`);

          localStorage.setItem("auth_token", this.token);
          localStorage.setItem("user_data", JSON.stringify(this.user));

          return { success: true };
        } else {
          return {
            success: false,
            message: response.data.error || "Error al iniciar sesión",
          };
        }
      } catch (error) {
        return {
          success: false,
          message: error.response?.data?.error || "Error al iniciar sesión",
        };
      }
    },

    logout() {
      this.token = null;
      this.user = {};
      this.isAuthenticated = false;

      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");
    },
  },
});
