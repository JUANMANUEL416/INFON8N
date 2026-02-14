/* eslint-env node */

const { configure } = require("quasar/wrappers");

module.exports = configure(function (/* ctx */) {
  return {
    eslint: {
      warnings: true,
      errors: true,
    },

    boot: ["axios"],

    css: ["app.scss"],

    extras: ["roboto-font", "material-icons", "mdi-v7", "fontawesome-v6"],

    build: {
      target: {
        browser: ["es2019", "edge88", "firefox78", "chrome87", "safari13.1"],
        node: "node18",
      },

      vueRouterMode: "hash",

      env: {
        API_URL: process.env.API_URL || "http://localhost:5000",
      },
    },

    devServer: {
      open: true,
      port: 8080,
    },

    framework: {
      config: {
        dark: false,
        notify: {},
        loading: {},
      },

      plugins: [
        "Notify",
        "Loading",
        "Dialog",
        "LocalStorage",
        "SessionStorage",
      ],
    },

    animations: "all",

    ssr: {
      pwa: false,
      prodPort: 3000,
      middlewares: ["render"],
    },

    pwa: {
      workboxMode: "generateSW",
      injectPwaMetaTags: true,
      swFilename: "sw.js",
      manifestFilename: "manifest.json",
      useCredentialsForManifestTag: false,
    },

    cordova: {},
    capacitor: {},
    electron: {},

    bex: {},
  };
});
