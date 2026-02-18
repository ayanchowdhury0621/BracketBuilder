import { Outlet } from "react-router";
import { Navbar, BottomNav } from "./Navbar";
import { BracketProvider } from "../context/BracketContext";
import { Toast } from "./Toast";

export function Layout() {
  return (
    <BracketProvider>
      <div style={{ minHeight: "100vh" }}>
        <Navbar />
        <Outlet />
        <BottomNav />
        <Toast />
      </div>
    </BracketProvider>
  );
}
