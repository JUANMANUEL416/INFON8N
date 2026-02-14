const routes = [
  {
    path: "/login",
    component: () => import("../pages/LoginPage.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    component: () => import("../layouts/MainLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        component: () => import("../pages/UsuarioPage.vue"),
        meta: { requiresAuth: true },
      },
      {
        path: "admin",
        component: () => import("../pages/AdminPage.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
    ],
  },

  // Ruta 404
  {
    path: "/:catchAll(.*)*",
    component: () => import("../pages/ErrorNotFound.vue"),
  },
];

export default routes;
