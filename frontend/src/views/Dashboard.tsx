import { useEffect, useState } from "react";
import { api, fmtDate } from "../api";
import type { Project, Recipe } from "../types";

const RECIPE_ORDER = ["avatar", "dub", "face_swap", "person_replace", "motion_transfer", "voice_only", "create"];

export default function Dashboard({ open }: { open: (id: string) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [wizard, setWizard] = useState(false);
  const [sel, setSel] = useState("avatar");
  const [name, setName] = useState("");
  const [brief, setBrief] = useState("");
  const [format, setFormat] = useState("9:16");
  const [quality, setQuality] = useState("production");
  const [err, setErr] = useState("");

  const load = () => {
    api.projects().then(setProjects).catch((e) => setErr(String(e)));
    api.recipes().then((r) => setRecipes(r.recipes)).catch(() => {});
  };
  useEffect(load, []);

  const create = async () => {
    try {
      const p = await api.createProject({ name: name || "Sans titre", brief, recipe: sel, format, quality });
      setWizard(false); open(p.id);
    } catch (e) { setErr(String(e)); }
  };

  const byId = (id: string) => recipes.find((r) => r.id === id);

  return (
    <div>
      <div className="spread">
        <div>
          <h1>Productions</h1>
          <p className="sub">Commandez une vidéo — le studio choisit la méthode. Partez d'une vraie
            performance filmée quand vous l'avez : c'est presque toujours le chemin le plus crédible.</p>
        </div>
        <button className="btn" onClick={() => setWizard(true)}>＋ Nouvelle production</button>
      </div>
      {err && <div className="banner">⚠ {err}</div>}

      {projects.length === 0 && (
        <div className="card">
          <h3>Aucune production pour l'instant</h3>
          <p className="mut">Créez votre première production : choisissez ce que vous voulez obtenir
            (avatar parlant, nouveau dialogue sur une vidéo existante, remplacement de visage…),
            importez vos sources, puis générez plan par plan et gardez les meilleures prises.</p>
          <button className="btn" onClick={() => setWizard(true)}>Démarrer</button>
        </div>
      )}

      <div className="grid">
        {projects.map((p) => (
          <div key={p.id} className="card clickable" onClick={() => open(p.id)}>
            <div className="spread">
              <span className="recipe-icon">{byId(p.recipe)?.icon ?? "🎬"}</span>
              <span className="badge">{byId(p.recipe)?.label ?? p.recipe}</span>
            </div>
            <h3>{p.name}</h3>
            <p className="mut">{p.brief.slice(0, 140) || "—"}</p>
            <div className="row mut">
              <span>{p.shots_count ?? 0} plan(s)</span>·<span>{p.exports_count ?? 0} export(s)</span>·
              <span>{p.format}</span>·<span>{fmtDate(p.created_at)}</span>
            </div>
          </div>
        ))}
      </div>

      {wizard && (
        <div className="modal-bg" onClick={() => setWizard(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="spread"><h2 style={{ margin: 0 }}>Que voulez-vous produire ?</h2>
              <button className="btn ghost small" onClick={() => setWizard(false)}>✕</button></div>
            <div className="grid" style={{ marginTop: 16 }}>
              {RECIPE_ORDER.map((id) => byId(id)).filter(Boolean).map((r) => (
                <div key={r!.id} className="card clickable" onClick={() => setSel(r!.id)}
                     style={sel === r!.id ? { borderColor: "var(--acc)", outline: "2px solid var(--acc)" } : {}}>
                  <span className="recipe-icon">{r!.icon}</span>
                  <h3>{r!.label}</h3>
                  <p className="mut">{r!.promise}</p>
                  <p className="mut"><b>Il vous faudra :</b> {r!.needs.map((n) => r!.needs_labels[n]).join(" · ")}</p>
                </div>
              ))}
            </div>
            <label>Titre de la production</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex. UGC café — version FR" />
            <label>Brief / intention (décrivez simplement le résultat voulu)</label>
            <textarea rows={3} value={brief} onChange={(e) => setBrief(e.target.value)}
              placeholder="Ex. Léa présente notre torréfaction, ton complice, 30 secondes pour TikTok…" />
            <div className="row">
              <div style={{ flex: 1 }}><label>Format</label>
                <select value={format} onChange={(e) => setFormat(e.target.value)}>
                  <option value="9:16">9:16 — vertical (TikTok, Reels, Shorts)</option>
                  <option value="16:9">16:9 — horizontal</option>
                  <option value="1:1">1:1 — carré</option>
                </select></div>
              <div style={{ flex: 1 }}><label>Niveau de qualité (choix du moteur, automatique)</label>
                <select value={quality} onChange={(e) => setQuality(e.target.value)}>
                  <option value="brouillon">Brouillon — rapide, valider l'idée</option>
                  <option value="production">Production — équilibre qualité/coût</option>
                  <option value="premium">Premium — meilleur moteur, plans héros</option>
                </select></div>
            </div>
            <div className="row" style={{ marginTop: 16 }}>
              <button className="btn" onClick={create}>Créer et ouvrir le studio →</button>
              <span className="mut">Aucune dépense GPU à cette étape.</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
