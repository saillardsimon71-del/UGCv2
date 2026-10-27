import { useEffect, useState } from "react";
import { api } from "./api";
import type { Job } from "./types";
import Dashboard from "./views/Dashboard";
import Library from "./views/Library";
import Studio from "./views/Studio";
import System from "./views/System";

type View = { kind: "home" } | { kind: "project"; id: string } | { kind: "library" } | { kind: "system" };

export default function App() {
  const [view, setView] = useState<View>({ kind: "home" });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [noReal, setNoReal] = useState(false);
  const [openLog, setOpenLog] = useState<string | null>(null);
  const [logText, setLogText] = useState("");

  useEffect(() => {
    api.system().then((s) => setNoReal((s.blockers ?? []).some((b: string) => b.includes("Aucun moteur IA réel")))).catch(() => {});
    const load = () => api.jobs().then(setJobs).catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const active = jobs.filter((j) => ["queued", "running"].includes(j.status));
  const recent = jobs.slice(0, 4);

  const showLog = async (id: string) => {
    if (openLog === id) { setOpenLog(null); return; }
    const j = await api.job(id);
    setLogText((j.log ?? []).join("\n") || "(log en mémoire du process serveur — vide après redémarrage)");
    setOpenLog(id);
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="logo">Studio <span>UGC v2</span></div>
        <button className={`navbtn ${view.kind === "home" || view.kind === "project" ? "active" : ""}`} onClick={() => setView({ kind: "home" })}>🎬 Productions</button>
        <button className={`navbtn ${view.kind === "library" ? "active" : ""}`} onClick={() => setView({ kind: "library" })}>👤 Personnages & voix</button>
        <button className={`navbtn ${view.kind === "system" ? "active" : ""}`} onClick={() => setView({ kind: "system" })}>⚙️ Moteurs & coûts</button>
        <div style={{ marginTop: "auto" }} className="mut">
          <p>On commande une vidéo,<br />pas un pipeline.</p>
          <p>GPU : Modal à la demande<br />(0 € au repos).</p>
        </div>
      </aside>

      <main className="main">
        {noReal && (
          <div className="banner">🧪 <b>Mode atelier (sans GPU)</b> — import, analyse, montage, sous-titres, QC et exports sont
            100 % réels ; les « générations » IA produisent des plaques <b>SIMULATION</b> tant que Modal n'est pas activé
            (voir <b>Moteurs & coûts</b>). Aucune de ces plaques n'est présentable à un client.</div>
        )}
        {view.kind === "home" && <Dashboard open={(id) => setView({ kind: "project", id })} />}
        {view.kind === "project" && <Studio projectId={view.id} back={() => setView({ kind: "home" })} />}
        {view.kind === "library" && <Library />}
        {view.kind === "system" && <System />}

        {(active.length > 0 || recent.length > 0) && (
          <div className="card jobsbar">
            <div className="spread"><b>⚙ Travaux {active.length ? `(${active.length} en cours)` : ""}</b>
              <span className="mut">Un seul GPU à la fois — les jobs se succèdent.</span></div>
            {recent.map((j) => (
              <div key={j.id} className="row" style={{ marginTop: 6 }}>
                <span className={`badge ${j.status === "succeeded" ? "ok" : j.status === "failed" ? "bad" : "warn"}`}>{j.status}</span>
                <span>{j.type} · {j.engine}</span>
                {j.simulated === 1 && <span className="badge sim">SIMULATION</span>}
                {["queued", "running"].includes(j.status) && <progress value={j.progress} max={1} />}
                <span className="mut">{j.stage}</span>
                {j.error && !["queued", "running"].includes(j.status) && <span className="mut" style={{ maxWidth: 420 }}>{j.error.slice(0, 160)}</span>}
                <button className="btn ghost small" onClick={() => showLog(j.id)}>Log</button>
                {["queued", "running"].includes(j.status) && <button className="btn danger small" onClick={() => api.cancelJob(j.id)}>Annuler</button>}
              </div>
            ))}
            {openLog && <div className="logbox" style={{ marginTop: 10 }}>{logText}</div>}
          </div>
        )}
      </main>
    </div>
  );
}
