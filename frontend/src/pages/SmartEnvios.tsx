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

interface ProveedorPago {
  codigo: string;
  nombre: string;
  total: number;
  documentos: number;
}

interface PagoRegla {
  tipo: string;
  etiqueta: string;
  mensaje: string;
  proveedores: ProveedorPago[];
  total_general: number;
}

interface PagoData {
  activo: boolean;
  reglas: PagoRegla[];
  telefonos?: string[];
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

  const [pagoData, setPagoData] = useState<PagoData>({ activo: false, reglas: [] });
  const [pagoEnviando, setPagoEnviando] = useState<string | null>(null);
  const [pagoResultado, setPagoResultado] = useState<{ tipo: string; res: ReglaResultado } | null>(null);
  const [enviandoTodo, setEnviandoTodo] = useState(false);
  const [todoResultado, setTodoResultado] = useState<{ enviados: number; fallidos: number; detalles: string[] } | null>(null);

  const EMOJIS = ["😀","😁","😂","🤣","😊","😎","👍","👎","🙌","👏","🎉","🎊","❤️","💯","✅","❌","⭐","🔥","💪","🤝","👋","📢","📌","🎯","💰","📈","📊","🏆","🛒","🚚","📦","🎁","🔔","📞","✉️","📱","☀️","🌧️","⏰","📅","🔴","🟢","🟡","🔵","🟣","⚪","🟠","🟤"];

