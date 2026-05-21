import { useEffect, useState, useRef } from "react";

type WStatus = { status: string; connected: boolean };
type StatusData = { backend: string; whatsapp: WStatus } | null;

export function ServiceStatus() {
  const [data, setData] = useState<StatusData>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const poll = async () => {
      try {
        const r = await fetch("http://127.0.0.1:8000/api/services/status");
        const d: StatusData = await r.json();
        if (mounted.current) setData(d);
      } catch {
        if (mounted.current) setData(null);
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
      <div className="flex items-center gap-2">
        {dot(data?.whatsapp?.connected === true)}
        <span className="text-xs text-gray-400">
          WhatsApp {data?.whatsapp?.status && data.whatsapp.status !== "connected"
            ? `(${data.whatsapp.status})` : ""}
        </span>
      </div>
    </div>
  );
}
