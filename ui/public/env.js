// Runtime configuration - overwritten at container start by envsubst
// In development, the Vite proxy handles /api routing
window.__ENV__ = {
  API_URL: "/api",
};
