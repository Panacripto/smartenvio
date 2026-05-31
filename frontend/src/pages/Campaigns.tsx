import { useEffect, useState, useRef, useCallback } from "react";
import api from "@/api/client";

const EMOJIS = [
  "😀","😁","😂","🤣","😊","😎","👍","👎","🙌","👏","🎉","🎊",
  "❤️","💯","✅","❌","⭐","🔥","💪","🤝","👋","📢","📌","🎯",
  "💰","📈","📊","🏆","🛒","🚚","📦","🎁","🔔","📞","✉️","📱",
  "☀️","🌧️","⏰","📅","🔴","🟢","🟡","🔵","🟣","⚪","🟠","🟤",
];

const INTERVALOS = [
  { key: "diario", label: "Diario" },
  { key: "interdiario", label: "Interdiario" },
  { key: "semanal", label: "Semanal" },
  { key: "mensual", label: "Mensual" },
];

const FILTROS = [
  { tipo: "facturas_vencidas", label: "Facturas vencidas", desc: "Clientes con cuentas por cobrar vencidas", tieneValor: false },
  { tipo: "por_vencer", label: "Por vencer (próximos N días)", desc: "Clientes con facturas por vencer en un rango de días", tieneValor: true, valorLabel: "Días", valorDefault: 7 },
  { tipo: "con_saldo", label: "Con saldo pendiente", desc: "Clientes con cualquier saldo > 0 en cuentas por cobrar", tieneValor: false },
  { tipo: "saldo_mayor_que", label: "Saldo mayor que...", desc: "Clientes con saldo total mayor a un monto específico", tieneValor: true, valorLabel: "Monto ($)", valorDefault: 100 },
  { tipo: "vencidas_saldo_mayor_que", label: "Vencidas + saldo > monto", desc: "Solo facturas vencidas con saldo mayor a un monto", tieneValor: true, valorLabel: "Monto ($)", valorDefault: 100 },
];

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [paginas, setPaginas] = useState(1);
  const [cargando, setCargando] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [showLog, setShowLog] = useState<any>(null);
  const [logData, setLogData] = useState<any[]>([]);
  const [showEmojis, setShowEmojis] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [filtroEstado, setFiltroEstado] = useState("todas");
  const [busqueda, setBusqueda] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [segmento, setSegmento] = useState("");

  const [nombre, setNombre] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [intervalo, setIntervalo] = useState("diario");
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [horaEnvio, setHoraEnvio] = useState("");
  const [horaFin, setHoraFin] = useState("");
  const [repetirCada, setRepetirCada] = useState(0);
  const [adjuntos, setAdjuntos] = useState<{ file: File; name: string; base64: string; mimetype: string }[]>([]);
  const [guardando, setGuardando] = useState(false);

  const [clientes, setClientes] = useState<any[]>([]);
  const [clientesCargando, setClientesCargando] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchCli, setSearchCli] = useState("");
  const [codigoDesde, setCodigoDesde] = useState("");
  const [codigoHasta, setCodigoHasta] = useState("");
  const [usarFiltro, setUsarFiltro] = useState(false);
  const [filtroTipo, setFiltroTipo] = useState("");
  const [filtroValor, setFiltroValor] = useState("");
  const [filtroPreview, setFiltroPreview] = useState<{ total: number; clientes: any[] } | null>(null);
  const [previewMsg, setPreviewMsg] = useState<string | null>(null);

  const calcularProximaEjecucion = (c: any): string | null => {
    if (!c.activo) return null;
    const hoy = new Date();
    const fechaFin = c.fecha_fin ? new Date(c.fecha_fin + "T23:59:59") : null;
    if (fechaFin && fechaFin < hoy) return "Finalizada";
    if (!c.hora_envio) return null;
    const [hh, mm] = c.hora_envio.split(":").map(Number);
    const hf = c.hora_fin ? c.hora_fin.split(":").map(Number) : null;
    const fInicio = c.fecha_inicio ? new Date(c.fecha_inicio + "T" + c.hora_envio) : null;
    if (fInicio && fInicio > hoy) return fInicio.toLocaleString("es-VE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: true });
    if (c.ultima_ejecucion && c.repetir_cada > 0) {
      const ult = new Date(c.ultima_ejecucion);
      const sig = new Date(ult.getTime() + c.repetir_cada * 3600000);
      if (sig.toDateString() === ult.toDateString() && (!hf || sig.getHours() < hf[0] || (sig.getHours() === hf[0] && sig.getMinutes() <= hf[1]))) {
        if (sig > hoy) return sig.toLocaleString("es-VE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: true });
      }
    }
    const base = new Date();
    base.setHours(hh, mm, 0, 0);
    if (base <= hoy) base.setDate(base.getDate() + 1);
    switch (c.intervalo) {
      case "diario": break;
      case "interdiario": base.setDate(base.getDate() + 1); break;
      case "semanal": base.setDate(base.getDate() + 6); break;
      case "mensual": base.setMonth(base.getMonth() + 1); break;
    }
    if (fechaFin && base > fechaFin) return "Finalizada";
    return base.toLocaleString("es-VE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: true });
  };

  const cargar = async (pag = 1) => {
    setCargando(true);
    try {
      const params: Record<string, any> = {
        filtro: filtroEstado, q: busqueda, page: pag, per_page: 20,
      };
      const r = await api.get("/campaigns", { params });
      setCampaigns(r.data.data);
      setTotal(r.data.total);
      setPagina(r.data.page);
      setPaginas(Math.max(1, Math.ceil(r.data.total / r.data.per_page)));
    } catch {}
    setCargando(false);
  };

  useEffect(() => { cargar(); }, [filtroEstado, busqueda, desde, hasta, segmento]);
  useEffect(() => { const iv = setInterval(() => cargar(pagina), 10000); return () => clearInterval(iv); }, [pagina, filtroEstado, busqueda, desde, hasta, segmento]);

  const cargarClientes = async () => {
    setClientesCargando(true);
    try {
      const params: Record<string, any> = { solo_con_telefono: true };
      if (searchCli) params.search = searchCli;
      if (codigoDesde) params.codigo_desde = codigoDesde;
      if (codigoHasta) params.codigo_hasta = codigoHasta;
      const contactosParams: Record<string, any> = {};
      if (searchCli) contactosParams.search = searchCli;
      const [r, rContactos] = await Promise.all([
        api.get("/clientes", { params }),
        api.get("/contactos", { params: contactosParams }),
      ]);
      const contactosMapped = rContactos.data.map((c: any) => ({
        FC_CODIGO: `CONTACTO_${c.id}`,
        FC_DESCRIPCION: c.nombre,
        FC_TELEFONO: c.telefono,
        _esContacto: true,
      }));
      setClientes([...r.data, ...contactosMapped]);
    } catch {}
    setClientesCargando(false);
  };

  const previsualizarFiltro = useCallback(async () => {
    if (!filtroTipo) { setFiltroPreview(null); return; }
    try {
      const body: any = { tipo: filtroTipo };
      if (FILTROS.find(f => f.tipo === filtroTipo)?.tieneValor && filtroValor) {
        const key = FILTROS.find(f => f.tipo === filtroTipo)?.valorLabel?.toLowerCase().includes("día") ? "dias" : "valor";
        body[key] = Number(filtroValor);
      }
      const r = await api.post("/campaigns/preview-filter", body);
      setFiltroPreview(r.data);
    } catch {
      setFiltroPreview(null);
    }
  }, [filtroTipo, filtroValor]);

  const abrirCrear = () => {
    setEditing(null);
    setNombre(""); setMensaje(""); setIntervalo("diario");
    setFechaInicio(""); setFechaFin(""); setHoraEnvio(""); setHoraFin(""); setRepetirCada(0);
    setAdjuntos([]); setSelected(new Set()); setClientes([]);
    setSearchCli(""); setCodigoDesde(""); setCodigoHasta("");
    setUsarFiltro(false); setFiltroTipo(""); setFiltroValor(""); setFiltroPreview(null);
    setShowForm(true);
    cargarClientes();
  };

  const abrirEditar = async (c: any) => {
    setEditing(c);
    setNombre(c.nombre); setMensaje(c.mensaje || ""); setIntervalo(c.intervalo);
    setFechaInicio(c.fecha_inicio?.split("T")[0] || c.fecha_inicio || "");
    setFechaFin(c.fecha_fin?.split("T")[0] || c.fecha_fin || "");
    setHoraEnvio(c.hora_envio || "");
    setHoraFin(c.hora_fin || "");
    setRepetirCada(c.repetir_cada || 0);
    try {
      const r = await api.get(`/campaigns/${c.id}`);
      const existentes = (r.data.adjuntos || []).map((a: any) => ({
        file: null, name: a.archivo_nombre, base64: a.archivo_base64, mimetype: a.archivo_mimetype || "application/octet-stream"
      }));
      setAdjuntos(existentes);
    } catch { setAdjuntos([]); }
    try { setSelected(new Set(JSON.parse(c.clientes_seleccionados || "[]"))); } catch { setSelected(new Set()); }
    try {
      const f = JSON.parse(c.filtro);
      if (f && f.tipo) {
        setUsarFiltro(true);
        setFiltroTipo(f.tipo);
        setFiltroValor(String(f.valor || f.dias || ""));
      }
    } catch {}
    setShowForm(true);
    cargarClientes();
  };

  const toggle = async (c: any) => {
    try { await api.put(`/campaigns/${c.id}/toggle`); cargar(); } catch {}
  };

  const eliminar = async (c: any) => {
    if (!confirm(`¿Eliminar campaña "${c.nombre}"?`)) return;
    try { await api.delete(`/campaigns/${c.id}`); cargar(); } catch {}
  };

  const verLog = async (c: any) => {
    setShowLog(c);
    try {
      const r = await api.get(`/campaigns/${c.id}/detail`);
      setLogData(r.data.log || []);
    } catch { setLogData([]); }
  };

  const insertarEmoji = (emoji: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    setMensaje(mensaje.substring(0, start) + emoji + mensaje.substring(end));
    setShowEmojis(false);
    setTimeout(() => {
      ta.selectionStart = ta.selectionEnd = start + emoji.length;
      ta.focus();
    }, 0);
  };

  const manejarAdjunto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || adjuntos.length >= 5) return;
    const base64 = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve((reader.result as string).split(",")[1] || "");
      reader.readAsDataURL(file);
    });
    setAdjuntos([...adjuntos, { file, name: file.name, base64, mimetype: file.type || "application/octet-stream" }]);
    e.target.value = "";
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

  const seleccionarTodosA2 = () => {
    setSelected(new Set(clientes.filter(c => !c._esContacto).map(c => c.FC_CODIGO)));
  };

  const seleccionarTodosAgenda = () => {
    setSelected(new Set(clientes.filter(c => c._esContacto).map(c => c.FC_CODIGO)));
  };

  const guardar = async () => {
    if (!nombre || !fechaInicio) return;
    if (!usarFiltro && selected.size === 0) return;
    setGuardando(true);
    let bodyFiltro = null;
    if (usarFiltro && filtroTipo) {
      bodyFiltro = { tipo: filtroTipo };
      const cfg = FILTROS.find(f => f.tipo === filtroTipo);
      if (cfg?.tieneValor && filtroValor) {
        const key = cfg.valorLabel?.toLowerCase().includes("día") ? "dias" : "valor";
        bodyFiltro[key] = Number(filtroValor);
      }
    }
    const body: any = {
      nombre, mensaje, intervalo, fecha_inicio: fechaInicio,
      fecha_fin: fechaFin, hora_envio: horaEnvio, hora_fin: horaFin, repetir_cada: repetirCada,
      clientes_seleccionados: usarFiltro ? [] : Array.from(selected),
      filtro: bodyFiltro,
      adjuntos: adjuntos.map(a => ({ archivo_nombre: a.name, archivo_base64: a.base64, archivo_mimetype: a.mimetype })),
    };
    try {
      if (editing) {
        await api.put(`/campaigns/${editing.id}`, body);
      } else {
        await api.post("/campaigns", body);
      }
      setShowForm(false);
      cargar();
    } catch (e: any) {
      alert(e.response?.data?.detail || "Error al guardar");
    }
    setGuardando(false);
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-800">{"Campañas"}</h2>
        <button className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-green-600 hover:to-green-700 shadow-sm flex items-center gap-1.5" onClick={abrirCrear}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
          {"Nueva campaña"}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {["todas", "activas", "finalizadas"].map((tab) => (
          <button key={tab} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${filtroEstado === tab ? "bg-white text-gray-800 shadow-sm" : "text-gray-500 hover:text-gray-700"}`} onClick={() => { setFiltroEstado(tab); setPagina(1); }}>
            {tab === "todas" ? "Todas" : tab === "activas" ? "Activas" : "Finalizadas"}
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-2 mb-4">
        <input className="border rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-400" placeholder="Buscar por nombre..." value={busqueda} onChange={e => setBusqueda(e.target.value)} />
        <input type="date" className="border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" value={desde} onChange={e => setDesde(e.target.value)} title="Desde" />
        <input type="date" className="border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" value={hasta} onChange={e => setHasta(e.target.value)} title="Hasta" />
        <select className="border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" value={segmento} onChange={e => setSegmento(e.target.value)}>
          <option value="">Todos los segmentos</option>
          <option value="manual">Selección manual</option>
          <option value="dinamico">Segmento dinámico</option>
        </select>
        {(busqueda || desde || hasta || segmento) && (
          <button className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 border rounded-lg" onClick={() => { setBusqueda(""); setDesde(""); setHasta(""); setSegmento(""); }}>
            Limpiar
          </button>
        )}
        <span className="text-xs text-gray-400 self-center ml-auto">{total} campaña{total !== 1 ? "s" : ""}</span>
      </div>

      {cargando ? (
        <p className="text-sm text-gray-400 text-center py-12">Cargando...</p>
      ) : campaigns.length === 0 ? (
        <div className="bg-white rounded-xl border shadow-md p-12 text-center">
          <p className="text-gray-400 mb-4">{"No hay campañas creadas"}</p>
          <button className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-green-600 hover:to-green-700 shadow-sm" onClick={abrirCrear}>
            {"Crear primera campaña"}
          </button>
        </div>
      ) : (
        <><div className="grid gap-4">
          {campaigns.map((c) => {
            let etiquetaDestinos = "";
            try { const f = JSON.parse(c.filtro); if (f?.tipo) etiquetaDestinos = "Segmento: " + (FILTROS.find(x => x.tipo === f.tipo)?.label || f.tipo); } catch {}
            if (!etiquetaDestinos) {
              const n = (() => { try { return JSON.parse(c.clientes_seleccionados || "[]").length; } catch { return 0; } })();
              etiquetaDestinos = `${n} cliente${n !== 1 ? "s" : ""}`;
            }
            return (
              <div key={c.id} className="bg-white rounded-xl border shadow-md p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-800">{c.nombre}</h3>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${c.activo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {c.activo ? "Activa" : "Pausada"}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${etiquetaDestinos.startsWith("Segmento") ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-400"}`}>{etiquetaDestinos}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className={`w-10 h-5 rounded-full transition-colors ${c.activo ? "bg-green-500" : "bg-gray-300"}`} onClick={() => toggle(c)}>
                      <div className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${c.activo ? "translate-x-5" : "translate-x-0.5"}`} />
                    </button>
                    <button className="text-gray-400 hover:text-blue-600 p-1" title="Editar" onClick={() => abrirEditar(c)}>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                    </button>
                    <button className="text-gray-400 hover:text-red-600 p-1" title="Eliminar" onClick={() => eliminar(c)}>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-6 gap-4 text-xs mb-3">
                  <div><span className="text-gray-400">Intervalo:</span> <span className="text-gray-700 font-medium">{INTERVALOS.find(i => i.key === c.intervalo)?.label || c.intervalo}</span></div>
                  <div><span className="text-gray-400">Inicio:</span> <span className="text-gray-700">{c.fecha_inicio}</span></div>
                  <div><span className="text-gray-400">Fin:</span> <span className="text-gray-700">{c.fecha_fin || "—"}</span></div>
                  <div><span className="text-gray-400">Hora:</span> <span className="text-gray-700">{c.hora_envio ? (c.hora_envio + (c.repetir_cada > 0 ? ` >${c.repetir_cada}h` + (c.hora_fin ? ` >${c.hora_fin}` : "") : "")) : "—"}</span></div>
                  <div><span className="text-gray-400">Ejecuciones:</span> <span className="text-gray-700 font-medium">{c.veces_ejecutada || 0}</span></div>
                  <div><span className="text-gray-400">{"Última:"}</span> <span className="text-gray-700">{c.ultima_ejecucion ? c.ultima_ejecucion.slice(0, 16).replace("T", " ") : "—"}</span></div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div className="bg-green-50 rounded-lg px-3 py-2">
                    <span className="text-green-700 font-semibold">{c.enviados_total || 0}</span>
                    <span className="text-green-600 ml-1">enviados</span>
                  </div>
                  <div className="bg-red-50 rounded-lg px-3 py-2">
                    <span className="text-red-700 font-semibold">{c.fallidos_total || 0}</span>
                    <span className="text-red-600 ml-1">fallidos</span>
                  </div>
                  <div className="bg-blue-50 rounded-lg px-3 py-2 cursor-pointer hover:bg-blue-100" onClick={() => verLog(c)}>
                    <span className="text-blue-700 font-semibold">{c.veces_ejecutada || 0}</span>
                    <span className="text-blue-600 ml-1">{"ejecuciones →"}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {paginas > 1 && (
          <div className="flex items-center justify-center gap-2 pt-4">
            <button className={`px-3 py-1 rounded-lg text-sm border ${pagina <= 1 ? "text-gray-300 border-gray-200 cursor-default" : "hover:bg-gray-100"}`} disabled={pagina <= 1} onClick={() => cargar(1)}>{"<<"}</button>
            <button className={`px-3 py-1 rounded-lg text-sm border ${pagina <= 1 ? "text-gray-300 border-gray-200 cursor-default" : "hover:bg-gray-100"}`} disabled={pagina <= 1} onClick={() => cargar(pagina - 1)}>{"<"}</button>
            <span className="text-sm text-gray-500 px-2">Pág. {pagina} de {paginas}</span>
            <button className={`px-3 py-1 rounded-lg text-sm border ${pagina >= paginas ? "text-gray-300 border-gray-200 cursor-default" : "hover:bg-gray-100"}`} disabled={pagina >= paginas} onClick={() => cargar(pagina + 1)}>{">"}</button>
            <button className={`px-3 py-1 rounded-lg text-sm border ${pagina >= paginas ? "text-gray-300 border-gray-200 cursor-default" : "hover:bg-gray-100"}`} disabled={pagina >= paginas} onClick={() => cargar(paginas)}>{">>"}</button>
          </div>
        )}
      </>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowForm(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-[900px] max-w-[95vw] mx-4 max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">{editing ? "Editar" : "Nueva"} {"campaña"}</h3>
              <button className="text-gray-400 hover:text-gray-600 p-1" onClick={() => setShowForm(false)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {/* Configuracion general */}
              <div className="mb-5">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">{"Configuración general"}</h4>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-3">
                    <label className="block text-xs font-medium text-gray-600 mb-1">Nombre</label>
                    <input className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={nombre} onChange={e => setNombre(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Fecha inicio</label>
                    <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={fechaInicio} onChange={e => setFechaInicio(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{"Fecha fin (opcional)"}</label>
                    <input type="date" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={fechaFin} onChange={e => setFechaFin(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Intervalo</label>
                    <div className="flex gap-1.5">
                      {INTERVALOS.map(i => (
                        <button key={i.key} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${intervalo === i.key ? "bg-green-500 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`} onClick={() => setIntervalo(i.key)}>{i.label}</button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Programacion horaria */}
              <div className="mb-5">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">{"Programación horaria"}</h4>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">{"Hora de envío"}</label>
                    <input type="time" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={horaEnvio} onChange={e => setHoraEnvio(e.target.value)} />
                  </div>
                  {horaEnvio && (
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{"Repetir cada"}</label>
                      <div className="flex gap-1.5">
                        {[0,1,2,3,4,5].map(n => (
                          <button key={n} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${repetirCada === n ? "bg-green-500 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`} onClick={() => setRepetirCada(n)}>
                            {n === 0 ? "No" : `${n}h`}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {horaEnvio && repetirCada > 0 && (
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">{"Hasta las"}</label>
                      <input type="time" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={horaFin} onChange={e => setHoraFin(e.target.value)} />
                    </div>
                  )}
                  {horaEnvio && repetirCada > 0 && (() => {
                    try {
                      const [hh, mm] = horaEnvio.split(":").map(Number);
                      const fin = horaFin ? horaFin.split(":").map(Number) : null;
                      let total = hh * 60 + mm;
                      const tope = fin ? fin[0] * 60 + fin[1] : 24 * 60;
                      if (total >= tope) return null;
                      const seq = [];
                      while (total < tope) {
                        seq.push(`${String(total / 60 | 0).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`);
                        total += repetirCada * 60;
                      }
                      return (
                        <div className="col-span-3 bg-gradient-to-r from-blue-50 to-blue-100/80 rounded-lg px-4 py-3 text-xs border border-blue-200">
                          <span className="text-blue-600 font-medium">{"Secuencia de envíos: "}</span>
                          <span className="text-blue-800 font-semibold">{seq.join(" → ")}</span>
                          <span className="inline-flex items-center ml-3 px-2 py-0.5 bg-blue-200 text-blue-800 rounded-full">({seq.length} {"envío"}{seq.length !== 1 ? "s" : ""})</span>
                        </div>
                      );
                    } catch { return null; }
                  })()}
                </div>
              </div>

              {/* Mensaje */}
              <div className="mb-5">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Mensaje</h4>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-gray-600">{"Contenido del mensaje"}</label>
                  <button className="text-xs text-gray-400 hover:text-gray-600" onClick={() => setShowEmojis(!showEmojis)}>{"\uD83D\uDE0A Emojis"}</button>
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  <button className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                    const ta = textareaRef.current; if (!ta) return;
                    const s = ta.selectionStart, e = ta.selectionEnd;
                    setMensaje(prev => prev.substring(0, s) + "{empresa_razon_social}" + prev.substring(e));
                    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 22; ta.focus(); }, 0);
                  }}>{`{empresa_razon_social}`}</button>
                  <button className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                    const ta = textareaRef.current; if (!ta) return;
                    const s = ta.selectionStart, e = ta.selectionEnd;
                    setMensaje(prev => prev.substring(0, s) + "{empresa_rif}" + prev.substring(e));
                    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
                  }}>{`{empresa_rif}`}</button>
                  <span className="text-[10px] text-gray-400 self-center">Cliente:</span>
                  <button className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                    const ta = textareaRef.current; if (!ta) return;
                    const s = ta.selectionStart, e = ta.selectionEnd;
                    setMensaje(prev => prev.substring(0, s) + "{FC_DESCRIPCION}" + prev.substring(e));
                    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 17; ta.focus(); }, 0);
                  }}>{`{FC_DESCRIPCION}`}</button>
                  <button className="text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                    const ta = textareaRef.current; if (!ta) return;
                    const s = ta.selectionStart, e = ta.selectionEnd;
                    setMensaje(prev => prev.substring(0, s) + "{FC_TELEFONO}" + prev.substring(e));
                    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
                  }}>{`{FC_TELEFONO}`}</button>
                  {usarFiltro && <>
                    <span className="text-[10px] text-gray-400 self-center">Segmento:</span>
                    <button className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                      const ta = textareaRef.current; if (!ta) return;
                      const s = ta.selectionStart, e = ta.selectionEnd;
                      setMensaje(prev => prev.substring(0, s) + "{FC_SALDO_TOTAL}" + prev.substring(e));
                      setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
                    }}>{`{FC_SALDO_TOTAL}`}</button>
                    <button className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                      const ta = textareaRef.current; if (!ta) return;
                      const s = ta.selectionStart, e = ta.selectionEnd;
                      setMensaje(prev => prev.substring(0, s) + "{FC_DOCUMENTOS}" + prev.substring(e));
                      setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
                    }}>{`{FC_DOCUMENTOS}`}</button>
                    <button className="text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 border border-orange-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                      const ta = textareaRef.current; if (!ta) return;
                      const s = ta.selectionStart, e = ta.selectionEnd;
                      setMensaje(prev => prev.substring(0, s) + "{FC_CRITERIO}" + prev.substring(e));
                      setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
                    }}>{`{FC_CRITERIO}`}</button>
                  </>}
                  <span className="text-[10px] text-gray-400 self-center">Tasas:</span>
                  <button className="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-md px-2 py-1 font-medium" onClick={() => { const ta = textareaRef.current; if (!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; setMensaje(prev => prev.substring(0, s) + "{bcv_usd}" + prev.substring(e)); setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 9; ta.focus(); }, 0); }}>{`{bcv_usd}`}</button>
                  <button className="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-md px-2 py-1 font-medium" onClick={() => { const ta = textareaRef.current; if (!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; setMensaje(prev => prev.substring(0, s) + "{bcv_eur}" + prev.substring(e)); setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 9; ta.focus(); }, 0); }}>{`{bcv_eur}`}</button>
                  <button className="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-md px-2 py-1 font-medium" onClick={() => { const ta = textareaRef.current; if (!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; setMensaje(prev => prev.substring(0, s) + "{usdt_avg}" + prev.substring(e)); setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 10; ta.focus(); }, 0); }}>{`{usdt_avg}`}</button>
                  <button className="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-md px-2 py-1 font-medium" onClick={() => { const ta = textareaRef.current; if (!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; setMensaje(prev => prev.substring(0, s) + "{brecha}" + prev.substring(e)); setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 8; ta.focus(); }, 0); }}>{`{brecha}`}</button>
                  <button className="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-md px-2 py-1 font-medium" onClick={() => { const ta = textareaRef.current; if (!ta) return; const s = ta.selectionStart, e = ta.selectionEnd; setMensaje(prev => prev.substring(0, s) + "{brecha_pct}" + prev.substring(e)); setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 12; ta.focus(); }, 0); }}>{`{brecha_pct}`}</button>
                </div>
                {showEmojis && (
                  <div className="flex flex-wrap gap-1 mb-2 p-2 bg-gray-50 rounded-lg max-h-24 overflow-y-auto">
                    {EMOJIS.map(e => (
                      <button key={e} className="text-lg hover:bg-gray-200 rounded p-0.5" onClick={() => insertarEmoji(e)}>{e}</button>
                    ))}
                  </div>
                )}
                <textarea ref={textareaRef} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 min-h-[100px]" value={mensaje} onChange={e => setMensaje(e.target.value)} />
                <div className="flex items-center gap-2 mt-2">
                  <button className="border border-gray-300 text-gray-600 px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50 flex items-center gap-1" onClick={async () => {
                    try {
                      const r = await api.post("/preview", { tipo: "cobranza", template: mensaje, criterio: "todas", dias: 0 });
                      setPreviewMsg(r.data.vista);
                    } catch (e: any) {
                      setPreviewMsg("Error: " + (e.response?.data?.detail || e.message));
                    }
                  }}>
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                    Vista previa
                  </button>
                  {previewMsg && (
                    <span className="text-xs text-green-600 cursor-pointer hover:text-green-800" onClick={() => setPreviewMsg(null)}>Cerrar preview</span>
                  )}
                </div>
                {previewMsg && (
                  <div className="mt-2 border rounded-lg p-3 bg-gray-50 max-h-40 overflow-y-auto">
                    <pre className="text-sm font-mono whitespace-pre-wrap">{previewMsg}</pre>
                  </div>
                )}
              </div>

              {/* Adjuntos */}
              <div className="mb-5">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">{"Adjuntos (máx 5)"}</h4>
                <div className="flex flex-wrap gap-2 mb-2">
                  {adjuntos.map((a, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 bg-gray-100 rounded-lg px-3 py-1.5 text-xs border">
                      <span className="text-base">{"\uD83D\uDCCE"}</span>
                      <span className="text-gray-700">{a.name}</span>
                      <button className="text-red-400 hover:text-red-600 ml-1" onClick={() => setAdjuntos(adjuntos.filter((_, j) => j !== i))}>{"\u2715"}</button>
                    </span>
                  ))}
                </div>
                {adjuntos.length < 5 && (
                  <label className="block border-2 border-dashed rounded-lg px-4 py-3 text-sm hover:bg-gray-50 cursor-pointer text-center text-gray-400 hover:text-gray-600 transition-colors">
                    <span className="font-medium">{"+ Agregar archivo"}</span>
                    <input type="file" className="hidden" onChange={manejarAdjunto} />
                  </label>
                )}
              </div>

              {/* Destinatarios */}
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  {"Destinatarios "}
                  {usarFiltro && filtroPreview ? <span className="text-green-600 font-bold">(≈ {filtroPreview.total} clientes)</span> : <span className="text-gray-400">({selected.size} seleccionados)</span>}
                </h4>
                <div className="flex gap-2 mb-3">
                  <button className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${!usarFiltro ? "bg-green-500 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`} onClick={() => setUsarFiltro(false)}>Selección manual</button>
                  <button className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${usarFiltro ? "bg-green-500 text-white shadow-sm" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`} onClick={() => setUsarFiltro(true)}>Segmento dinámico</button>
                </div>

                {usarFiltro ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Condición</label>
                        <select className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={filtroTipo} onChange={e => { setFiltroTipo(e.target.value); setFiltroPreview(null); }}>
                          <option value="">Seleccionar...</option>
                          {FILTROS.map(f => (
                            <option key={f.tipo} value={f.tipo}>{f.label}</option>
                          ))}
                        </select>
                        {filtroTipo && <p className="text-xs text-gray-400 mt-1">{FILTROS.find(f => f.tipo === filtroTipo)?.desc}</p>}
                      </div>
                      {filtroTipo && FILTROS.find(f => f.tipo === filtroTipo)?.tieneValor && (
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">{FILTROS.find(f => f.tipo === filtroTipo)?.valorLabel}</label>
                          <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" placeholder={String(FILTROS.find(f => f.tipo === filtroTipo)?.valorDefault ?? "")} value={filtroValor} onChange={e => setFiltroValor(e.target.value)} />
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="px-3 py-1.5 bg-blue-500 text-white rounded-lg text-xs font-medium hover:bg-blue-600 shadow-sm" onClick={previsualizarFiltro} disabled={!filtroTipo}>Previsualizar</button>
                      {filtroPreview && (
                        <span className="text-xs text-gray-500">
                          ≈ {filtroPreview.total} cliente{filtroPreview.total !== 1 ? "s" : ""} cumplen esta condición
                        </span>
                      )}
                    </div>
                    {filtroPreview && filtroPreview.clientes.length > 0 && (
                      <div className="border rounded-lg overflow-hidden max-h-36 overflow-y-auto">
                        <div className="divide-y divide-gray-100">
                          {filtroPreview.clientes.map((c: any, i: number) => (
                            <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-xs">
                              <span className="flex-1 truncate text-gray-700">{c.FC_DESCRIPCION || c.FC_CODIGO}</span>
                              <span className="w-20 truncate text-gray-400">{c.FC_TELEFONO}</span>
                              <span className="w-20 text-right text-red-600 font-medium">{Number(c.FC_SALDO_TOTAL || 0).toFixed(2)}</span>
                              <span className="w-10 text-right text-gray-500">{c.FC_DOCUMENTOS || 0} docs</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="flex gap-1.5 mb-2">
                      <input className="flex-1 border rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Buscar..." value={searchCli} onChange={e => setSearchCli(e.target.value)} onKeyDown={e => { if (e.key === "Enter") cargarClientes(); }} />
                      <button className="px-3 py-1.5 bg-blue-500 text-white rounded-lg text-xs font-medium hover:bg-blue-600 shadow-sm" onClick={cargarClientes} disabled={clientesCargando}>Buscar</button>
                    </div>
                    <div className="flex gap-1.5 mb-2">
                      <input className="w-24 border rounded-lg px-2 py-1.5 text-xs" placeholder={"Cód. desde"} value={codigoDesde} onChange={e => setCodigoDesde(e.target.value)} />
                      <input className="w-24 border rounded-lg px-2 py-1.5 text-xs" placeholder={"Cód. hasta"} value={codigoHasta} onChange={e => setCodigoHasta(e.target.value)} />
                      <button className="px-3 py-1.5 bg-blue-500 text-white rounded-lg text-xs font-medium hover:bg-blue-600 shadow-sm" onClick={cargarClientes} disabled={clientesCargando}>Filtrar</button>
                      <button className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-200" onClick={() => { setSearchCli(""); setCodigoDesde(""); setCodigoHasta(""); cargarClientes(); }}>Limpiar</button>
                    </div>
                    <div className="border rounded-lg overflow-hidden shadow-sm">
                      <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-3 py-2 flex items-center gap-2 border-b text-xs font-semibold text-gray-600">
                        <input type="checkbox" checked={selected.size === clientes.length && clientes.length > 0} onChange={toggleTodos} className="rounded" />
                        <span className="flex-1">Cliente</span>
                        <span className="w-24">{"Teléfono"}</span>
                        <span className="w-16 text-right text-green-600">{selected.size > 0 ? `✓ ${selected.size}` : ""}</span>
                        <div className="flex gap-1 ml-1">
                          <button className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700 hover:bg-blue-200" onClick={seleccionarTodosA2}>A2</button>
                          <button className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-700 hover:bg-purple-200" onClick={seleccionarTodosAgenda}>Agenda</button>
                        </div>
                      </div>
                      <div className="max-h-52 overflow-y-auto divide-y divide-gray-100">
                        {clientesCargando ? (
                          <p className="text-xs text-gray-400 text-center py-4">Cargando...</p>
                        ) : clientes.length === 0 ? (
                          <p className="text-xs text-gray-400 text-center py-4">Sin resultados</p>
                        ) : (
                          clientes.map((c) => (
                            <div key={c.FC_CODIGO} className={`flex items-center gap-2 px-3 py-2 text-xs transition-colors hover:bg-green-50/60 cursor-pointer ${selected.has(c.FC_CODIGO) ? "bg-green-50" : ""}`} onClick={() => toggleCliente(c.FC_CODIGO)}>
                              <input type="checkbox" checked={selected.has(c.FC_CODIGO)} onChange={() => {}} className="rounded" />
                              {c._esContacto
                                ? <span className="px-1.5 py-0.5 text-[10px] font-medium bg-purple-100 text-purple-700 rounded">Agenda</span>
                                : <span className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-100 text-blue-700 rounded">A2</span>}
                              <span className="flex-1 truncate text-gray-700">{c.FC_DESCRIPCION || c.FC_CODIGO}</span>
                              <span className="w-24 truncate text-gray-400">{c.FC_TELEFONO || <span className="text-red-400 font-medium">SIN TELÉFONO</span>}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
            <div className="p-4 border-t flex justify-end gap-2">
              <button className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" onClick={() => setShowForm(false)}>Cancelar</button>
              <button className="px-4 py-2 text-sm bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 shadow-sm disabled:opacity-50" onClick={guardar} disabled={guardando || !nombre || !fechaInicio || (!usarFiltro && selected.size === 0) || (usarFiltro && !filtroTipo)}>
                {guardando ? "Guardando..." : editing ? "Actualizar" : "Crear campaña"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowLog(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">{"Detalle: "}{showLog.nombre}</h3>
              <button className="text-gray-400 hover:text-gray-600 p-1" onClick={() => setShowLog(null)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {/* Resumen de la campaña */}
              <div className="grid grid-cols-6 gap-3 text-xs mb-4 p-3 bg-gray-50 rounded-lg border">
                <div><span className="text-gray-400">Intervalo:</span> <span className="text-gray-700 font-medium">{INTERVALOS.find(i => i.key === showLog.intervalo)?.label || showLog.intervalo}</span></div>
                <div><span className="text-gray-400">Inicio:</span> <span className="text-gray-700">{showLog.fecha_inicio}</span></div>
                <div><span className="text-gray-400">Fin:</span> <span className="text-gray-700">{showLog.fecha_fin || "—"}</span></div>
                <div><span className="text-gray-400">Hora:</span> <span className="text-gray-700">{showLog.hora_envio || "—"}{showLog.hora_fin ? ` — ${showLog.hora_fin}` : ""}</span></div>
                <div><span className="text-gray-400">Repetición:</span> <span className="text-gray-700">{showLog.repetir_cada > 0 ? `Cada ${showLog.repetir_cada}h` : "No"}</span></div>
                <div><span className="text-gray-400">Próxima:</span> <span className={`font-medium ${calcularProximaEjecucion(showLog)?.includes("Finalizada") ? "text-red-500" : "text-green-600"}`}>{calcularProximaEjecucion(showLog) || "—"}</span></div>
              </div>
              <div className="flex gap-3 mb-4 text-xs">
                <div className="bg-green-50 rounded-lg px-3 py-2 flex-1 text-center">
                  <span className="text-green-700 font-semibold">{showLog.enviados_total || 0}</span>
                  <span className="text-green-600 ml-1">enviados</span>
                </div>
                <div className="bg-red-50 rounded-lg px-3 py-2 flex-1 text-center">
                  <span className="text-red-700 font-semibold">{showLog.fallidos_total || 0}</span>
                  <span className="text-red-600 ml-1">fallidos</span>
                </div>
                <div className="bg-blue-50 rounded-lg px-3 py-2 flex-1 text-center">
                  <span className="text-blue-700 font-semibold">{showLog.veces_ejecutada || 0}</span>
                  <span className="text-blue-600 ml-1">ejecuciones</span>
                </div>
              </div>
              {logData.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">Sin ejecuciones</p>
              ) : (
                <div className="space-y-3">
                  {logData.map((l, i) => (
                    <div key={i} className="border rounded-lg p-3">
                      <div className="flex gap-4 text-xs mb-2 pb-2 border-b border-gray-100">
                        <span className="text-gray-400 font-semibold">#{l.ejecucion_numero}</span>
                        <span className="text-gray-600">{l.ejecutado_en?.slice(0, 16).replace("T", " ") || "-"}</span>
                        <span className="text-green-700 font-medium">{l.enviados} ✓ enviados</span>
                        <span className="text-red-700 font-medium">{l.fallidos} ✗ fallidos</span>
                        <span className="text-blue-600 font-medium">{l.total_destinos || 0} total</span>
                      </div>
                      {l.detalles && (() => {
                        try {
                          const det = JSON.parse(l.detalles);
                          if (!det.length) return null;
                          return (
                            <div className="max-h-48 overflow-y-auto text-xs divide-y divide-gray-100">
                              {det.map((d: string, j: number) => {
                                const ok = d.startsWith("✓");
                                const texto = d.replace(/^[✓✗]\s*/, "");
                                const [nombre, ...resto] = texto.split(" - ");
                                return (
                                  <div key={j} className={`px-2 py-1.5 flex items-center gap-2 ${ok ? "text-green-700" : "text-red-600"}`}>
                                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-bold ${ok ? "bg-green-500" : "bg-red-500"}`}>{ok ? "✓" : "✗"}</span>
                                    <span className="font-medium text-gray-800">{nombre}</span>
                                    {resto.length > 0 && <span className="text-gray-500">{resto.join(" - ")}</span>}
                                  </div>
                                );
                              })}
                            </div>
                          );
                        } catch { return null; }
                      })()}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="p-4 border-t flex justify-end">
              <button className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" onClick={() => setShowLog(null)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
