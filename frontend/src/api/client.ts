import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default api;

export async function fetchDashboard() {
  const { data } = await api.get("/dashboard/resumen");
  return data;
}

export async function fetchClientes(search?: string) {
  const params = search ? { search } : {};
  const { data } = await api.get("/clientes", { params });
  return data;
}

export async function fetchVentas(params?: Record<string, any>) {
  const { data } = await api.get("/ventas", { params });
  return data;
}

export async function fetchCompras(params?: Record<string, any>) {
  const { data } = await api.get("/compras", { params });
  return data;
}

export async function fetchInventario(params?: Record<string, any>) {
  const { data } = await api.get("/inventario", { params });
  return data;
}

export async function fetchCuentasCobrar(params?: Record<string, any>) {
  const { data } = await api.get("/cuentas/cobrar", { params });
  return data;
}

export async function fetchCuentasPagar(params?: Record<string, any>) {
  const { data } = await api.get("/cuentas/pagar", { params });
  return data;
}

export async function fetchMensajes(params?: Record<string, any>) {
  const { data } = await api.get("/mensajes", { params });
  return data;
}

export async function fetchPlantillas() {
  const { data } = await api.get("/plantillas");
  return data;
}

export async function sendMensaje(mensajeId: number) {
  const { data } = await api.post(`/mensajes/${mensajeId}/enviar`);
  return data;
}

export async function enviarMasivo(body: any) {
  const { data } = await api.post("/mensajes/enviar-masivo", body);
  return data;
}

export async function enviarPersonalizados(body: any) {
  const { data } = await api.post("/mensajes/personalizados", body);
  return data;
}

export async function getWhatsAppStatus() {
  const { data } = await api.get("/whatsapp/status");
  return data;
}

export async function getWhatsAppQR() {
  const { data } = await api.get("/whatsapp/qr");
  return data;
}

export async function sendTestWhatsApp(telefono: string, mensaje: string) {
  const { data } = await api.post("/whatsapp/send", { telefono, mensaje });
  return data;
}
