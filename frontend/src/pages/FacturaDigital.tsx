import { useEffect, useState, useRef } from "react";
import api from "@/api/client";

interface Factura {
  FTI_DOCUMENTO: string;
  FTI_FECHAEMISION: string;
  FTI_MONEDA: number;
  FTI_FACTORREFERENCIA: number;
  FTI_RESPONSABLE: string;
  FTI_PERSONACONTACTO: string | null;
  FTI_TELEFONOCONTACTO: string | null;
  FC_TELEFONO: string | null;
  FC_DESCRIPCION: string | null;
  BI_DIVISA: number;
  IVA_DIVISA: number;
  TOTAL_DIVISA: number;
  SALDO_DIVISA: number;
  FTI_TOTALNETO: number;
  FTI_SALDOOPERACION: number;
  enviado?: string | boolean | null;
  enviado_en?: string | null;
  envio_estado?: string | null;
  sin_telefono?: boolean;
}

const FILTROS = [
  { key: "todo", label: "Todo" },
  { key: "hoy", label: "Hoy" },
  { key: "semana", label: "Semana" },
  { key: "mes", label: "Mes" },
  { key: "anio", label: "Año" },
  { key: "personalizado", label: "Personalizado" },
];

export default function FacturaDigital() {
  const [facturas, setFacturas] = useState<Factura[]>([]);
  const [search, setSearch] = useState("");
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState("");
  const [resultadosDetalle, setResultadosDetalle] = useState<string[]>([]);
  const [fdEmpresaRazon, setFdEmpresaRazon] = useState("");
  const [fdEmpresaRif, setFdEmpresaRif] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [fdMensaje, setFdMensaje] = useState("");
  const [filtro, setFiltro] = useState("todo");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [seleccionadas, setSeleccionadas] = useState<Set<string>>(new Set());
  const [metrics, setMetrics] = useState<any>(null);
  const [modalTipo, setModalTipo] = useState<string | null>(null);

  const paramsBusqueda = (filtroOverride?: string, desdeOverride?: string, hastaOverride?: string) => {
    const f = filtroOverride ?? filtro;
    const d = desdeOverride ?? desde;
    const h = hastaOverride ?? hasta;
    const p: Record<string, any> = {};
    if (search) p.search = search;
    if (f !== "todo") p.filtro = f;
    if (f === "personalizado") {
      if (d) p.desde = d;
      if (h) p.hasta = h;
    }
    return p;
  };

  const cargar = async (filtroOverride?: string, desdeOverride?: string, hastaOverride?: string) => {
    const f = filtroOverride ?? filtro;
    const d = desdeOverride ?? desde;
    const h = hastaOverride ?? hasta;
    const p: Record<string, any> = {};
    if (search) p.search = search;
    if (f !== "todo") p.filtro = f;
    if (f === "personalizado") {
      if (d) p.desde = d;
      if (h) p.hasta = h;
    }
    setCargando(true);
    try {
      const [r1, r2, r3] = await Promise.all([
        api.get("/factura-digital", { params: p }),
        api.get("/factura-digital/config"),
        api.get("/factura-digital/metrics"),
      ]);
      setFacturas(r1.data);
      setFdMensaje(r2.data.mensaje || "");
      setFdEmpresaRazon(r2.data.empresa_razon_social || "");
      setFdEmpresaRif(r2.data.empresa_rif || "");
      setMetrics(r3.data);
    } catch { }
    setCargando(false);
  };

  useEffect(() => { cargar(); }, []);

  const cargarRef = useRef(cargar);
  cargarRef.current = cargar;
  useEffect(() => {
    const interval = setInterval(() => cargarRef.current(), 30000);
    return () => clearInterval(interval);
  }, []);

  const formatearFecha = (f: string) => {
    if (!f) return "";
    return f.split("T")[0] || f.split(" ")[0] || f;
  };

  const agruparPorCliente = () => {
    const grupos: Record<string, { telefono: string; cliente: string; facturas: Factura[] }> = {};
    for (const f of facturas) {
      const tel = (f.FTI_TELEFONOCONTACTO || f.FC_TELEFONO || "").replace(/\s/g, "").replace(/-/g, "");
      if (!tel) continue;
      const key = tel + "|" + f.FTI_RESPONSABLE;
      if (!grupos[key]) grupos[key] = { telefono: tel, cliente: f.FTI_PERSONACONTACTO || f.FC_DESCRIPCION || f.FTI_RESPONSABLE || "", facturas: [] };
      grupos[key].facturas.push(f);
    }
    return grupos;
  };

  const generarMensaje = (cliente: string, facturas: Factura[]) => {
    const bloqueFacturas = facturas.map(f => {
      const fecha = formatearFecha(f.FTI_FECHAEMISION);
      const totalNeto = f.FTI_TOTALNETO || 0;
      const moneda = f.FTI_MONEDA || 0;
      const factor = f.FTI_FACTORREFERENCIA || 1;
      const totalBs = moneda === 2 ? totalNeto * factor : totalNeto;
      const totalUsd = totalBs / (factor || 1);
      return `DOCUMENTO: ${f.FTI_DOCUMENTO}\nFECHA: ${fecha}\nTOTAL$: ${totalUsd.toFixed(2)}\nTASA: ${factor.toFixed(2)}\nTOTAL Bs.: ${totalBs.toFixed(2)}`;
    }).join("\n\n");
    const plantilla = fdMensaje || "Estimado: {cliente} hemos emitido la siguiente(s) facturas a su nombre:\n{facturas}";
    return plantilla
      .replace("{empresa_razon_social}", fdEmpresaRazon || "")
      .replace("{empresa_rif}", fdEmpresaRif || "")
      .replace("{cliente}", cliente)
      .replace("{facturas}", bloqueFacturas);
  };

  const enviarSeleccionadas = async () => {
    const docs = Array.from(seleccionadas);
    if (docs.length === 0) {
      setResultado("Selecciona al menos una factura");
      return;
    }

    setEnviando(true);
    setShowPreview(false);
    setResultado("");
    setResultadosDetalle([]);
    try {
      const r = await api.post("/factura-digital/enviar-seleccionados", { documentos: docs });
      const sinTel = r.data.sin_telefono || 0;
      setResultado(`✓ ${r.data.enviados} enviados | ✗ ${r.data.fallidos} fallidos${sinTel ? ` | X ${sinTel} sin telefono` : ""}`);
      setResultadosDetalle(r.data.detalles || []);
    } catch (e: any) {
      setResultado(`Error: ${e.response?.data?.detail || e.message || "desconocido"}`);
    }
    setEnviando(false);
    setSeleccionadas(new Set());
    cargar();
  };

  const fm = (n: number) =>
    n?.toLocaleString?.("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? n;

  const estadoIcono = (e: string | boolean | null | undefined, sinTel?: boolean) => {
    if (sinTel) return "\u26A0";
    if (e === true || e === "enviado" || e === "sent") return "\u25CF";
    if (e === "confirmado") return "✓";
    if (e === "pendiente") return "\u23F3";
    if (e === "fallido") return "✗";
    if (e === "no_phone") return "\u26A0";
    return "\u2013";
  };
  const estadoColor = (e: string | boolean | null | undefined, sinTel?: boolean) => {
    if (sinTel) return "#ea580c";
    if (e === true || e === "enviado" || e === "sent") return "#ca8a04";
    if (e === "confirmado") return "#16a34a";
    if (e === "pendiente") return "#3b82f6";
    if (e === "fallido") return "#ef4444";
    if (e === "no_phone") return "#ea580c";
    return "#9ca3af";
  };

  const quitarEnvio = async (doc: string) => {
    try {
      await api.delete(`/factura-digital/envio/${encodeURIComponent(doc)}`);
      cargar();
    } catch {}
  };

  const conTelefono = facturas.filter(f => f.FTI_TELEFONOCONTACTO || f.FC_TELEFONO);
  const grupos = agruparPorCliente();
  const phonesUnicos = new Set(conTelefono.map(f => f.FTI_TELEFONOCONTACTO || f.FC_TELEFONO));
  const totalClientesEnvio = Object.keys(grupos).length;
  const cantSel = Array.from(seleccionadas).filter(d => facturas.find(f => f.FTI_DOCUMENTO === d)).length;

  return (
    <div className="h-full overflow-y-auto p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Factura Digital</h2>

      {metrics && (
        <div className="grid grid-cols-6 gap-3 mb-4">
          <div className="bg-white rounded-xl border shadow-sm p-3 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-lg">{metrics.total}</div>
            <div><p className="text-xs font-medium text-gray-800">Total</p><p className="text-[10px] text-gray-400">Facturas</p></div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-3 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-600 font-bold text-lg">{metrics.enviadas + metrics.confirmadas}</div>
            <div><p className="text-xs font-medium text-gray-800">Enviadas</p><p className="text-[10px] text-gray-400">{metrics.confirmadas > 0 ? `${metrics.confirmadas} confirmadas` : ""}</p></div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-3 flex items-center gap-3 cursor-pointer hover:shadow-md transition-shadow" onClick={() => metrics.fallidas > 0 && setModalTipo("fallidas")}>
            <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center text-red-600 font-bold text-lg">{metrics.fallidas}</div>
            <div><p className="text-xs font-medium text-gray-800">Fallidas</p><p className="text-[10px] text-gray-400">Error al enviar</p></div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-3 flex items-center gap-3 cursor-pointer hover:shadow-md transition-shadow" onClick={() => metrics.pendientes > 0 && setModalTipo("pendientes")}>
            <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-gray-600 font-bold text-lg">{metrics.pendientes}</div>
            <div><p className="text-xs font-medium text-gray-800">Pendientes</p><p className="text-[10px] text-gray-400">Sin enviar</p></div>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-3 flex items-center gap-3 cursor-pointer hover:shadow-md transition-shadow" onClick={() => metrics.sin_telefono > 0 && setModalTipo("sin_telefono")}>
            <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center text-orange-600 font-bold text-lg">{metrics.sin_telefono}</div>
            <div><p className="text-xs font-medium text-gray-800">Sin Tel.</p><p className="text-[10px] text-gray-400">No se enviaran</p></div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border shadow-md p-5">
        <div className="flex items-center gap-2 mb-3">
          {FILTROS.map(f => (
            <button key={f.key}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filtro === f.key ? "bg-gradient-to-r from-green-500 to-green-600 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
              onClick={() => { setFiltro(f.key); if (f.key !== "personalizado") cargar(f.key); }}
            >
              {f.label}
            </button>
          ))}
        </div>
        {filtro === "personalizado" && (
          <div className="flex items-center gap-2 mb-3">
            <input type="date" className="border rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-green-500" value={desde} onChange={e => { setDesde(e.target.value); }} />
            <span className="text-xs text-gray-400">a</span>
            <input type="date" className="border rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-green-500" value={hasta} onChange={e => { setHasta(e.target.value); }} />
            <button className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-blue-600 hover:to-blue-700 shadow-sm flex items-center gap-1" onClick={() => cargar("personalizado", desde, hasta)}>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
              Filtrar
            </button>
          </div>
        )}
        <div className="flex items-center gap-2 mb-4">
          <input
            type="text"
            placeholder="Buscar por documento o responsable..."
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") cargar(); }}
          />
          <button
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1.5"
            onClick={() => cargar()}
            disabled={cargando}
          >
            {cargando ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            )}
            {cargando ? "Buscando..." : "Buscar"}
          </button>
          <button
            className="bg-gradient-to-r from-gray-500 to-gray-600 text-white rounded-lg px-3 py-2 text-sm font-medium hover:from-gray-600 hover:to-gray-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1.5"
            onClick={() => setShowPreview(true)}
            disabled={totalClientesEnvio === 0}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
            Vista previa
          </button>
          <button
            className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-1.5"
            onClick={enviarSeleccionadas}
            disabled={enviando || cantSel === 0}
          >
            {enviando ? (
              <span className="flex items-center gap-1.5">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                Enviando...
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                Enviar a {cantSel} cliente{cantSel !== 1 ? "s" : ""}
              </span>
            )}
          </button>
        </div>

        <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 px-4 py-3 flex items-center gap-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">
            <span className="w-8 text-center">
              <input type="checkbox"
                className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
                checked={facturas.length > 0 && seleccionadas.size === facturas.filter(f => !f.enviado && !f.sin_telefono).length}
                onChange={() => {
                  const seleccionables = facturas.filter(f => !f.enviado && !f.sin_telefono).map(f => f.FTI_DOCUMENTO);
                  if (seleccionadas.size === seleccionables.length) setSeleccionadas(new Set());
                  else setSeleccionadas(new Set(seleccionables));
                }}
              />
            </span>
            <span className="w-20">Documento</span>
            <span className="w-20">Emisi&oacute;n</span>
            <span className="flex-1">Cliente</span>
            <span className="w-20 text-right">Total</span>
            <span className="w-20 text-right">Saldo</span>
            <span className="w-24">Tel&eacute;fono</span>
            <span className="w-32">Env&iacute;o</span>
            <span className="w-12 text-center">Env.</span>
          </div>
          <div className="max-h-[600px] overflow-y-auto divide-y divide-gray-100">
            {facturas.map((f, i) => (
              <div key={i} className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${seleccionadas.has(f.FTI_DOCUMENTO) ? 'bg-green-50/80' : i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'} hover:bg-green-50/60`}>
                <span className="w-8 flex items-center justify-center">
                  <input type="checkbox"
                    className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
                    checked={seleccionadas.has(f.FTI_DOCUMENTO)}
                    disabled={!!f.enviado || !!f.sin_telefono}
                    onChange={() => {
                      setSeleccionadas(prev => {
                        const next = new Set(prev);
                        if (next.has(f.FTI_DOCUMENTO)) next.delete(f.FTI_DOCUMENTO); else next.add(f.FTI_DOCUMENTO);
                        return next;
                      });
                    }}
                  />
                </span>
                <span className="w-20 font-mono text-xs font-medium text-gray-700">{f.FTI_DOCUMENTO}</span>
                <span className="w-20 text-xs text-gray-500">{formatearFecha(f.FTI_FECHAEMISION)}</span>
                <span className="flex-1 truncate text-xs text-gray-700">{f.FTI_PERSONACONTACTO || f.FC_DESCRIPCION || f.FTI_RESPONSABLE}</span>
                <span className="w-20 text-right text-xs font-mono text-red-600 font-medium">{fm(f.TOTAL_DIVISA)}</span>
                <span className="w-20 text-right text-xs font-mono text-gray-600">{fm(f.SALDO_DIVISA)}</span>
                <span className="w-24 text-xs text-gray-400 truncate">{f.FTI_TELEFONOCONTACTO || f.FC_TELEFONO || <span className="text-orange-500 font-medium">Sin teléfono</span>}</span>
                <span className="w-32 text-xs text-gray-400 truncate">{f.enviado_en || "-"}</span>
                <span className="w-12 text-center text-xs font-bold" style={{ color: estadoColor(f.enviado, f.sin_telefono), cursor: f.enviado ? "pointer" : "default" }} title={f.sin_telefono ? "Sin telefono" : f.enviado ? "Click para quitar envio" : ""} onClick={() => { if (f.enviado) quitarEnvio(f.FTI_DOCUMENTO); }}>{estadoIcono(f.enviado, f.sin_telefono)}</span>
              </div>
            ))}
            {facturas.length === 0 && !cargando && (
              <p className="text-sm text-gray-400 text-center py-8">No hay facturas emitidas</p>
            )}
            {cargando && <p className="text-sm text-gray-400 text-center py-8">Cargando...</p>}
          </div>
        </div>
        {facturas.length > 0 && (
          <p className="text-xs text-gray-400 mt-2">{facturas.length} factura{facturas.length !== 1 ? "s" : ""}</p>
        )}
      </div>

      {resultado && (
        <div className="bg-white rounded-xl border shadow-md p-5 mt-4">
          <p className="text-sm font-medium mb-2">{resultado}</p>
          {resultadosDetalle.length > 0 && (
            <div className="max-h-40 overflow-y-auto text-xs space-y-0.5">
              {resultadosDetalle.map((d, i) => (
                <div key={i} className={d.startsWith("✓") ? "text-green-600" : "text-red-600"}>{d}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowPreview(false)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">Vista previa del envio</h3>
              <button className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg p-1.5 transition-colors" onClick={() => setShowPreview(false)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {(() => {
                const selDocs = new Set(seleccionadas);
                const selGrupos: Record<string, { telefono: string; cliente: string; facturas: Factura[] }> = {};
                for (const f of facturas) {
                  if (!selDocs.has(f.FTI_DOCUMENTO)) continue;
                  if (f.sin_telefono) continue;
                  const tel = (f.FTI_TELEFONOCONTACTO || f.FC_TELEFONO || "").replace(/\s/g, "").replace(/-/g, "");
                  if (!tel) continue;
                  const key = tel + "|" + f.FTI_RESPONSABLE;
                  if (!selGrupos[key]) selGrupos[key] = { telefono: tel, cliente: f.FTI_PERSONACONTACTO || f.FC_DESCRIPCION || f.FTI_RESPONSABLE || "", facturas: [] };
                  selGrupos[key].facturas.push(f);
                }
                return Object.values(selGrupos);
              })().map((grupo, i) => (
                <div key={i} className="border rounded-lg p-3">
                  <p className="text-xs font-medium text-gray-500 mb-2">
                    {grupo.cliente} - {grupo.telefono} ({grupo.facturas.length} factura{grupo.facturas.length !== 1 ? "s" : ""})
                  </p>
                  <pre className="text-xs bg-gray-50 p-3 rounded whitespace-pre-wrap font-sans">
                    {generarMensaje(grupo.cliente, grupo.facturas)}
                  </pre>
                </div>
              ))}
            </div>
            <div className="p-4 border-t flex justify-end gap-2">
              <button className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 flex items-center gap-1.5 transition-colors" onClick={() => setShowPreview(false)}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                Cancelar
              </button>
              <button className="px-4 py-2 text-sm bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 shadow-sm flex items-center gap-1.5 transition-all" onClick={enviarSeleccionadas} disabled={enviando}>
                {enviando ? (
                  <span className="flex items-center gap-1.5">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Enviando...
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                    Confirmar env&iacute;o a {cantSel} cliente{cantSel !== 1 ? "s" : ""}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {modalTipo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setModalTipo(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">
                {modalTipo === "fallidas" ? "Facturas fallidas" : modalTipo === "pendientes" ? "Facturas pendientes" : "Facturas sin teléfono"}
              </h3>
              <button className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg p-1.5 transition-colors" onClick={() => setModalTipo(null)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 uppercase tracking-wider border-b">
                    <th className="pb-2 pr-2">Documento</th>
                    <th className="pb-2 pr-2">Fecha</th>
                    <th className="pb-2 pr-2">Cliente</th>
                    <th className="pb-2">{modalTipo === "fallidas" ? "Error" : "Teléfono"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {facturas.filter(f => {
                    if (modalTipo === "fallidas") return f.envio_estado === "fallido";
                    if (modalTipo === "pendientes") return !f.enviado && !f.sin_telefono;
                    if (modalTipo === "sin_telefono") return f.sin_telefono;
                    return false;
                  }).map((f, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="py-2 pr-2 font-mono">{f.FTI_DOCUMENTO}</td>
                      <td className="py-2 pr-2 text-gray-500">{formatearFecha(f.FTI_FECHAEMISION)}</td>
                      <td className="py-2 pr-2 text-gray-700 truncate max-w-[200px]">{f.FTI_PERSONACONTACTO || f.FC_DESCRIPCION || f.FTI_RESPONSABLE}</td>
                      <td className="py-2 text-gray-500">{modalTipo === "fallidas" ? f.envio_estado : f.FTI_TELEFONOCONTACTO || f.FC_TELEFONO || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {facturas.filter(f => {
                if (modalTipo === "fallidas") return f.envio_estado === "fallido";
                if (modalTipo === "pendientes") return !f.enviado && !f.sin_telefono;
                if (modalTipo === "sin_telefono") return f.sin_telefono;
                return false;
              }).length === 0 && (
                <p className="text-xs text-gray-400 text-center py-8">No hay facturas en esta categoría</p>
              )}
            </div>
            <div className="p-4 border-t flex justify-end">
              <button className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors" onClick={() => setModalTipo(null)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
