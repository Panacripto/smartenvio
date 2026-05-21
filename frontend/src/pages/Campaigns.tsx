import { useEffect, useState, useRef } from "react";
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

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [cargando, setCargando] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [showLog, setShowLog] = useState<any>(null);
  const [logData, setLogData] = useState<any[]>([]);
  const [showEmojis, setShowEmojis] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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

  const cargar = async () => {
    setCargando(true);
    try {
      const r = await api.get("/campaigns");
      setCampaigns(r.data);
    } catch {}
    setCargando(false);
  };

  useEffect(() => { cargar(); const iv = setInterval(cargar, 10000); return () => clearInterval(iv); }, []);

  const cargarClientes = async () => {
    setClientesCargando(true);
    try {
      const params: Record<string, any> = { solo_con_telefono: true };
      if (searchCli) params.search = searchCli;
      if (codigoDesde) params.codigo_desde = codigoDesde;
      if (codigoHasta) params.codigo_hasta = codigoHasta;
      const r = await api.get("/clientes", { params });
      setClientes(r.data);
    } catch {}
    setClientesCargando(false);
  };

  const abrirCrear = () => {
    setEditing(null);
    setNombre(""); setMensaje(""); setIntervalo("diario");
    setFechaInicio(""); setFechaFin(""); setHoraEnvio(""); setHoraFin(""); setRepetirCada(0);
    setAdjuntos([]); setSelected(new Set()); setClientes([]);
    setSearchCli(""); setCodigoDesde(""); setCodigoHasta("");
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
      const r = await api.get(`/campaigns/${c.id}`);
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

  const guardar = async () => {
    if (!nombre || !fechaInicio || selected.size === 0) return;
    setGuardando(true);
    const body: any = {
      nombre, mensaje, intervalo, fecha_inicio: fechaInicio,
      fecha_fin: fechaFin, hora_envio: horaEnvio, hora_fin: horaFin, repetir_cada: repetirCada,
      clientes_seleccionados: Array.from(selected),
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
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">{"Campañas"}</h2>
        <button className="bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:from-green-600 hover:to-green-700 shadow-sm flex items-center gap-1.5" onClick={abrirCrear}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
          {"Nueva campaña"}
        </button>
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
        <div className="grid gap-4">
          {campaigns.map((c) => {
            const nClientes = (() => { try { return JSON.parse(c.clientes_seleccionados || "[]").length; } catch { return 0; } })();
            return (
              <div key={c.id} className="bg-white rounded-xl border shadow-md p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-800">{c.nombre}</h3>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${c.activo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {c.activo ? "Activa" : "Pausada"}
                    </span>
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{nClientes} cliente{nClientes !== 1 ? "s" : ""}</span>
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
                </div>
                {showEmojis && (
                  <div className="flex flex-wrap gap-1 mb-2 p-2 bg-gray-50 rounded-lg max-h-24 overflow-y-auto">
                    {EMOJIS.map(e => (
                      <button key={e} className="text-lg hover:bg-gray-200 rounded p-0.5" onClick={() => insertarEmoji(e)}>{e}</button>
                    ))}
                  </div>
                )}
                <textarea ref={textareaRef} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 min-h-[100px]" value={mensaje} onChange={e => setMensaje(e.target.value)} />
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

              {/* Clientes */}
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  {"Clientes ("}{selected.size}{")"}
                </h4>
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
                          <span className="flex-1 truncate text-gray-700">{c.FC_DESCRIPCION || c.FC_CODIGO}</span>
                          <span className="w-24 truncate text-gray-400">{c.FC_TELEFONO || "-"}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
            <div className="p-4 border-t flex justify-end gap-2">
              <button className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" onClick={() => setShowForm(false)}>Cancelar</button>
              <button className="px-4 py-2 text-sm bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 shadow-sm disabled:opacity-50" onClick={guardar} disabled={guardando || !nombre || !fechaInicio || selected.size === 0}>
                {guardando ? "Guardando..." : editing ? "Actualizar" : "Crear campaña"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowLog(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">{"Historial: "}{showLog.nombre}</h3>
              <button className="text-gray-400 hover:text-gray-600 p-1" onClick={() => setShowLog(null)}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {logData.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Sin ejecuciones</p>
              ) : (
                <div className="space-y-3">
                  {logData.map((l, i) => (
                    <div key={i} className="border rounded-lg p-3">
                      <div className="flex gap-4 text-xs mb-2">
                        <span className="text-gray-400">#{l.ejecucion_numero}</span>
                        <span className="text-gray-600">{l.ejecutado_en?.slice(0, 16).replace("T", " ") || "-"}</span>
                        <span className="text-green-700 font-medium">{l.enviados} enviados</span>
                        <span className="text-red-700 font-medium">{l.fallidos} fallidos</span>
                      </div>
                      {l.detalles && (() => {
                        try {
                          const det = JSON.parse(l.detalles);
                          return (
                            <div className="max-h-32 overflow-y-auto text-xs space-y-0.5">
                              {det.map((d: string, j: number) => (
                                <div key={j} className={d.startsWith("✓") ? "text-green-600" : "text-red-600"}>{d}</div>
                              ))}
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
