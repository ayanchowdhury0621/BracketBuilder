import { useEffect } from "react";
import { Brain } from "lucide-react";
import { useBracket } from "../context/BracketContext";

export function Toast() {
  const { state, dismissToast } = useBracket();
  const { toastMessage } = state;

  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(dismissToast, 15000);
    return () => clearTimeout(timer);
  }, [toastMessage, dismissToast]);

  if (!toastMessage) return null;

  return (
    <div
      className="fixed bottom-24 md:bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-2xl shadow-2xl animate-in slide-in-from-bottom-4"
      style={{
        background: "rgba(0, 12, 42, 0.95)",
        border: "1px solid rgba(0, 184, 219, 0.3)",
        backdropFilter: "blur(20px)",
      }}
    >
      <div className="animate-spin">
        <Brain size={16} color="#00b8db" />
      </div>
      <span
        style={{
          fontFamily: "Rubik, sans-serif",
          fontSize: 13,
          fontWeight: 500,
          color: "rgba(255,255,255,0.9)",
        }}
      >
        {toastMessage}
      </span>
    </div>
  );
}
