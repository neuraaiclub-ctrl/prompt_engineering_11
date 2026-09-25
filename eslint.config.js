module.exports = [
  {
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        fetch: "readonly",
        URLSearchParams: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        Event: "readonly",
        CustomEvent: "readonly",
        navigator: "readonly",
        Blob: "readonly",
        URL: "readonly",
        requestAnimationFrame: "readonly",
        cancelAnimationFrame: "readonly",
        FormData: "readonly",
        confirm: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        alert: "readonly"
      }
    },
    rules: {
      "no-undef": "error"
    }
  }
];
