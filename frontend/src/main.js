import { createApp } from "vue";
import {
  Quasar,
  Notify,
  Loading,
  Dialog,
  LocalStorage,
  SessionStorage,
} from "quasar";
import { createPinia } from "pinia";

// Import icon libraries
import "@quasar/extras/material-icons/material-icons.css";
import "@quasar/extras/mdi-v7/mdi-v7.css";
import "@quasar/extras/fontawesome-v6/fontawesome-v6.css";

// Import Quasar css
import "quasar/dist/quasar.css";

// Import App and Router
import App from "./App.vue";
import router from "./router";

// Import global styles
import "./css/app.scss";

const app = createApp(App);

app.use(Quasar, {
  plugins: {
    Notify,
    Loading,
    Dialog,
    LocalStorage,
    SessionStorage,
  },
  config: {
    notify: {
      position: "top-right",
      timeout: 2500,
    },
    loading: {},
  },
});

app.use(createPinia());
app.use(router);

app.mount("#app");
