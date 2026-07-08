// Single axios instance for the whole SPA.
//
// Session lives in an httpOnly cookie the browser sends automatically
// (withCredentials). For writes, the backend also wants the CSRF token
// echoed back in X-CSRF-TOKEN — we stash it in localStorage at login and
// attach it here. On a 401 we clear the local session so the UI logs out.
import axios from "axios";

const BASE = import.meta.env.VITE_BACKEND_URL || "";

export const api = axios.create({
  baseURL: `${BASE}/api`,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const csrf = localStorage.getItem("csrf_token");
  if (csrf && !["get", "head", "options"].includes((config.method || "").toLowerCase())) {
    config.headers["X-CSRF-TOKEN"] = csrf;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      clearSession();
      if (!window.location.pathname.startsWith("/login") &&
          !window.location.pathname.startsWith("/table/")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

// ── Session helpers (staff) ─────────────────────────────
export const getStoredUser = () => {
  try {
    const raw = localStorage.getItem("user");
    if (!raw || raw === "undefined") return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

export const setSession = (user, csrfToken) => {
  if (user) localStorage.setItem("user", JSON.stringify(user));
  if (csrfToken) localStorage.setItem("csrf_token", csrfToken);
};

export const clearSession = () => {
  localStorage.removeItem("user");
  localStorage.removeItem("csrf_token");
};

// Turn an axios error into a readable message.
export const errMsg = (err, fallback = "Une erreur est survenue") =>
  err?.response?.data?.message || fallback;
