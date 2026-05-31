import { useEffect, useState } from "react";
import api from "@/api/client";

export default function GestionPagos() {
  const [proveedores, setProveedores] = useState<any[]>([]);
  const [totalGeneral, setTotalGeneral] = useState(0);
  const [cantDocs, setCantDocs] = useState(0);
  const [search, setSearch] = useState("");
  const [criterio, setCriterio] = useState("todas");
  const [cargando, setCargando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState("");
  const [resultadosDetalle, setResultadosDetalle] = useState<string[]>([]);
  const [whatsappStatus, setWhatsappStatus] = useState("disconnected");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    api.get("/whatsapp/status").then(r => setWhatsappStatus(r.data.status)).catch(() => {});
    (async () => {
      try { await api.post("/gestion-pagos/sync"); } catch {}
      await cargarDatos();
    })();
  }, []);

  const cargarDatos = async (crit?: string) => {
    setCargando(true);
    setErrorMsg("");
    try {
      const c = crit ?? criterio;
      const params: Record<string, any> = { criterio: c };
      if (search) params.search = search;
      const r = await api.get("/gestion-pagos", { params });
      const data = r.data;
      if (Array.isArray(data)) {
        setProveedores([]);
        setTotalGeneral(0);
        setCantDocs(0);
      } else {
        setProveedores(data.proveedores || []);
        setTotalGeneral(data.total_general || 0);
        setCantDocs(data.cantidad_documentos || 0);
      }
    } catch (e: any) {
      setProveedores([]);
      setTotalGeneral(0);
      setCantDocs(0);
      setErrorMsg("Error al cargar: " + (e.response?.data?.detail || e.message));
    }
    setCargando(false);
  };

  const enviar = async () => {
    setEnviando(true);
    setResultado("");
    setResultadosDetalle([]);
    try {
      const r = await api.post("/gestion-pagos/enviar", null, { params: { criterio } });
      const d = r.data;
      setResultado(`✓ ${d.enviados} enviados | ✗ ${d.fallidos} fallidos`);
      setResultadosDetalle(d.detalles || []);
    } catch (e: any) {
      setResultado("Error: " + (e.response?.data?.detail || e.message));
      setResultadosDetalle([]);
    }
    setEnviando(false);
  };

  const formatearMonto = (n: number) =>
    n?.toLocaleString?.("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? String(n);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Gestión de Pagos</h2>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-1 text-sm bg-gray-100 rounded-lg p-0.5">
          {(["vencidas", "por_vencer", "todas"] as const).map(val => (
            <button key={val}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${criterio === val ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
              onClick={() => { setCriterio(val); cargarDatos(val); }}
            >
              {val === "vencidas" ? "Vencidas" : val === "por_vencer" ? "Por vencer" : "Todas"}
            </button>
          ))}
        </div>
        <div className="flex gap-2 flex-1">
          <input
            type="text" placeholder="Buscar por código o nombre del proveedor..."
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            value={search} onChange={e => setSearch(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") cargarDatos(); }}
          />
          <button
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1.5"
            onClick={() => cargarDatos()} disabled={cargando}
          >
            {cargando ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            )}
            {cargando ? "Buscando..." : "Buscar"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-md p-5">
        {proveedores.length > 0 && (
          <div className="flex items-center justify-between mb-3 text-sm text-gray-500">
            <span>{cantDocs} facturas de {proveedores.length} proveedores</span>
            <span className="font-semibold text-red-600">Total: ${formatearMonto(totalGeneral)}</span>
          </div>
        )}

        <div className="max-h-[500px] overflow-y-auto divide-y divide-gray-100">
          {proveedores.map((p) => (
            <div key={p.codigo} className="py-3">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-gray-800">{p.nombre}</span>
                <span className="text-xs font-mono text-red-600 font-semibold">${formatearMonto(p.total)}</span>
              </div>
              <div className="space-y-0.5">
                {p.documentos.map((d: any, i: number) => (
                  <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-x-3 text-xs text-gray-500 pl-2 items-center">
                    <span className="font-mono truncate">{d.numero}</span>
                    <span className="font-mono whitespace-nowrap text-right">${d.monto.toFixed(2)}</span>
                    <span className={`whitespace-nowrap text-right ${d.dias > 0 ? "text-red-500 font-medium" : "text-amber-500"}`}>
                      {d.fecha_vencimiento} ({d.dias > 0 ? `${d.dias}d vencido` : d.dias < 0 ? `${Math.abs(d.dias)}d` : "hoy"})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {proveedores.length === 0 && !cargando && !errorMsg && (
            <p className="text-sm text-gray-400 text-center py-8">No hay proveedores con deuda pendiente</p>
          )}
          {errorMsg && (
            <p className="text-sm text-red-500 text-center py-8">{errorMsg}</p>
          )}
          {cargando && <p className="text-sm text-gray-400 text-center py-8">Cargando...</p>}
        </div>
      </div>

      <div className="mt-6 flex items-center gap-4">
        <button
          className="bg-gradient-to-r from-red-500 to-red-600 text-white px-8 py-3 rounded-xl text-sm font-medium hover:from-red-600 hover:to-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-2"
          disabled={enviando || proveedores.length === 0 || whatsappStatus !== "connected"}
          onClick={enviar}
        >
          {enviando ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              Enviando...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
              Enviar recordatorio a teléfonos configurados
            </span>
          )}
        </button>
        {resultado && <span className="text-sm font-medium">{resultado}</span>}
      </div>

      {resultadosDetalle.length > 0 && (
        <div className="mt-4 bg-white border rounded-xl shadow-md p-5 max-h-40 overflow-y-auto">
          <p className="text-xs font-medium text-gray-500 mb-2">Detalle de envíos:</p>
          <div className="text-xs space-y-0.5">
            {resultadosDetalle.map((d, i) => (
              <div key={i} className={d.startsWith("✓") ? "text-green-600" : "text-red-600"}>{d}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