  useEffect(() => {
    (async () => {
      try {
        const [r1, r2] = await Promise.all([
          api.get("/smartenvio/clientes"),
          api.get("/smartenvio/proveedores"),
        ]);
        const data = r1.data.reglas || [];
        setReglas(data);
        const msgs: Record<number, string> = {};
        data.forEach((reg: Regla) => { msgs[reg.dias] = reg.mensaje; });
        setMensajes(msgs);
        setPagoData(r2.data || { activo: false, reglas: [] });
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

  const enviarTodo = async () => {
    setEnviandoTodo(true);
    setTodoResultado(null);
    try {
      const r = await api.post("/smartenvio/enviar-todo");
      setTodoResultado(r.data);
    } catch (e: any) {
      setTodoResultado({ enviados: 0, fallidos: 0, detalles: ["Error: " + (e.response?.data?.detail || e.message)] });
    }
    setEnviandoTodo(false);
  };

  const enviarPagos = async (tipo: string) => {
    setPagoEnviando(tipo);
    setPagoResultado(null);
    try {
      const r = await api.post("/gestion-pagos/enviar", null, { params: { criterio: tipo } });
      setPagoResultado({ tipo, res: r.data });
    } catch (e: any) {
      setPagoResultado({ tipo, res: { enviados: 0, fallidos: 0, detalles: ["Error: " + (e.response?.data?.detail || e.message)] } });
    }
    setPagoEnviando(null);
  };

  const formatearMonto = (n: number): string =>
    n?.toLocaleString?.("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? String(n);

  const totalClientes = reglas.reduce((s, r) => s + r.clientes.length, 0);
  const totalProveedores = pagoData.reglas.reduce((s, r) => s + r.proveedores.length, 0);
  const hasData = reglas.length > 0 || (pagoData.activo && totalProveedores > 0);

  const renderResultado = (res: ReglaResultado | null) => {
    if (!res) return null;
    return (
      <div className="mt-2 space-y-1">
        <span className="text-xs font-medium">
          <span className="text-green-600">{res.enviados} enviados</span>
          {res.fallidos > 0 && <span className="text-red-600 ml-1">| {res.fallidos} fallidos</span>}
        </span>
        {res.detalles.length > 0 && (
          <div className="bg-gray-50 border rounded-lg p-2 max-h-24 overflow-y-auto">
            <div className="text-xs space-y-0.5">
              {res.detalles.map((d, i) => (
                <div key={i} className={d.startsWith("✓") ? "text-green-600" : "text-red-600"}>{d}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const content = (
    <>
      <div className="flex items-center justify-between mb-4">
        <h2 className={`font-bold text-gray-800 ${asModal ? "text-xl" : "text-2xl"}`}>
          SmartEnvios
        </h2>
        <div className="flex items-center gap-2">
          {hasData && (
            <button
              className="bg-gradient-to-r from-green-500 to-emerald-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium hover:from-green-600 hover:to-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-1.5"
              disabled={enviandoTodo}
              onClick={enviarTodo}
            >
              {enviandoTodo ? (
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
              )}
              {enviandoTodo ? "Enviando..." : "Enviar Todo"}
            </button>
          )}
          {hasData && (
            <span className="text-sm text-gray-500 bg-white border rounded-full px-3 py-1">
              {totalClientes > 0 && `${totalClientes} cliente${totalClientes !== 1 ? "s" : ""}`}
              {totalClientes > 0 && totalProveedores > 0 && " | "}
              {totalProveedores > 0 && `${totalProveedores} proveedor${totalProveedores !== 1 ? "es" : ""}`}
            </span>
          )}
        </div>
      </div>
      {todoResultado && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-xl p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-green-800">
              {todoResultado.enviados} enviados{todoResultado.fallidos > 0 ? `, ${todoResultado.fallidos} fallidos` : ""}
            </span>
            <button className="text-xs text-green-600 hover:text-green-800" onClick={() => setTodoResultado(null)}>Cerrar</button>
          </div>
          {todoResultado.detalles.length > 0 && (
            <div className="mt-2 text-xs text-gray-600 space-y-0.5">
              {todoResultado.detalles.map((d, i) => <div key={i}>{d}</div>)}
            </div>
          )}
        </div>
      )}

      {cargando ? (
        <p className="text-sm text-gray-400 text-center py-8">Consultando...</p>
      ) : !hasData ? (
        <div className="bg-white rounded-xl border shadow-md p-8 text-center">
          <p className="text-gray-400 text-sm mb-1">No hay reglas activas con datos disponibles</p>
          <p className="text-xs text-gray-300">Verifica la configuraci&oacute;n de SmartEnvios y Gesti&oacute;n de Pagos</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* ===== COBRANZA SECTION ===== */}
          {reglas.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-blue-600 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>
                Cobranza — Clientes que nos deben
              </h3>
              <div className="space-y-3">
                {reglas.map(reg => {
                  const res = resultados[reg.dias];
                  return (
                    <div key={reg.dias} className="bg-white rounded-xl border shadow-md p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-800 text-sm">
                          {reg.etiqueta}
                          <span className="text-gray-400 font-normal ml-2">
                            ({reg.clientes.length} cliente{reg.clientes.length !== 1 ? "s" : ""})
                          </span>
                        </h4>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-400">{reg.clientes.reduce((s, c) => s + (c.FC_DOCUMENTOS || 0), 0)} doc.</span>
                          <span className="text-xs font-mono text-red-600 font-semibold">${formatearMonto(reg.clientes.reduce((s, c) => s + (c.FC_SALDO_TOTAL || 0), 0))}</span>
                        </div>
                      </div>
                      <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm mb-2">
                        <div className="divide-y divide-gray-100 max-h-[120px] overflow-y-auto">
                          {reg.clientes.map((c, i) => (
                            <div key={c.FC_CODIGO} className={`flex items-center gap-2 px-3 py-1 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}>
                              <span className="font-mono text-xs text-gray-700 w-14 truncate">{c.FC_CODIGO}</span>
                              <span className="flex-1 truncate text-xs text-gray-700">{c.FC_DESCRIPCION}</span>
                              <span className="text-xs font-mono text-red-600 font-medium w-20 text-right">{formatearMonto(c.FC_SALDO_TOTAL)}</span>
                              <span className="text-xs text-gray-400 w-12 text-right">{c.FC_DOCUMENTOS || 0} doc.</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          className="bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-1.5 rounded-lg text-xs font-medium hover:from-red-600 hover:to-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-1.5"
                          disabled={enviando[reg.dias] || !mensajes[reg.dias]}
                          onClick={() => enviar(reg.dias)}
                        >
                          {enviando[reg.dias] ? (
                            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                          ) : (
                            <>
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                              Enviar
                            </>
                          )}
                        </button>
                        {renderResultado(res)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ===== PAGOS SECTION ===== */}
          {pagoData.activo && pagoData.reglas.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-purple-600 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                Pagos — Proveedores que debemos
                {pagoData.telefonos && pagoData.telefonos.length > 0 && (
                  <span className="text-xs font-normal text-gray-400 ml-1">
                    (envía a {pagoData.telefonos.join(", ")})
                  </span>
                )}
              </h3>
              <div className="space-y-3">
                {pagoData.reglas.map(reg => (
                  <div key={reg.tipo} className="bg-white rounded-xl border shadow-md p-4">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-800 text-sm">
                          {reg.etiqueta}
                          <span className="text-gray-400 font-normal ml-2">
                            ({reg.proveedores.length} proveedor{reg.proveedores.length !== 1 ? "es" : ""})
                          </span>
                        </h4>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-400">{reg.proveedores.reduce((s, p) => s + (p.documentos || 0), 0)} doc.</span>
                          <span className="text-xs font-mono text-red-600 font-semibold">${formatearMonto(reg.total_general)}</span>
                        </div>
                      </div>
                      <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm mb-2">
                        <div className="divide-y divide-gray-100 max-h-[120px] overflow-y-auto">
                          {reg.proveedores.map((p, i) => (
                          <div key={p.codigo} className={`flex items-center gap-2 px-3 py-1 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}>
                            <span className="font-mono text-xs text-gray-700 w-14 truncate">{p.codigo}</span>
                            <span className="flex-1 truncate text-xs text-gray-700">{p.nombre}</span>
                            <span className="text-xs font-mono text-red-600 font-medium w-20 text-right">{formatearMonto(p.total)}</span>
                            <span className="text-xs text-gray-400 w-12 text-right">{p.documentos} doc.</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        className="bg-gradient-to-r from-purple-500 to-purple-600 text-white px-4 py-1.5 rounded-lg text-xs font-medium hover:from-purple-600 hover:to-purple-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md flex items-center gap-1.5"
                        disabled={!!pagoEnviando}
                        onClick={() => enviarPagos(reg.tipo === "vencidas" ? "vencidas" : "por_vencer")}
                      >
                        {!!pagoEnviando ? (
                          <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                        ) : (
                          <>
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                            Enviar recordatorio
                          </>
                        )}
                      </button>
                      {pagoResultado?.tipo === reg.tipo && renderResultado(pagoResultado.res)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
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
