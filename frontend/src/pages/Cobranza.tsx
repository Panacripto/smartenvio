import { useEffect, useState, useRef } from "react";
import api from "@/api/client";

export default function Cobranza() {
  const [clientes, setClientes] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const [criterio, setCriterio] = useState("ambas");
  const [cargando, setCargando] = useState(false);
  const [mensaje, setMensaje] = useState(
    "Hola *{FC_DESCRIPCION}*, su apreciada cuenta presenta  *{FC_DOCUMENTOS}* facturas *{FC_CRITERIO}* que totalizan un monto de *{FC_SALDO_TOTAL} $*. Agradecemos realizar el pago a la mayor brevedad posible, si ya realizo su pago, haga caso omiso a este mensaje, Gracias."
  );
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState("");
  const [resultadosDetalle, setResultadosDetalle] = useState<string[]>([]);
  const [whatsappStatus, setWhatsappStatus] = useState("disconnected");
  const [errorMsg, setErrorMsg] = useState("");
  const [showEmojis, setShowEmojis] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const EMOJIS = ["😀","😁","😂","🤣","😊","😎","👍","👎","🙌","👏","🎉","🎊","❤️","💯","✅","❌","⭐","🔥","💪","🤝","👋","📢","📌","🎯","💰","📈","📊","🏆","🛒","🚚","📦","🎁","🔔","📞","✉️","📱","☀️","🌧️","⏰","📅","🔴","🟢","🟡","🔵","🟣","⚪","🟠","🟤"];

  const insertarEmoji = (emoji: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const s = ta.selectionStart, e = ta.selectionEnd;
    setMensaje(prev => prev.substring(0, s) + emoji + prev.substring(e));
    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + emoji.length; ta.focus(); }, 0);
  };

  useEffect(() => {
    api.get("/whatsapp/status").then(r => setWhatsappStatus(r.data.status)).catch(() => {});
    api.get("/cobranza/config").then(r => {
      if (r.data.mensaje) setMensaje(r.data.mensaje);
    }).catch(() => {});
    cargar();
  }, []);

  const cargar = async (crit?: string) => {
    setCargando(true);
    setErrorMsg("");
    try {
      const c = crit ?? criterio;
      const params: Record<string, any> = { criterio: c };
      if (search) params.search = search;
      const r = await api.get("/cobranza", { params });
      setClientes(r.data);
      setSelected(new Set());
    } catch (e) {
      setClientes([]);
      setSelected(new Set());
      setErrorMsg("Error al cargar datos: " + (e.response?.data?.detail || e.message));
    }
    setCargando(false);
  };

  const toggleCliente = (cod: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(cod)) next.delete(cod); else next.add(cod);
      return next;
    });
  };

  const toggleTodos = () => {
    if (selected.size === clientes.length) setSelected(new Set());
    else setSelected(new Set(clientes.map(c => c.FC_CODIGO)));
  };

  const reemplazar = (texto: string, c: any) => {
    return texto
      .replace(/\{FC_CODIGO\}/g, c.FC_CODIGO ?? "")
      .replace(/\{FC_DESCRIPCION\}/g, c.FC_DESCRIPCION ?? "")
      .replace(/\{FC_TELEFONO\}/g, c.FC_TELEFONO ?? "")
      .replace(/\{FC_SALDO_TOTAL\}/g, Number(c.FC_SALDO_TOTAL)?.toFixed?.(2) ?? c.FC_SALDO_TOTAL ?? "")
      .replace(/\{FC_DOCUMENTOS\}/g, c.FC_DOCUMENTOS ?? "")
      .replace(/\{FC_CRITERIO\}/g, c.FC_CRITERIO ?? "");
  };

  const enviar = async () => {
    if (!mensaje) return;
    setEnviando(true);
    setResultado("");
    setResultadosDetalle([]);
    const detalle: string[] = [];
    let enviados = 0, fallidos = 0;

    for (const cod of selected) {
      const c = clientes.find(x => x.FC_CODIGO === cod);
      if (!c) continue;
      const tel = String(c.FC_TELEFONO || "").replace(/\D/g, "");
      if (!tel) { fallidos++; detalle.push(`✗ ${c.FC_DESCRIPCION} - sin teléfono`); continue; }
      const msg = reemplazar(mensaje, c);
      try {
        await api.post("/whatsapp/send", { telefono: tel, mensaje: msg });
        enviados++;
        detalle.push(`✓ ${c.FC_DESCRIPCION}`);
      } catch (e: any) {
        fallidos++;
        detalle.push(`✗ ${c.FC_DESCRIPCION}: ${e.response?.data?.detail || e.message || "Error"}`);
      }
    }

    setResultado(`✓ ${enviados} enviados | ✗ ${fallidos} fallidos`);
    setResultadosDetalle(detalle);
    setEnviando(false);
  };

  const formatearMonto = (n: number) => {
    return n?.toLocaleString?.("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? n;
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Cobranza</h2>

      <div className="flex gap-6">
        <div className="w-[420px] shrink-0 space-y-4">
          <div className="bg-white rounded-xl border shadow-md p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Mensaje de Cobranza</h3>
            <textarea
              ref={textareaRef}
              className="w-full border rounded-lg px-3 py-2.5 text-sm min-h-[150px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
              value={mensaje}
              onChange={e => setMensaje(e.target.value)}
            />
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span className="text-xs text-gray-500 mr-1 self-center">Insertar:</span>
              <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium transition-colors" onClick={() => {
                const ta = textareaRef.current; if (!ta) return;
                const s = ta.selectionStart, e = ta.selectionEnd;
                const v = mensaje.substring(0, s) + "{FC_DESCRIPCION}" + mensaje.substring(e);
                setMensaje(v);
                setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 17; ta.focus(); }, 0);
              }}>{`{Nombre}`}</button>
              <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium transition-colors" onClick={() => {
                const ta = textareaRef.current; if (!ta) return;
                const s = ta.selectionStart, e = ta.selectionEnd;
                const v = mensaje.substring(0, s) + "{FC_SALDO_TOTAL}" + mensaje.substring(e);
                setMensaje(v);
                setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
              }}>{`{Saldo}`}</button>
              <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium transition-colors" onClick={() => {
                const ta = textareaRef.current; if (!ta) return;
                const s = ta.selectionStart, e = ta.selectionEnd;
                const v = mensaje.substring(0, s) + "{FC_DOCUMENTOS}" + mensaje.substring(e);
                setMensaje(v);
                setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
              }}>{`{Documentos}`}</button>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <button
                className="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-md px-2 py-1 font-medium transition-colors flex items-center gap-1"
                onClick={() => setShowEmojis(!showEmojis)}
              >
                <span>😀</span> Emojis
              </button>
            </div>
            {showEmojis && (
              <div className="mt-1 p-2 border rounded-lg bg-white max-h-32 overflow-y-auto grid grid-cols-12 gap-0.5">
                {EMOJIS.map((e) => (
                  <button key={e} className="text-lg hover:bg-gray-100 rounded p-0.5 transition-colors" onClick={() => insertarEmoji(e)}>{e}</button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 bg-white rounded-xl border shadow-md p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Clientes con saldo pendiente</h3>

          <div className="flex items-center gap-4 mb-3">
            <div className="flex items-center gap-1 text-sm bg-gray-100 rounded-lg p-0.5">
              {(["vencidas", "por_vencer", "ambas"] as const).map(val => (
                <button key={val}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${criterio === val ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
                  onClick={() => { setCriterio(val); cargar(val); }}
                >
                  {val === "vencidas" ? "Solo vencidas" : val === "por_vencer" ? "Solo por vencer" : "Ambas"}
                </button>
              ))}
            </div>
            <div className="flex gap-2 flex-1">
              <input
                type="text" placeholder="Buscar por código, nombre o teléfono..."
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                value={search} onChange={e => setSearch(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") cargar(); }}
              />
              <button
                className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1.5"
                onClick={() => cargar()} disabled={cargando}
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

          <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 px-4 py-3 flex items-center gap-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">
              <input type="checkbox" checked={clientes.length > 0 && selected.size === clientes.length} onChange={toggleTodos} className="rounded border-gray-300" />
              <span>{selected.size} de {clientes.length}</span>
              <span className="ml-auto">
                Total: {formatearMonto(clientes.reduce((s, c) => s + (Number(c.FC_SALDO_TOTAL) || 0), 0))}
              </span>
            </div>
            <div className="max-h-[400px] overflow-y-auto divide-y divide-gray-100">
              {clientes.map((c, i) => (
                <label key={c.FC_CODIGO} className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer text-sm transition-colors hover:bg-green-50/60 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}>
                  <input type="checkbox" checked={selected.has(c.FC_CODIGO)} onChange={() => toggleCliente(c.FC_CODIGO)} className="rounded border-gray-300" />
                  <span className="font-mono text-xs font-medium text-gray-700 w-16">{c.FC_CODIGO}</span>
                  <span className="flex-1 truncate text-gray-700">{c.FC_DESCRIPCION}</span>
                  <span className="text-xs text-gray-400 w-28">{c.FC_TELEFONO || "-"}</span>
                  <span className="text-xs font-mono text-red-600 font-medium w-28 text-right">
                    {formatearMonto(c.FC_SALDO_TOTAL)}
                  </span>
                  <span className="text-xs text-gray-400 w-16 text-right">{c.FC_DOCUMENTOS} doc.</span>
                </label>
              ))}
              {clientes.length === 0 && !cargando && !errorMsg && (
                <p className="text-sm text-gray-400 text-center py-8">No hay clientes con saldo pendiente para este criterio</p>
              )}
              {errorMsg && (
                <p className="text-sm text-red-500 text-center py-8">{errorMsg}</p>
              )}
              {cargando && <p className="text-sm text-gray-400 text-center py-8">Cargando...</p>}
          </div>
        </div>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-4">
        <button
          className="bg-gradient-to-r from-red-500 to-red-600 text-white px-8 py-3 rounded-xl text-sm font-medium hover:from-red-600 hover:to-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-2"
          disabled={enviando || !mensaje || selected.size === 0 || clientes.length === 0 || whatsappStatus !== "connected"}
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
              Enviar recordatorio a {selected.size} cliente{selected.size !== 1 ? "s" : ""}
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
