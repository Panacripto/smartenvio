import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/layout";
import WhatsAppPage from "@/pages/WhatsAppPage";
import { initTheme } from "@/lib/theme";
import EnvioMasivo from "@/pages/EnvioMasivo";
import Configuracion from "@/pages/Configuracion";
import Cobranza from "@/pages/Cobranza";
import SmartEnvios from "@/pages/SmartEnvios";
import FacturaDigital from "@/pages/FacturaDigital";
import Campaigns from "@/pages/Campaigns";
import GestionPagos from "@/pages/GestionPagos";
import api from "@/api/client";

export default function App() {
  const [licenciaValida, setLicenciaValida] = useState<boolean | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [verificado, setVerificado] = useState(false);

  useEffect(() => { initTheme(); }, []);

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get("/license/status");
        setLicenciaValida(r.data.valida === true || r.data.razon === "Sin archivo de licencia");
      } catch {
        setLicenciaValida(false);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [cfg, clientes] = await Promise.all([
          api.get("/smartenvio/config"),
          api.get("/smartenvio/clientes"),
        ]);
        if (cfg.data.activo && clientes.data.reglas?.length > 0) {
          setModalOpen(true);
        }
      } catch {
      }
      setVerificado(true);
    })();
  }, []);

  if (licenciaValida === null) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100/80 flex items-center justify-center">
        <span className="w-8 h-8 border-4 border-green-500 border-t-transparent rounded-full animate-spin"></span>
      </div>
    );
  }

  if (!licenciaValida) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100/80 flex items-center justify-center p-6">
        <div className="bg-white rounded-2xl shadow-2xl border p-8 w-full max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl text-red-500">!</span>
          </div>
          <h1 className="text-xl font-bold text-gray-800 mb-2">Licencia invalida</h1>
          <p className="text-sm text-gray-500 mb-4">El archivo de licencia no es valido para este equipo.</p>
          <p className="text-xs text-gray-400">Usa el generador de licencias en backend/generar_licencia_gui.pyw</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<WhatsAppPage />} />
          <Route path="/envio-masivo" element={<EnvioMasivo />} />
          <Route path="/cobranza" element={<Cobranza />} />
          <Route path="/smartenvio" element={<SmartEnvios />} />
          <Route path="/factura-digital" element={<FacturaDigital />} />
          <Route path="/campaigns" element={<Campaigns />} />
          <Route path="/gestion-pagos" element={<GestionPagos />} />
          <Route path="/configuracion" element={<Configuracion />} />
        </Route>
      </Routes>

      {verificado && modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-gray-100 rounded-2xl shadow-2xl p-6 w-[800px] max-h-[90vh] overflow-y-auto relative">
            <button
              className="absolute top-3 right-3 text-gray-400 hover:text-gray-700 text-xl leading-none"
              onClick={() => setModalOpen(false)}
            >
              &times;
            </button>
            <SmartEnvios asModal onClose={() => setModalOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}
