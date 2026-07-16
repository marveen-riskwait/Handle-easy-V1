// Public catalogue calls (no auth). Reuses the shared axios instance; GET
// requests carry no CSRF and never trigger the 401 logout redirect.
import { api } from "./api";

export const getBikes = () => api.get("/bikes").then((r) => r.data.bikes);
export const getStations = () => api.get("/stations").then((r) => r.data.stations);
export const getOptions = () => api.get("/options").then((r) => r.data.options);
export const getBike = (slug) => api.get(`/bikes/${slug}`).then((r) => r.data.bike);

// Cents → "45 €" (no decimals when round, else "12,50 €").
export const euros = (cents) => {
  if (cents == null) return null;
  const v = cents / 100;
  return (Number.isInteger(v) ? v.toString() : v.toFixed(2).replace(".", ",")) + " €";
};
