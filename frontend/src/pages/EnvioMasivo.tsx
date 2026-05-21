import { useEffect, useState, useRef } from "react";
import api from "@/api/client";

const CAMPOS = [
  { key: "FC_CODIGO", label: "Código" },
  { key: "FC_DESCRIPCION", label: "Nombre" },
  { key: "FC_TELEFONO", label: "Teléfono" },
  { key: "FC_EMAIL", label: "Email" },
  { key: "FC_DIRECCION1", label: "Dirección" },
  { key: "FC_LIMITECREDITO", label: "Límite Crédito" },
  { key: "FC_SALDO", label: "Saldo" },
];

const EMOJIS = [
  "😀","😁","😂","🤣","😊","😎","👍","👎","🙌","👏","🎉","🎊",
  "❤️","💯","✅","❌","⭐","🔥","💪","🤝","👋","📢","📌","🎯",
  "💰","📈","📊","🏆","🛒","🚚","📦","🎁","🔔","📞","✉️","📱",
  "☀️","🌧️","⏰","📅","🔴","🟢","🟡","🔵","🟣","⚪","🟠","🟤",
];

export default function EnvioMasivo() {
  const [mensaje, setMensaje] = useState("");
  const [clientes, setClientes] = useState<any[]>([]);
  const [telefonoManual, setTelefonoManual] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [archivoNombre, setArchivoNombre] = useState("");
  const archivoFileRef = useRef<File | null>(null);
  const [search, setSearch] = useState("");
  const [codigoDesde, setCodigoDesde] = useState("");
  const [codigoHasta, setCodigoHasta] = useState("");
  const [soloConTelefono, setSoloConTelefono] = useState(true);
  const [cargando, setCargando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState("");
  const [resultadosDetalle, setResultadosDetalle] = useState<string[]>([]);
  const [whatsappStatus, setWhatsappStatus] = useState("disconnected");
  const [showEmojis, setShowEmojis] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.get("/whatsapp/status").then(r => setWhatsappStatus(r.data.status)).catch(() => {});
    cargarClientes();
  }, []);

  const cargarClientes = async () => {
    setCargando(true);
    try {
      const params: Record<string, any> = { solo_con_telefono: true };
      if (search) params.search = search;
      if (codigoDesde) params.codigo_desde = codigoDesde;
      if (codigoHasta) params.codigo_hasta = codigoHasta;
      const r = await api.get("/clientes", { params });
      setClientes(r.data);
      setSelected(new Set());
    } catch (e: any) {
      console.error("Error cargando clientes:", e);
    }
    setCargando(false);
  };

  const insertarCampo = (campo: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const txt = mensaje;
    const nuevo = txt.substring(0, start) + `{${campo}}` + txt.substring(end);
    setMensaje(nuevo);
    setTimeout(() => {
      ta.selectionStart = ta.selectionEnd = start + campo.length + 2;
      ta.focus();
    }, 0);
  };

  const insertarEmoji = (emoji: string) => {
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const nuevo = mensaje.substring(0, start) + emoji + mensaje.substring(end);
    setMensaje(nuevo);
    setShowEmojis(false);
    setTimeout(() => {
      ta.selectionStart = ta.selectionEnd = start + emoji.length;
      ta.focus();
    }, 0);
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

  const reemplazarVariables = (texto: string, cliente: any) => {
    let t = texto;
    for (const campo of CAMPOS) {
      t = t.replace(new RegExp(`\\{${campo.key}\\}`, "g"), cliente[campo.key] ?? "");
    }
    return t;
  };

  const enviar = async () => {
    if (!mensaje) return;
    setEnviando(true);
    setResultado("");
    setResultadosDetalle([]);
    const detalle: string[] = [];
    let enviados = 0;
    let fallidos = 0;

    // Leer archivo (si hay)
    let archivoBase64: string | null = null;
    let archivoNombre = "";
    let archivoMimetype = "";
    if (archivoFileRef.current) {
      try {
        const file = archivoFileRef.current;
        archivoNombre = file.name;
        archivoMimetype = file.type || "application/octet-stream";
        archivoBase64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const data = reader.result as string;
            resolve(data.split(",")[1] || data);
          };
          reader.onerror = () => reject("Error al leer archivo");
          reader.readAsDataURL(file);
        });
      } catch (e) {
        detalle.push(`✗ Error al leer archivo: ${e}`);
        fallidos++;
      }
    }

    const enviarA = async (tel: string, msgTexto: string) => {
      const body: Record<string, any> = { telefono: tel, mensaje: msgTexto };
      if (archivoBase64) {
        body.archivo_nombre = archivoNombre;
        body.archivo_base64 = archivoBase64;
        body.archivo_mimetype = archivoMimetype;
      }
      await api.post("/whatsapp/send", body);
    };

  const manuales = telefonoManual.split(/[\n,]+/).map(t => t.replace(/\D/g, "")).filter(t => t.length >= 10);
  for (const destino of manuales) {
    const clienteManual = clientes.find(c => String(c.FC_TELEFONO || "").replace(/\D/g, "") === destino);
    const msgFinal = clienteManual ? reemplazarVariables(mensaje, clienteManual) : mensaje;
    try {
      await enviarA(destino, msgFinal);
      enviados++;
      detalle.push(`✓ ${clienteManual?.FC_DESCRIPCION || destino}`);
    } catch (e: any) {
      fallidos++;
      detalle.push(`✗ ${clienteManual?.FC_DESCRIPCION || destino}: ${e.response?.data?.detail || e.message || "Error"}`);
    }
  }

    for (const cod of selected) {
      const cliente = clientes.find(c => c.FC_CODIGO === cod);
      if (!cliente) continue;
      const tel = String(cliente.FC_TELEFONO || "").replace(/\D/g, "");
      if (!tel) { fallidos++; detalle.push(`✗ ${cod} - sin teléfono`); continue; }
      const msg = reemplazarVariables(mensaje, cliente);
      try {
        await enviarA(tel, msg);
        enviados++;
        detalle.push(`✓ ${cliente.FC_DESCRIPCION}`);
      } catch (e: any) {
        fallidos++;
        detalle.push(`✗ ${cliente.FC_DESCRIPCION}: ${e.response?.data?.detail || e.message || "Error"}`);
      }
    }

    setResultado(`✓ ${enviados} enviados | ✗ ${fallidos} fallidos`);
    setResultadosDetalle(detalle);
    setEnviando(false);
  };

  const totalSeleccionados = selected.size + telefonoManual.split(/[\n,]+/).map(t => t.replace(/\D/g, "")).filter(t => t.length >= 10).length;

  return (
    <div className="h-full overflow-y-auto p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Envío Masivo</h2>

      <div className="flex gap-6">
        {/* Columna izquierda: mensaje + archivo + teléfono */}
        <div className="w-[420px] shrink-0 space-y-4">
          <div className="bg-white rounded-xl border shadow-md p-5">
            <h3 className="font-semibold text-gray-800 mb-3">Mensaje</h3>
            <textarea
              ref={textareaRef}
              className="w-full border rounded-lg px-3 py-2.5 text-sm min-h-[130px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
              placeholder="Escribe tu mensaje... usa {FC_DESCRIPCION} para el nombre, {FC_CODIGO} para el código, etc."
              value={mensaje}
              onChange={e => setMensaje(e.target.value)}
            />
            <div className="mt-2">
              <p className="text-xs text-gray-500 mb-1.5">Insertar campo:</p>
              <div className="flex flex-wrap gap-1.5">
                {CAMPOS.map(c => (
                  <button
                    key={c.key}
                    className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium transition-colors"
                    onClick={() => insertarCampo(c.key)}
                  >
                    {`{${c.label}}`}
                  </button>
                ))}
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
                    <button
                      key={e}
                      className="text-lg hover:bg-gray-100 rounded p-0.5 transition-colors"
                      onClick={() => insertarEmoji(e)}
                    >
                      {e}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl border shadow-md p-5">
            <div className="flex gap-4">
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 mb-2 text-sm">Adjuntar archivo</h3>
                <input type="file" id="file-input" className="hidden" onChange={e => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  archivoFileRef.current = file;
                  setArchivoNombre(file.name);
                }} />
                <label htmlFor="file-input" className="block border rounded-lg px-3 py-2 text-sm hover:bg-gray-50 cursor-pointer text-center">
                  {archivoNombre ? `📎 ${archivoNombre}` : "Seleccionar archivo..."}
                </label>
                {archivoNombre && (
                  <button className="mt-1.5 text-xs text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-md px-2 py-1 transition-colors flex items-center gap-1" onClick={() => { archivoFileRef.current = null; setArchivoNombre(""); }}>
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    Quitar archivo
                  </button>
                )}
              </div>
              <div className="flex-1">
            <h3 className="font-semibold text-gray-800 mb-2 text-sm">Teléfono manual</h3>
            <textarea placeholder={"Un numero por linea o separados por coma\n584146762870\n584141234567"} className="w-full border rounded-lg px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none" value={telefonoManual} onChange={e => setTelefonoManual(e.target.value)} />
              </div>
            </div>
          </div>
        </div>

        {/* Columna derecha: clientes */}
        <div className="flex-1 bg-white rounded-xl border shadow-md p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Clientes a2</h3>

          <div className="grid grid-cols-4 gap-2 mb-3">
            <input
              type="text"
              placeholder="Buscar..."
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") cargarClientes(); }}
            />
            <input
              type="text"
              placeholder="Código desde"
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              value={codigoDesde}
              onChange={e => setCodigoDesde(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") cargarClientes(); }}
            />
            <input
              type="text"
              placeholder="Código hasta"
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              value={codigoHasta}
              onChange={e => setCodigoHasta(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") cargarClientes(); }}
            />
            <button
              className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg text-sm font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center justify-center gap-1.5 px-4 py-2"
              onClick={cargarClientes}
              disabled={cargando}
            >
              {cargando ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              )}
              {cargando ? "Cargando..." : "Cargar"}
            </button>
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-600 mb-3">
            <input type="checkbox" checked={soloConTelefono} onChange={e => setSoloConTelefono(e.target.checked)} />
            Solo clientes con teléfono
          </label>

          <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 px-4 py-3 flex items-center gap-3 text-xs font-semibold text-gray-600 uppercase tracking-wider">
              <input type="checkbox" checked={clientes.length > 0 && selected.size === clientes.length} onChange={toggleTodos} className="rounded border-gray-300" />
              <span>{selected.size} de {clientes.length} seleccionados</span>
            </div>
            <div className="max-h-[350px] overflow-y-auto divide-y divide-gray-100">
              {clientes.map((c, i) => (
                <label key={c.FC_CODIGO} className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer text-sm transition-colors hover:bg-green-50/60 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}>
                  <input type="checkbox" checked={selected.has(c.FC_CODIGO)} onChange={() => toggleCliente(c.FC_CODIGO)} className="rounded border-gray-300" />
                  <span className="font-mono text-xs font-medium text-gray-700 w-16">{c.FC_CODIGO}</span>
                  <span className="flex-1 truncate text-gray-700">{c.FC_DESCRIPCION}</span>
                  <span className="text-xs text-gray-400">{c.FC_TELEFONO || "-"}</span>
                </label>
              ))}
              {clientes.length === 0 && !cargando && (
                <p className="text-sm text-gray-400 text-center py-8">Presiona "Cargar" para ver clientes</p>
              )}
              {cargando && <p className="text-sm text-gray-400 text-center py-8">Cargando...</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Botón enviar */}
      <div className="mt-6 flex items-center gap-4">
        <button
          className="bg-gradient-to-r from-green-500 to-green-600 text-white px-8 py-3 rounded-xl text-sm font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-2"
          disabled={enviando || (!mensaje || totalSeleccionados === 0) || whatsappStatus !== "connected"}
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
              Enviar a {totalSeleccionados} destinatario{totalSeleccionados !== 1 ? "s" : ""}
            </span>
          )}
        </button>
        {resultado && (
          <span className="text-sm font-medium">{resultado}</span>
        )}
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
