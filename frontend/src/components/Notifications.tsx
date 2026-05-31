import { useEffect, useState, useRef, useCallback } from "react";

type Toast = { id: number; tipo: "error" | "warning" | "info"; mensaje: string };

let toastId = 0;

export default function Notifications() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const prevStatus = useRef<string | null>(null);
  const prevPhone = useRef<string | null>(null);
  const prevLogCount = useRef<number>(-1);
  const initial = useRef(true);
  const mounted = useRef(true);

  const addToast = useCallback((tipo: Toast["tipo"], mensaje: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev.slice(-4), { id, tipo, mensaje }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  }, []);

  useEffect(() => {
    mounted.current = true;
    addToast("info", "Sistema de notificaciones activo.");

    const poll = async () => {
      try {
        const [r1, r2] = await Promise.all([
          fetch("http://127.0.0.1:8000/api/services/status"),
          fetch("http://127.0.0.1:8000/api/dashboard/resumen"),
        ]);
        if (!mounted.current) return;
        const status = await r1.json();
        const dash = await r2.json();

        const wa = status?.whatsapp?.status || "disconnected";
        const phone = dash?.whatsapp_phone || null;

        if (initial.current) {
          initial.current = false;
          if (wa === "connected") {
            addToast("info", phone ? `WhatsApp conectado: ${phone}` : "WhatsApp conectado.");
          } else if (wa === "awaiting_scan") {
            addToast("warning", "Esperando código QR.");
          } else {
            addToast("error", "WhatsApp desconectado.");
          }
          prevStatus.current = wa;
          prevPhone.current = phone;
          prevLogCount.current = dash?.ejecuciones_totales ?? 0;
          return;
        }

        // WhatsApp disconnected
        if (prevStatus.current === "connected" && wa !== "connected") {
          addToast("error", "WhatsApp se ha desconectado. Escanea el QR nuevamente.");
        }
        // WhatsApp QR ready
        if (wa === "awaiting_scan" && prevStatus.current !== "awaiting_scan") {
          addToast("warning", "Código QR listo para escanear desde tu teléfono.");
        }
        // WhatsApp reconnected
        if (prevStatus.current !== "connected" && wa === "connected" && phone) {
          if (prevPhone.current !== phone) {
            addToast("info", `WhatsApp conectado: ${phone}`);
          } else {
            addToast("info", "WhatsApp reconectado.");
          }
        }
        prevStatus.current = wa;
        prevPhone.current = phone;

        // Campaign completed (log count increased)
        const logCount = dash?.ejecuciones_totales ?? 0;
        if (prevLogCount.current >= 0 && logCount > prevLogCount.current) {
          addToast("info", `Campaña ejecutada. Enviados hoy: ${dash?.enviados_hoy ?? 0}`);
        }
        prevLogCount.current = logCount;
      } catch {}
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => { mounted.current = false; clearInterval(id); };
  }, [addToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] space-y-2 max-w-sm pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto rounded-xl border shadow-lg p-4 flex items-start gap-3 transition-all duration-500 animate-slide-in ${
            t.tipo === "error"
              ? "bg-red-50 border-red-200 text-red-800"
              : t.tipo === "warning"
              ? "bg-yellow-50 border-yellow-200 text-yellow-800"
              : "bg-blue-50 border-blue-200 text-blue-800"
          }`}
        >
          <span className="text-lg leading-none shrink-0 mt-0.5">
            {t.tipo === "error" ? "✗" : t.tipo === "warning" ? "!" : "✓"}
          </span>
          <p className="text-sm">{t.mensaje}</p>
          <button
            onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
            className="ml-auto shrink-0 text-current opacity-50 hover:opacity-100"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
      <style>{`
        @keyframes slideIn { from { opacity: 0; transform: translateX(100px); } to { opacity: 1; transform: translateX(0); } }
        .animate-slide-in { animation: slideIn 0.3s ease-out; }
      `}</style>
    </div>
  );
}