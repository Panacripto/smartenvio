import { useState, useEffect } from "react";
import api from "@/api/client";

interface ReglaUI {
  dias: number;
  activo: boolean;
  etiqueta: string;
  mensaje: string;
}

const DIAS_REGLA = [15, 7, 3, 0];

export default function Configuracion() {
  const [connStr, setConnStr] = useState("");
  const [probando, setProbando] = useState(false);
  const [resultado, setResultado] = useState<{ ok: boolean; msg: string } | null>(null);

  const [activo, setActivo] = useState(true);
  const [reglas, setReglas] = useState<ReglaUI[]>([]);
  const [seGuardando, setSeGuardando] = useState(false);
  const [seMsg, setSeMsg] = useState("");

  const [fdMensaje, setFdMensaje] = useState("");
  const [fdAutoActivo, setFdAutoActivo] = useState(false);
  const [fdAutoIntervalo, setFdAutoIntervalo] = useState(5);
  const [fdEnviarPdf, setFdEnviarPdf] = useState(true);
  const [fdIncluirSello, setFdIncluirSello] = useState(true);
  const [fdEmpresaRazon, setFdEmpresaRazon] = useState("");
  const [fdEmpresaRif, setFdEmpresaRif] = useState("");
  const [fdEmpresaDir, setFdEmpresaDir] = useState("");
  const [fdEmpresaTel, setFdEmpresaTel] = useState("");
  const [fdEmpresaLogo, setFdEmpresaLogo] = useState("");
  const [fdLogoPreview, setFdLogoPreview] = useState("");
  const [fdGuardando, setFdGuardando] = useState(false);
  const [fdMsg, setFdMsg] = useState("");

  const [cbMensaje, setCbMensaje] = useState("");
  const [cbGuardando, setCbGuardando] = useState(false);

  const [footerTexto, setFooterTexto] = useState("");
  const [footerGuardando, setFooterGuardando] = useState(false);
  const [footerMsg, setFooterMsg] = useState("");
  const [cbMsg, setCbMsg] = useState("");

  const [expandSe, setExpandSe] = useState(true);
  const [expandSeRegla, setExpandSeRegla] = useState<number>(15);
  const [showEmojisFd, setShowEmojisFd] = useState(false);
  const [showEmojisCb, setShowEmojisCb] = useState(false);
  const [showEmojisSe, setShowEmojisSe] = useState<number | null>(null);

  const EMOJIS = ["😀","😁","😂","🤣","😊","😎","👍","👎","🙌","👏","🎉","🎊","❤️","💯","✅","❌","⭐","🔥","💪","🤝","👋","📢","📌","🎯","💰","📈","📊","🏆","🛒","🚚","📦","🎁","🔔","📞","✉️","📱","☀️","🌧️","⏰","📅","🔴","🟢","🟡","🔵","🟣","⚪","🟠","🟤"];

  const insertEmojiEnTextarea = (id: string, setter: (v: string) => void) => (emoji: string) => {
    const ta = document.getElementById(id) as HTMLTextAreaElement;
    if (!ta) return;
    const s = ta.selectionStart, e = ta.selectionEnd;
    setter(ta.value.substring(0, s) + emoji + ta.value.substring(e));
    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + emoji.length; ta.focus(); }, 0);
  };

  useEffect(() => {
    api.get("/odbc/status").then(r => {
      setResultado({ ok: r.data.connected, msg: r.data.message });
      setConnStr(r.data.saved || r.data.connection_string || "");
    }).catch(() => setResultado({ ok: false, msg: "No se pudo conectar al servidor" }));

    api.get("/smartenvio/config").then(r => {
      setActivo(r.data.activo);
      const rs = DIAS_REGLA.map(d => {
        const found = (r.data.reglas || []).find((x: any) => x.dias === d);
        return found || { dias: d, activo: true, etiqueta: "", mensaje: "" };
      });
      setReglas(rs);
    }).catch(() => {});

    api.get("/factura-digital/config").then(r => {
      setFdMensaje(r.data.mensaje || "");
      setFdAutoActivo(r.data.auto_activo || false);
      setFdAutoIntervalo(r.data.auto_intervalo || 5);
      setFdEnviarPdf(r.data.enviar_pdf !== false);
      setFdIncluirSello(r.data.incluir_sello !== false);
      setFdEmpresaRazon(r.data.empresa_razon_social || "");
      setFdEmpresaRif(r.data.empresa_rif || "");
      setFdEmpresaDir(r.data.empresa_direccion || "");
      setFdEmpresaTel(r.data.empresa_telefono || "");
      setFdEmpresaLogo(r.data.empresa_logo || "");
      setFdLogoPreview(r.data.empresa_logo ? `data:image/png;base64,${r.data.empresa_logo}` : "");
    }).catch(() => {});

    api.get("/cobranza/config").then(r => {
      if (r.data.mensaje) setCbMensaje(r.data.mensaje);
    }).catch(() => {});

    api.get("/config/footer").then(r => {
      if (r.data.texto) setFooterTexto(r.data.texto);
    }).catch(() => {});
  }, []);

  const actualizarRegla = (dias: number, campo: string, valor: any) => {
    setReglas(prev => prev.map(r => r.dias === dias ? { ...r, [campo]: valor } : r));
  };

  const guardarSmart = async () => {
    setSeGuardando(true);
    setSeMsg("");
    try {
      await api.post("/smartenvio/config", { activo, reglas });
      setSeMsg("Configuración guardada");
    } catch (e: any) {
      setSeMsg("Error: " + (e.response?.data?.detail || e.message));
    }
    setSeGuardando(false);
  };

  const probar = async () => {
    setProbando(true);
    setResultado(null);
    try {
      const r = await api.post("/odbc/test", { connection_string: connStr });
      setResultado({ ok: r.data.connected, msg: r.data.message });
      if (r.data.connected && connStr) {
        await api.post("/odbc/save-config", { connection_string: connStr });
      }
    } catch (e: any) {
      setResultado({ ok: false, msg: e.response?.data?.detail || e.message });
    }
    setProbando(false);
  };

  const handleLogoFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = (reader.result as string).split(",")[1];
      setFdEmpresaLogo(b64);
      setFdLogoPreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const guardarFd = async () => {
    setFdGuardando(true);
    setFdMsg("");
    try {
      await api.post("/factura-digital/config", {
        mensaje: fdMensaje,
        auto_activo: fdAutoActivo,
        auto_intervalo: fdAutoIntervalo,
        enviar_pdf: fdEnviarPdf,
        incluir_sello: fdIncluirSello,
        empresa_razon_social: fdEmpresaRazon,
        empresa_rif: fdEmpresaRif,
        empresa_direccion: fdEmpresaDir,
        empresa_telefono: fdEmpresaTel,
        empresa_logo: fdEmpresaLogo,
      });
      setFdMsg("Guardado");
    } catch (e: any) {
      setFdMsg("Error: " + (e.response?.data?.detail || e.message));
    }
    setFdGuardando(false);
  };

  const guardarCb = async () => {
    setCbGuardando(true);
    setCbMsg("");
    try {
      await api.post("/cobranza/config", { mensaje: cbMensaje });
      setCbMsg("Guardado");
    } catch (e: any) {
      setCbMsg("Error: " + (e.response?.data?.detail || e.message));
    }
    setCbGuardando(false);
  };

  const guardarFooter = async () => {
    setFooterGuardando(true);
    setFooterMsg("");
    try {
      await api.put("/config/footer", { texto: footerTexto });
      setFooterMsg("Guardado");
    } catch (e: any) {
      setFooterMsg("Error: " + (e.response?.data?.detail || e.message));
    }
    setFooterGuardando(false);
  };

  return (
    <div className="max-w-5xl mx-auto pt-6 space-y-4">
      <h2 className="text-2xl font-bold text-gray-800">Configuración</h2>

      <div className="grid grid-cols-1 gap-5">
        <div className="bg-white rounded-xl border shadow-md p-5">
          <h3 className="text-sm font-bold text-gray-800 mb-2">Conexión ODBC</h3>
          <p className="text-xs text-gray-400 mb-2">Cadena a tu base de datos DBSAM</p>
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm font-mono min-h-[60px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            placeholder="DSN=HAC_HO;"
            value={connStr}
            onChange={e => setConnStr(e.target.value)}
          />
          <div className="flex items-center gap-2 mt-2">
            <button
              className="bg-gradient-to-r from-green-500 to-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1"
              disabled={probando}
              onClick={probar}
            >
              {probando ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              )}
              {probando ? "Probando..." : "Probar"}
            </button>
            {resultado && (
              <div className={`flex items-center gap-1.5 text-xs ${resultado.ok ? "text-green-700" : "text-red-700"}`}>
                <div className={`w-2 h-2 rounded-full ${resultado.ok ? "bg-green-500" : "bg-red-500"}`}></div>
                <span className="truncate">{resultado.msg}</span>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border shadow-md p-5">
          <h3 className="text-sm font-bold text-gray-800 mb-2">Factura Digital</h3>

          <label className="flex items-center gap-2 mb-3 cursor-pointer">
            <div className={`relative w-9 h-5 rounded-full transition-colors ${fdAutoActivo ? "bg-green-500" : "bg-gray-300"}`}>
              <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${fdAutoActivo ? "translate-x-4" : ""}`}></div>
              <input type="checkbox" className="sr-only" checked={fdAutoActivo} onChange={e => setFdAutoActivo(e.target.checked)} />
            </div>
            <span className="text-xs font-medium text-gray-700">Auto-enviar facturas nuevas</span>
          </label>

          {fdAutoActivo && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-gray-500">Revisar cada</span>
              <select className="border rounded px-2 py-1 text-xs" value={fdAutoIntervalo} onChange={e => setFdAutoIntervalo(Number(e.target.value))}>
                <option value={1}>1 minuto</option>
                <option value={2}>2 minutos</option>
                <option value={5}>5 minutos</option>
                <option value={10}>10 minutos</option>
                <option value={15}>15 minutos</option>
                <option value={30}>30 minutos</option>
              </select>
            </div>
          )}
          <label className="flex items-center gap-2 mb-3 cursor-pointer">
            <div className={`relative w-9 h-5 rounded-full transition-colors ${fdEnviarPdf ? "bg-green-500" : "bg-gray-300"}`}>
              <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${fdEnviarPdf ? "translate-x-4" : ""}`}></div>
              <input type="checkbox" className="sr-only" checked={fdEnviarPdf} onChange={e => setFdEnviarPdf(e.target.checked)} />
            </div>
            <span className="text-xs font-medium text-gray-700">Enviar PDF adjunto</span>
          </label>
          <label className="flex items-center gap-2 mb-3 cursor-pointer">
            <div className={`relative w-9 h-5 rounded-full transition-colors ${fdIncluirSello ? "bg-green-500" : "bg-gray-300"}`}>
              <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${fdIncluirSello ? "translate-x-4" : ""}`}></div>
              <input type="checkbox" className="sr-only" checked={fdIncluirSello} onChange={e => setFdIncluirSello(e.target.checked)} />
            </div>
            <span className="text-xs font-medium text-gray-700">Incluir sello PROCESADO en PDF</span>
          </label>

          <p className="text-xs text-gray-400 mb-2">
            Variables disponibles:
          </p>
          <div className="flex flex-wrap gap-1 mb-2">
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("fd-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setFdMensaje(prev => prev.substring(0, s) + "{empresa_razon_social}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 22; ta.focus(); }, 0);
            }}>{`{empresa_razon_social}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("fd-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setFdMensaje(prev => prev.substring(0, s) + "{empresa_rif}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
            }}>{`{empresa_rif}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("fd-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setFdMensaje(prev => prev.substring(0, s) + "{cliente}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 9; ta.focus(); }, 0);
            }}>{`{cliente}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("fd-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setFdMensaje(prev => prev.substring(0, s) + "{facturas}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 10; ta.focus(); }, 0);
            }}>{`{facturas}`}</button>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <button
              className="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-md px-2 py-1 font-medium transition-colors flex items-center gap-1"
              onClick={() => setShowEmojisFd(!showEmojisFd)}
            >
              <span>😀</span> Emojis
            </button>
          </div>
          {showEmojisFd && (
            <div className="mb-2 p-2 border rounded-lg bg-white max-h-32 overflow-y-auto grid grid-cols-12 gap-0.5">
              {EMOJIS.map((e) => (
                <button key={e} className="text-lg hover:bg-gray-100 rounded p-0.5 transition-colors" onClick={() => { insertEmojiEnTextarea("fd-textarea", setFdMensaje)(e); setShowEmojisFd(false); }}>{e}</button>
              ))}
            </div>
          )}
          <textarea id="fd-textarea"
            className="w-full border rounded-lg px-3 py-2 text-sm min-h-[180px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none font-mono"
            value={fdMensaje}
            onChange={e => setFdMensaje(e.target.value)}
          />

          <p className="text-xs text-gray-400 mt-3 mb-1">Datos del emisor (aparecen en el PDF):</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500">Razón Social</label>
              <input className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={fdEmpresaRazon} onChange={e => setFdEmpresaRazon(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500">RIF</label>
              <input className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={fdEmpresaRif} onChange={e => setFdEmpresaRif(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Dirección</label>
              <input className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={fdEmpresaDir} onChange={e => setFdEmpresaDir(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Teléfono</label>
              <input className="w-full border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" value={fdEmpresaTel} onChange={e => setFdEmpresaTel(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500">Logo (PNG/JPG)</label>
              <input type="file" accept="image/png,image/jpeg" className="w-full text-xs" onChange={handleLogoFile} />
              {fdLogoPreview && (
                <img src={fdLogoPreview} className="mt-1 h-12 w-12 object-contain border rounded" alt="Logo preview" />
              )}
            </div>
          </div>

          <div className="mt-2">
            <button
              className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1"
              disabled={fdGuardando}
              onClick={guardarFd}
            >
              {fdGuardando ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              )}
              {fdGuardando ? "Guardando..." : "Guardar"}
            </button>
            {fdMsg && (
              <span className={`ml-2 text-xs ${fdMsg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>{fdMsg}</span>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border shadow-md p-5">
          <h3 className="text-sm font-bold text-gray-800 mb-2">Cobranza</h3>
          <p className="text-xs text-gray-400 mb-2">
            Variables disponibles:
          </p>
          <div className="flex flex-wrap gap-1 mb-2">
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{FC_DESCRIPCION}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 17; ta.focus(); }, 0);
            }}>{`{FC_DESCRIPCION}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{FC_SALDO_TOTAL}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
            }}>{`{FC_SALDO_TOTAL}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{FC_DOCUMENTOS}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
            }}>{`{FC_DOCUMENTOS}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{FC_CRITERIO}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
            }}>{`{FC_CRITERIO}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{FC_CODIGO}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 11; ta.focus(); }, 0);
            }}>{`{FC_CODIGO}`}</button>
            <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{FC_TELEFONO}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
            }}>{`{FC_TELEFONO}`}</button>
            <button className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{empresa_razon_social}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 22; ta.focus(); }, 0);
            }}>{`{empresa_razon_social}`}</button>
            <button className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-md px-2 py-1 font-medium" onClick={() => {
              const ta = document.getElementById("cb-textarea") as HTMLTextAreaElement; if (!ta) return;
              const s = ta.selectionStart, e = ta.selectionEnd;
              setCbMensaje(prev => prev.substring(0, s) + "{empresa_rif}" + prev.substring(e));
              setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
            }}>{`{empresa_rif}`}</button>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <button
              className="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-md px-2 py-1 font-medium transition-colors flex items-center gap-1"
              onClick={() => setShowEmojisCb(!showEmojisCb)}
            >
              <span>😀</span> Emojis
            </button>
          </div>
          {showEmojisCb && (
            <div className="mb-2 p-2 border rounded-lg bg-white max-h-32 overflow-y-auto grid grid-cols-12 gap-0.5">
              {EMOJIS.map((e) => (
                <button key={e} className="text-lg hover:bg-gray-100 rounded p-0.5 transition-colors" onClick={() => { insertEmojiEnTextarea("cb-textarea", setCbMensaje)(e); setShowEmojisCb(false); }}>{e}</button>
              ))}
            </div>
          )}
          <textarea id="cb-textarea"
            className="w-full border rounded-lg px-3 py-2 text-sm min-h-[180px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none font-mono"
            value={cbMensaje}
            onChange={e => setCbMensaje(e.target.value)}
          />
          <div className="mt-2">
            <button
              className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1"
              disabled={cbGuardando}
              onClick={guardarCb}
            >
              {cbGuardando ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              )}
              {cbGuardando ? "Guardando..." : "Guardar"}
            </button>
            {cbMsg && (
              <span className={`ml-2 text-xs ${cbMsg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>{cbMsg}</span>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border shadow-md p-5">
          <h3 className="text-sm font-bold text-gray-800 mb-2">Pie de mensaje</h3>
          <p className="text-xs text-gray-400 mb-2">
            Texto que se agrega automaticamente al final de todos los mensajes enviados.
          </p>
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm min-h-[60px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
            value={footerTexto}
            onChange={e => setFooterTexto(e.target.value)}
            placeholder="Enviado desde SmartEnvios"
          />
          <div className="mt-2">
            <button
              className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1"
              disabled={footerGuardando}
              onClick={guardarFooter}
            >
              {footerGuardando ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              )}
              {footerGuardando ? "Guardando..." : "Guardar"}
            </button>
            {footerMsg && (
              <span className={`ml-2 text-xs ${footerMsg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>{footerMsg}</span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-md">
        <div className="p-5 cursor-pointer select-none flex items-center justify-between" onClick={() => setExpandSe(!expandSe)}>
          <div>
            <h3 className="text-sm font-bold text-gray-800">SmartEnvios</h3>
            <p className="text-xs text-gray-400 mt-0.5">Recordatorios automáticos al iniciar la app</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer" onClick={e => e.stopPropagation()}>
              <div className={`relative w-9 h-5 rounded-full transition-colors ${activo ? "bg-green-500" : "bg-gray-300"}`}>
                <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${activo ? "translate-x-4" : ""}`}></div>
                <input type="checkbox" className="sr-only" checked={activo} onChange={e => setActivo(e.target.checked)} />
              </div>
              <span className="text-xs font-medium text-gray-600">Activo</span>
            </label>
            <span className="text-gray-400 text-sm transition-transform" style={{ transform: expandSe ? "rotate(180deg)" : "none" }}>▼</span>
          </div>
        </div>
        {expandSe && (
          <div className="px-4 pb-4 border-t pt-3">
            <div className="space-y-2">
              {reglas.map(reg => {
                const expanded = expandSeRegla === reg.dias;
                return (
                  <div key={reg.dias} className="border rounded-lg">
                    <div className="flex items-center justify-between px-3 py-2 cursor-pointer select-none" onClick={() => setExpandSeRegla(expanded ? -1 : reg.dias)}>
                      <div className="flex items-center gap-2">
                        <div className={`relative w-8 h-4 rounded-full transition-colors ${reg.activo ? "bg-green-500" : "bg-gray-300"}`} onClick={e => { e.stopPropagation(); actualizarRegla(reg.dias, "activo", !reg.activo); }}>
                          <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform ${reg.activo ? "translate-x-3.5" : ""}`}></div>
                          <input type="checkbox" className="sr-only" checked={reg.activo} readOnly />
                        </div>
                        <span className="text-xs font-medium text-gray-700">
                          {reg.dias === 0 ? "Vence hoy" : `Vence en ${reg.dias} días`}
                        </span>
                      </div>
                      <span className={`text-gray-400 text-xs transition-transform ${expanded ? "rotate-180" : ""}`}>▼</span>
                    </div>
                    {expanded && (
                      <div className="px-3 pb-3 border-t pt-2">
                        <input
                          type="text"
                          className="w-full border rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-green-500 mb-1.5"
                          value={reg.etiqueta}
                          onChange={e => actualizarRegla(reg.dias, "etiqueta", e.target.value)}
                          placeholder={`Ej: Vence en ${reg.dias} días`}
                        />
                        <textarea id={`se-textarea-${reg.dias}`}
                          className="w-full border rounded px-2 py-1 text-xs min-h-[100px] focus:outline-none focus:ring-1 focus:ring-green-500 resize-none"
                          value={reg.mensaje}
                          onChange={e => actualizarRegla(reg.dias, "mensaje", e.target.value)}
                        />
                        <div className="mt-1 flex flex-wrap gap-1">
                          <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{FC_DESCRIPCION}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 17; ta.focus(); }, 0);
                          }}>{`{FC_DESCRIPCION}`}</button>
                          <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{FC_SALDO_TOTAL}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
                          }}>{`{FC_SALDO_TOTAL}`}</button>
                          <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{FC_DOCUMENTOS}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 15; ta.focus(); }, 0);
                          }}>{`{FC_DOCUMENTOS}`}</button>
                          <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{FC_CRITERIO}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
                          }}>{`{FC_CRITERIO}`}</button>
                          <button className="text-xs bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{FC_CODIGO}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 11; ta.focus(); }, 0);
                          }}>{`{FC_CODIGO}`}</button>
                          <button className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{empresa_razon_social}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 22; ta.focus(); }, 0);
                          }}>{`{empresa_razon_social}`}</button>
                          <button className="text-xs bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 rounded-md px-2 py-1 font-medium" onClick={() => {
                            const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement; if (!ta) return;
                            const s = ta.selectionStart, e = ta.selectionEnd;
                            const prev = reg.mensaje;
                            actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + "{empresa_rif}" + prev.substring(e));
                            setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 13; ta.focus(); }, 0);
                          }}>{`{empresa_rif}`}</button>
                        </div>
                        <div className="mt-1.5 flex items-center gap-2">
                          <button
                            className="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-md px-2 py-1 font-medium transition-colors flex items-center gap-1"
                            onClick={() => setShowEmojisSe(showEmojisSe === reg.dias ? null : reg.dias)}
                          >
                            <span>😀</span> Emojis
                          </button>
                        </div>
                        {showEmojisSe === reg.dias && (
                          <div className="mt-1 p-2 border rounded-lg bg-white max-h-32 overflow-y-auto grid grid-cols-12 gap-0.5">
                            {EMOJIS.map((e) => (
                              <button key={e} className="text-lg hover:bg-gray-100 rounded p-0.5 transition-colors" onClick={() => {
                                const ta = document.getElementById(`se-textarea-${reg.dias}`) as HTMLTextAreaElement;
                                if (!ta) return;
                                const s = ta.selectionStart, end = ta.selectionEnd;
                                const prev = reg.mensaje;
                                actualizarRegla(reg.dias, "mensaje", prev.substring(0, s) + e + prev.substring(end));
                                setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + e.length; ta.focus(); }, 0);
                                setShowEmojisSe(null);
                              }}>{e}</button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="mt-3 flex items-center gap-2">
              <button
                className="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 transition-all shadow-sm flex items-center gap-1"
                disabled={seGuardando}
                onClick={guardarSmart}
              >
                {seGuardando ? (
                  <span className="flex items-center gap-1">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                    Guardando...
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    Guardar SmartEnvios
                  </span>
                )}
              </button>
              {seMsg && (
                <span className={`text-xs ${seMsg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>{seMsg}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
