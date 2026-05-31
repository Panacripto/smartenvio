import { useEffect, useState, useRef } from "react";

type NetInfo = { ips: string[]; port: number } | null;

export function ServiceStatus() {
  const [data, setData] = useState<StatusData>(null);
  const [net, setNet] = useState<NetInfo>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const poll = async () => {
      try {
        const [r1, r2] = await Promise.all([
          fetch("http://127.0.0.1:8000/api/services/status"),
          fetch("http://127.0.0.1:8000/api/network/info"),
        ]);
        if (mounted.current) {
          setData(await r1.json());
          setNet(await r2.json());
        }
      } catch {
        if (mounted.current) { setData(null); setNet(null); }
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => { mounted.current = false; clearInterval(id); };
  }, []);

  const dot = (ok: boolean) => (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${ok ? "bg-green-400" : "bg-red-500"}`}
      style={{ boxShadow: ok ? "0 0 6px #22c55e" : "0 0 6px #ef4444" }}
    />
  );

  return (
    <div className="px-3 py-2 space-y-1">
      <div className="flex items-center gap-2">
        {dot(data?.backend === "running")}
        <span className="text-xs text-gray-400">Backend</span>
      </div>

      {net && net.ips.length > 0 && (
        <div className="pt-1 border-t border-gray-700/30 mt-1">
          <p className="text-[10px] text-gray-500 mb-0.5">Acceso desde la red:</p>
          {net.ips.map(ip => (
            <p key={ip} className="text-[10px] text-blue-400 font-mono">http://{ip}:{net.port}</p>
          ))}
        </div>
      )}
    </div>
  );
}
