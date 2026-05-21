import { useEffect, useState } from "react";
import api from "@/api/client";

interface Cliente {
  FC_CODIGO: string;
  FC_DESCRIPCION: string;
  FC_TELEFONO: string;
  FC_SALDO_TOTAL: number;
  FC_DOCUMENTOS: number;
  FC_CRITERIO: string;
}

interface Regla {
  dias: number;
  etiqueta: string;
  mensaje: string;
  clientes: Cliente[];
}

interface ReglaResultado {
  enviados: number;
  fallidos: number;
  detalles: string[];
}

interface Props {
  asModal?: boolean;
  onClose?: () => void;
}

export default function SmartEnvios({ asModal, onClose }: Props) {
  const [reglas, setReglas] = useState<Regla[]>([]);
  const [mensajes, setMensajes] = useState<Record<number, string>>({});
  const [enviando, setEnviando] = useState<Record<number, boolean>>({});
  const [resultados, setResultados] = useState<Record<number, ReglaResultado>>({});
  const [cargando, setCargando] = useState(true);
  const [previewAbierto, setPreviewAbierto] = useState<Record<string, boolean>>({});
  const [showEmojis, setShowEmojis] = useState<number | null>(null);
  const EMOJIS = ["😀","😁","😂","🤣","😊","😎","👍","👎","🙌","👏","🎉","🎊","❤️","💯","✅","❌","⭐","🔥","💪","🤝","👋","📢","📌","🎯","💰","📈","📊","🏆","🛒","🚚","📦","🎁","🔔","📞","✉️","📱","☀️","🌧️","⏰","📅","🔴","🟢","🟡","🔵","🟣","⚪","🟠","🟤"];

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get("/smartenvio/clientes");
        const data = r.data.reglas || [];
        setReglas(data);
        const msgs: Record<number, string> = {};
        data.forEach((reg: Regla) => { msgs[reg.dias] = reg.mensaje; });
        setMensajes(msgs);
      } catch { }
      setCargando(false);
    })();
  }, []);

  const enviar = async (dias: number) => {
    setEnviando(prev => ({ ...prev, [dias]: true }));
    try {
      const r = await api.post("/smartenvio/enviar", { dias, mensaje: mensajes[dias] });
      setResultados(prev => ({ ...prev, [dias]: r.data }));
    } catch (e: any) {
      setResultados(prev => ({
        ...prev,
        [dias]: { enviados: 0, fallidos: 0, detalles: ["Error: " + (e.response?.data?.detail || e.message)] },
      }));
    }
    setEnviando(prev => ({ ...prev, [dias]: false }));
  };

  const formatearMonto = (n: number): string =>
    n?.toLocaleString?.("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? String(n);

  const renderMensaje = (tmpl: string, c: Cliente) =>
    tmpl
      .replace(/\{FC_CODIGO\}/g, c.FC_CODIGO ?? "")
      .replace(/\{FC_DESCRIPCION\}/g, c.FC_DESCRIPCION ?? "")
      .replace(/\{FC_TELEFONO\}/g, c.FC_TELEFONO ?? "")
      .replace(/\{FC_SALDO_TOTAL\}/g, formatearMonto(c.FC_SALDO_TOTAL))
      .replace(/\{FC_DOCUMENTOS\}/g, String(c.FC_DOCUMENTOS ?? ""))
      .replace(/\{FC_CRITERIO\}/g, c.FC_CRITERIO ?? "");

  const togglePreview = (key: string) =>
    setPreviewAbierto(prev => ({ ...prev, [key]: !prev[key] }));

  const totalClientes = reglas.reduce((s, r) => s + r.clientes.length, 0);

  const content = (
    <>
      <div className="flex items-center justify-between mb-4">
        <h2 className={`font-bold text-gray-800 ${asModal ? "text-xl" : "text-2xl"}`}>
          SmartEnvios
        </h2>
        {totalClientes > 0 && (
          <span className="text-sm text-gray-500 bg-white border rounded-full px-3 py-1">
            {totalClientes} cliente{totalClientes !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {cargando ? (
        <p className="text-sm text-gray-400 text-center py-8">Consultando...</p>
      ) : reglas.length === 0 ? (
        <div className="bg-white rounded-xl border shadow-md p-8 text-center">
          <p className="text-gray-400 text-sm mb-1">No hay reglas activas con clientes disponibles</p>
          <p className="text-xs text-gray-300">Verifica la configuraci&oacute;n de SmartEnvios</p>
        </div>
      ) : (
        <div className="space-y-4">
          {reglas.map(reg => {
            const res = resultados[reg.dias];
            return (
              <div key={reg.dias} className="bg-white rounded-xl border shadow-md p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-800 text-sm">
                    {reg.etiqueta}
                    <span className="text-gray-400 font-normal ml-2">
                      ({reg.clientes.length} cliente{reg.clientes.length !== 1 ? "s" : ""})
                    </span>
                  </h3>
                </div>

                <textarea id={`se-${reg.dias}`}
                  className="w-full border rounded-lg px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none mb-2"
                  value={mensajes[reg.dias] ?? ""}
                  onChange={e => setMensajes(prev => ({ ...prev, [reg.dias]: e.target.value }))}
                />

                <div className="flex items-center gap-2 mb-3">
                  <button
                    className="text-xs bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 rounded-md px-2 py-1 font-medium transition-colors flex items-center gap-1"
                    onClick={() => setShowEmojis(showEmojis === reg.dias ? null : reg.dias)}
                  >
                    <span>😀</span> Emojis
                  </button>
                </div>
                {showEmojis === reg.dias && (
                  <div className="mb-3 p-2 border rounded-lg bg-white max-h-32 overflow-y-auto grid grid-cols-12 gap-0.5">
                    {EMOJIS.map((e) => (
                      <button key={e} className="text-lg hover:bg-gray-100 rounded p-0.5 transition-colors" onClick={() => {
                        const ta = document.getElementById(`se-${reg.dias}`) as HTMLTextAreaElement;
                        if (!ta) return;
                        const s = ta.selectionStart, end = ta.selectionEnd;
                        const prev = mensajes[reg.dias] ?? "";
                        setMensajes(prevMsgs => ({ ...prevMsgs, [reg.dias]: prev.substring(0, s) + e + prev.substring(end) }));
                        setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + e.length; ta.focus(); }, 0);
                        setShowEmojis(null);
                      }}>{e}</button>
                    ))}
                  </div>
                )}

                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm mb-3">
                  <div className="divide-y divide-gray-100 max-h-[150px] overflow-y-auto">
                    {reg.clientes.map((c, i) => (
                      <div key={c.FC_CODIGO} className={`flex items-center gap-2 px-3 py-1.5 text-sm transition-colors hover:bg-green-50/60 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}>
                        <span className="font-mono text-xs font-medium text-gray-700 w-14">{c.FC_CODIGO}</span>
                        <span className="flex-1 truncate text-xs text-gray-700">{c.FC_DESCRIPCION}</span>
                        <span className="text-xs text-gray-400 w-28 truncate">{c.FC_TELEFONO}</span>
                        <span className="text-xs font-mono text-red-600 font-medium w-20 text-right">{formatearMonto(c.FC_SALDO_TOTAL)}</span>
                        <span className="text-xs text-gray-400 w-12 text-right">{c.FC_DOCUMENTOS}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    className="bg-gradient-to-r from-red-500 to-red-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:from-red-600 hover:to-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-2"
                    disabled={enviando[reg.dias] || !mensajes[reg.dias]}
                    onClick={() => enviar(reg.dias)}
                  >
                    {enviando[reg.dias] ? (
                      <span className="flex items-center gap-2">
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                        Enviando...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                        Enviar a {reg.clientes.length} cliente{reg.clientes.length !== 1 ? "s" : ""}
                      </span>
                    )}
                  </button>
                  {res && (
                    <span className="text-xs font-medium">
                      <span className="text-green-600">{res.enviados} enviados</span>
                      {res.fallidos > 0 && <span className="text-red-600 ml-1">| {res.fallidos} fallidos</span>}
                    </span>
                  )}
                </div>

                {res && res.detalles.length > 0 && (
                  <div className="mt-2 bg-gray-50 border rounded-lg p-2 max-h-24 overflow-y-auto">
                    <div className="text-xs space-y-0.5">
                      {res.detalles.map((d, i) => (
                        <div key={i} className={d.startsWith("✓") ? "text-green-600" : "text-red-600"}>{d}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {asModal && (
        <div className="mt-4 flex justify-end">
          <button className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 flex items-center gap-1.5 transition-colors" onClick={onClose}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            Cerrar
          </button>
        </div>
      )}
    </>
  );

  if (asModal) return content;

  return <div className="h-full overflow-y-auto p-6">{content}</div>;
}
