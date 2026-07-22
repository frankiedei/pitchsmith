import { useEffect } from "react";
import { useStore } from "./store/store";
import { Sidebar } from "./components/Sidebar";
import { Composer } from "./components/Composer";
import { ArtistHub } from "./components/ArtistHub";

export default function App() {
  const { view, error, boot, toasts } = useStore();

  useEffect(() => {
    boot();
  }, [boot]);

  // a file dropped anywhere outside the dropzone would otherwise make the browser
  // navigate to it (leaving the app); swallow those stray drops.
  useEffect(() => {
    const stop = (e: DragEvent) => e.preventDefault();
    window.addEventListener("dragover", stop);
    window.addEventListener("drop", stop);
    return () => {
      window.removeEventListener("dragover", stop);
      window.removeEventListener("drop", stop);
    };
  }, []);

  return (
    <div className="app">
      <Sidebar />
      <main className="main-pane">
        {error && (
          <div
            className="glass card errbox"
            role="button"
            title="Click to dismiss"
            onClick={() => useStore.getState().set("error", null)}
          >
            {error}
          </div>
        )}
        {view === "compose" ? <Composer /> : <ArtistHub />}
      </main>
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast glass toast-${t.kind}`}>
            {t.msg}
          </div>
        ))}
      </div>
    </div>
  );
}
