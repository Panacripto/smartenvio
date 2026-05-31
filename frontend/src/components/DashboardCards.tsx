import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getShowRates } from "@/lib/theme";

type DashboardData = {
  whatsapp_connected: boolean;
  whatsapp_phone: string | null;
  campanas_activas: number;
  ejecuciones_totales: number;
  enviados_hoy: number;
  fallidos_hoy: number;
  total_clientes: number;
  total_contactos: number;
  total_inventario: number;
  total_cxc: number;
  total_cxp: number;
};

type RatesData = {
  bcv_usd: number;
  bcv_eur: number;
  usdt_avg: number;
  brecha_pct: number;
  timestamp: string;
};

export default function DashboardCards() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [rates, setRates] = useState<RatesData | null>(null);
  const [modalTipo, setModalTipo] = useState<string | null>(null);
  const [ejecuciones, setEjecuciones] = useState<any[]>([]);
  const [cargandoEj, setCargandoEj] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const showRates = getShowRates();
    const poll = async () => {
      try {
        const r = await fetch("http://127.0.0.1:8000/api/dashboard/resumen");
        if (mounted.current) setData(await r.json());
      } catch {}
      if (showRates) {
        try {
          const r = await fetch("http://127.0.0.1:8000/api/rates");
          if (mounted.current) {
            const j = await r.json();
            if (!j.error) setRates(j);
          }
        } catch {}
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => { mounted.current = false; clearInterval(id); };
  }, []);

  useEffect(() => {
    if (!modalTipo) return;
    setCargandoEj(true);
    fetch(`http://127.0.0.1:8000/api/dashboard/ejecuciones-hoy?tipo=${modalTipo}`)
      .then(r => r.ok ? r.json() : [])
      .then(d => { setEjecuciones(Array.isArray(d) ? d : []); })
      .catch(() => setEjecuciones([]))
      .finally(() => setCargandoEj(false));
  }, [modalTipo]);

  if (!data) return null;

  const cards = [
    {
      label: "WhatsApp",
      value: data.whatsapp_phone ? data.whatsapp_phone : data.whatsapp_connected ? "Conectado" : "Desconectado",
      color: data.whatsapp_connected ? "text-green-600" : "text-red-500",
      bg: data.whatsapp_connected ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200",
      icon: "M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z",
      onClick: null,
    },
    {
      label: "Campañas activas",
      value: String(data.campanas_activas),
      color: "text-blue-600",
      bg: "bg-blue-50 border-blue-200",
      icon: "M11 3.055A9.001 9.001 0 1020.945 13H11V3.055zM13 2.055V11h8.945A9.001 9.001 0 0013 2.055z",
      onClick: () => navigate("/campaigns?filtro=activas"),
    },
    {
      label: "Enviados hoy",
      value: String(data.enviados_hoy),
      color: "text-green-600",
      bg: "bg-green-50 border-green-200",
      icon: "M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2z",
      onClick: () => setModalTipo("enviados"),
    },
    {
      label: "Fallidos hoy",
      value: String(data.fallidos_hoy),
      color: "text-red-600",
      bg: "bg-red-50 border-red-200",
      icon: "M12 9v2m0 4h.01m21 12a9 9 0 11-18 0 9 9 0 0118 0z",
      onClick: () => setModalTipo("fallidos"),
    },
    {
      label: "Clientes a2",
      value: String(data.total_clientes),
      color: "text-purple-600",
      bg: "bg-purple-50 border-purple-200",
      icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z",
      onClick: () => navigate("/envio-masivo"),
    },
    {
      label: "Contactos",
      value: String(data.total_contactos),
      color: "text-amber-600",
      bg: "bg-amber-50 border-amber-200",
      icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
      onClick: () => navigate("/envio-masivo"),
    },
  ];

  const rateCards = rates ? [
    { label: "BCV USD", value: rates.bcv_usd.toFixed(2), color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200" },
    { label: "BCV EUR", value: rates.bcv_eur.toFixed(2), color: "text-sky-600", bg: "bg-sky-50 border-sky-200" },
    { label: "USDT prom.", value: rates.usdt_avg.toFixed(2), color: "text-violet-600", bg: "bg-violet-50 border-violet-200" },
    {
      label: "Brecha",
      value: rates.brecha_monto.toFixed(2),
      sub: `${rates.brecha_pct.toFixed(1)}%`,
      color: "text-orange-600",
      bg: "bg-orange-50 border-orange-200",
    },
  ] : [];

  return (
    <>
      <div className="grid grid-cols-6 gap-3 mb-4">
        {cards.map((c) => (
          <div key={c.label} className={`rounded-xl border p-3 ${c.bg} ${c.onClick ? "cursor-pointer hover:shadow-md transition-shadow" : ""}`} onClick={c.onClick || undefined}>
            <div className="flex flex-col items-center text-center gap-1">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${c.bg.replace("50", "100")}`}>
                <svg className={`w-4 h-4 ${c.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={c.icon} />
                </svg>
              </div>
              <p className={`text-lg font-bold ${c.color} leading-none`}>{c.value}</p>
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider leading-tight">{c.label}</p>
            </div>
          </div>        
        ))}
      </div>
      {rateCards.length > 0 && (
        <div className="grid grid-cols-4 gap-3 mb-4">
          {rateCards.map((c: any) => (
            <div key={c.label} className={`rounded-xl border p-3 ${c.bg}`}>
              <div className="flex flex-col items-center text-center gap-1">
                <p className={`text-lg font-bold ${c.color} leading-none`}>{c.value}</p>
                {c.sub && <span className={`text-[10px] font-semibold ${c.color}`}>{c.sub}</span>}
                <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider leading-tight">{c.label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {modalTipo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setModalTipo(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">{modalTipo === "enviados" ? "Enviados hoy" : "Fallidos hoy"}</h3>
              <button className="text-gray-400 hover:text-gray-600 p-1" onClick={() => setModalTipo(null)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {cargandoEj ? (
                <p className="text-sm text-gray-400 text-center py-8">Cargando...</p>
              ) : ejecuciones.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Sin resultados hoy</p>
              ) : (
                <div className="space-y-3">
                  {ejecuciones.map((ej: any) => {
                    const detalles = Array.isArray(ej.detalles) ? ej.detalles : [];
                    return (
                      <div key={ej.id} className="border rounded-xl overflow-hidden">
                        <div className="px-4 py-2 bg-gray-50 border-b flex items-center justify-between text-sm">
                          <span className="font-medium text-gray-700">{ej.campaign_nombre || "Campaña #" + ej.campaign_id}</span>
                          <span className="text-xs text-gray-400">{ej.ejecutado_en?.replace("T", " ")}</span>
                        </div>
                        {detalles.length > 0 ? (
                          <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                            {detalles.map((d: string, i: number) => (
                              <div key={i} className={"px-4 py-2 text-xs " + (d.startsWith("✓") || d.startsWith("OK") ? "text-gray-700" : "text-red-600")}>
                                {d}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="px-4 py-3 text-xs text-gray-400 text-center">Sin detalles</div>
                        )}
                        <div className="px-4 py-1.5 bg-gray-50 text-xs text-gray-500 flex gap-3 border-t">
                          <span className="text-green-600">✓ {ej.enviados} enviados</span>
                          <span className="text-red-600">✗ {ej.fallidos} fallidos</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
