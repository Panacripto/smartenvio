import { Outlet } from "react-router-dom";
import { Sidebar } from "./sidebar";
import Notifications from "./Notifications";

export function Layout() {
  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 bg-gradient-to-br from-gray-50 to-gray-100/80 min-h-screen">
        <Outlet />
      </main>
      <Notifications />
    </div>
  );
}
