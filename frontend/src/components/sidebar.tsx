import { NavLink } from "react-router-dom";
import api from "@/api/client";
import { ServiceStatus } from "./ServiceStatus";

const items = [
  { to: "/", label: "Vincular Teléfono", icon: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" },
  { to: "/smartenvio", label: "SmartEnvios", icon: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" },
  { to: "/factura-digital", label: "Factura Digital", icon: "M9 12h6M9 16h6M9 8h6M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16l-3-2-2 2-2-2-2 2-2-2-3 2z" },
  { to: "/cobranza", label: "Cobranza", icon: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" },
  { to: "/gestion-pagos", label: "Gestión de Pagos", icon: "M17 9V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2m2 4h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2zm7-5a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" },
  { to: "/envio-masivo", label: "Envío Masivo", icon: "M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2z" },
  { to: "/campaigns", label: "Campañas", icon: "M11 3.055A9.001 9.001 0 1020.945 13H11V3.055zM13 2.055V11h8.945A9.001 9.001 0 0013 2.055z" },
  { to: "/configuracion", label: "Configuración", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm3-16l1.3 3.26a9.96 9.96 0 0 1 2.46 1.42l3.38-.68 1.42 2.46-2.18 2.66a9.96 9.96 0 0 1 0 2.84l2.18 2.66-1.42 2.46-3.38-.68a9.96 9.96 0 0 1-2.46 1.42L15 21h-3l-1.3-3.26a9.96 9.96 0 0 1-2.46-1.42l-3.38.68-1.42-2.46 2.18-2.66a9.96 9.96 0 0 1 0-2.84L3.44 7.7l1.42-2.46 3.38.68A9.96 9.96 0 0 1 10.7 4.5L12 1h3z" },
];

export function Sidebar() {
  const cerrarSesion = async () => {
    try { await api.post("/whatsapp/logout"); } catch {}
  };

  return (
    <aside className="w-56 bg-gradient-to-b from-gray-900 to-gray-800 min-h-screen p-4 flex flex-col shadow-lg">
      <div className="flex flex-col items-center mb-8 px-2 pt-2">
        <svg className="w-14 h-14 mb-2" viewBox="0 0 64 64">
          <defs>
            <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#22c55e" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
          </defs>
          <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#lg)" />
          <path d="M20 20 Q44 8 44 28 Q20 28 20 44 Q44 54 44 44" fill="none" stroke="#fff" strokeWidth="5.5" strokeLinecap="round" />
        </svg>
        <span className="text-lg font-bold text-white tracking-tight">SmartEnvios</span>
        <span className="text-[10px] text-gray-500 mt-0.5">By CriptoPana</span>
      </div>
      <nav className="space-y-1 flex-1">
        {items.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 " +
              (isActive
                ? "bg-green-500/20 text-green-400 font-medium shadow-sm border border-green-500/10"
                : "text-gray-400 hover:text-white hover:bg-white/5")
            }
          >
            <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
            </svg>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 mb-2"></div>
      <ServiceStatus />
      <button
        onClick={cerrarSesion}
        className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 text-red-400 hover:text-red-300 hover:bg-red-500/10"
      >
        <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H6a2 2 0 01-2-2V7a2 2 0 012-2h5a2 2 0 012 2v1" />
        </svg>
        <span>Cerrar sesión</span>
      </button>
    </aside>
  );
}
