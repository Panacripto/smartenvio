import { useEffect, useState, useCallback } from "react";
import api from "@/api/client";

export default function WhatsAppPage() {
  const [status, setStatus] = useState("disconnected");
  const [qr, setQr] = useState<string | null>(null);
  const [telefono, setTelefono] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const [copiado, setCopiado] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/whatsapp/status");
      setStatus(r.data.status);
      if (r.data.status === "awaiting_scan") {
        const q = await api.get("/whatsapp/qr");
        setQr(q.data.qr);
      } else {
        setQr(null);
      }
    } catch {
      setStatus("disconnected");
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const enviarPrueba = async () => {
    if (!telefono || !mensaje) return;
    setSending(true);
    setResult(null);
    try {
      await api.post("/whatsapp/send", {
        telefono: telefono.replace(/\D/g, ""),
        mensaje,
      });
      setResult({ ok: true, text: "Enviado correctamente" });
    } catch (e: any) {
      setResult({ ok: false, text: e.response?.data?.detail || e.message || "Error" });
    }
    setSending(false);
  };

  const copiarAlPortapapeles = () => {
    navigator.clipboard.writeText(telefono);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  };

  const estados = {
    connected: { texto: "Conectado", color: "bg-green-500", bg: "bg-green-50", borde: "border-green-300", icono: "✓" },
    disconnected: { texto: "Desconectado", color: "bg-red-500", bg: "bg-red-50", borde: "border-red-300", icono: "✗" },
    awaiting_scan: { texto: "Esperando código QR", color: "bg-yellow-500", bg: "bg-yellow-50", borde: "border-yellow-300", icono: "⏳" },
    auth_failure: { texto: "Error de autenticación", color: "bg-red-500", bg: "bg-red-50", borde: "border-red-300", icono: "!" },
  };

  const e = estados[status as keyof typeof estados] || estados.disconnected;

  return (
    <div className="h-full flex items-start justify-center pt-8">
      <div className="w-full max-w-4xl">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">WhatsApp</h2>
        <div className="grid grid-cols-2 gap-6">
          {/* Columna izquierda: QR + Estado */}
          <div className="bg-white rounded-xl border shadow-md p-6 flex flex-col items-center">
            <div className={`w-full rounded-lg p-4 mb-5 ${e.bg} ${e.borde} border flex items-center gap-3`}>
              <div className={`w-3 h-3 rounded-full ${e.color} shrink-0`}></div>
              <span className="font-medium text-sm">{e.texto}</span>
            </div>

            {status === "awaiting_scan" && qr && (
              <div className="flex flex-col items-center">
                <p className="text-sm text-gray-500 mb-4 text-center">Escanea con WhatsApp en tu teléfono</p>
                <div className="bg-white p-3 rounded-xl shadow-md border">
                  <img src={qr} alt="QR" className="w-56 h-56" />
                </div>
              </div>
            )}

            {status === "connected" && (
              <div className="flex flex-col items-center justify-center py-10">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-3">
                  <span className="text-3xl text-green-600">✓</span>
                </div>
                <p className="text-green-700 font-medium">WhatsApp conectado</p>
                <p className="text-sm text-gray-400 mt-1">Listo para enviar mensajes</p>
              </div>
            )}

            {status === "disconnected" && (
              <div className="flex flex-col items-center justify-center py-10">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-3">
                  <span className="text-3xl text-gray-400">⟳</span>
                </div>
                <p className="text-gray-500 font-medium">Iniciando servicio...</p>
                <p className="text-sm text-gray-400 mt-1">Espera unos segundos</p>
              </div>
            )}
          </div>

          {/* Columna derecha: Mensaje de prueba */}
          <div className="bg-white rounded-xl border shadow-md p-6">
            <h3 className="font-semibold text-gray-800 mb-1">Enviar mensaje de prueba</h3>
            <p className="text-sm text-gray-400 mb-5">Verifica que el envío funciona correctamente</p>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-500 block mb-1">Teléfono</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="584146762870"
                    className="w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    value={telefono}
                    onChange={e => setTelefono(e.target.value)}
                  />
                  <button
                    onClick={copiarAlPortapapeles}
                    className="border border-gray-200 rounded-lg px-3 py-2.5 text-sm hover:bg-gray-50 hover:border-gray-300 transition-colors"
                    title="Copiar"
                  >
                    {copiado ? (
                      <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                    ) : (
                      <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                    )}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 block mb-1">Mensaje</label>
                <textarea
                  placeholder="Escribe tu mensaje de prueba..."
                  className="w-full border rounded-lg px-3 py-2.5 text-sm min-h-[100px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
                  value={mensaje}
                  onChange={e => setMensaje(e.target.value)}
                />
              </div>
              <button
                className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white py-2.5 rounded-lg text-sm font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center justify-center gap-2"
                disabled={sending || status !== "connected" || !telefono || !mensaje}
                onClick={enviarPrueba}
              >
                {sending ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Enviando...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                    Enviar mensaje de prueba
                  </span>
                )}
              </button>
              {result && (
                <div className={`rounded-lg p-3 text-sm ${result.ok ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
                  {result.ok ? "✓ " : "✗ "}{result.text}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
