import { useEffect, useState } from "react";
import { api } from "../api";
import type { EngineInfo } from "../types";

const MATURITY: Record<string, { label: string; cls: string }> = {
  production: { label: "✅ Production (prouvé)", cls: "ok" },
  benchmark_passed: { label: "Benchmark passé", cls: "ok" },
  benchmark_planned: { label: "⏳ Benchmark à exécuter", cls: "warn" },
  unverified: { label: "Non vérifié", cls: "" },
};

const BENCHMARKS = [
  { id: "S1", title: "Remplacement de visage", recipe: "face_swap",
    proto: "Vidéo 10 s face caméra + 3/4 + main devant le visage. FaceFusion vs Animate 2 (remplacement).",
    crit: "Identité, raccord cou, occlusions, « effet masque » absent. Seuil : ≥4/5 en revue aveugle." },
  { id: "S2", title: "Nouveau dialogue (doublage)", recipe: "dub",
    proto: "Vidéo de parole 12 s, nouveau texte FR avec consonnes dures (b, m, p, f). MuseTalk (brouillon) vs LatentSync 1.6.",
    crit: "Sync sur toute la durée, dents/langue, pas de halo buccal. Mesurer aussi le temps de rendu/s." },
  { id: "S3", title: "Remplacement de personne / transfert", recipe: "person_replace",
    proto: "Performance 8 s : marche + geste + saisie d'objet. Animate 2 vs SCAIL-2, même photo de personnage.",
    crit: "Mains, contacts objet, morphologie, intégration décor/lumière." },
  { id: "S4", title: "Avatar parlant", recipe: "avatar",
    proto: "Photo + 20 s de voix FR (3 plans enchaînés si limite pilote). LongCat 1.5 vs InfiniteTalk.",
    crit: "Naturel du jeu (regard, respiration, gestuelle), lip-sync, stabilité d'identité sur la durée." },
  { id: "S5", title: "Publicité complète 30 s", recipe: "create + avatar",
    proto: "Storyboard 5 plans mêlant avatar + plans générés + source réelle transformée, montage studio.",
    crit: "Test spectateur : crédible au premier visionnage ? Coût par vidéo acceptée (échecs inclus)." },
];

export default function System() {
  const [sys, setSys] = useState<{ engines: EngineInfo[]; blockers: string[]; ffmpeg: string; modal_enabled: boolean } | null>(null);
  useEffect(() => { api.system().then(setSys).catch(() => {}); }, []);
  if (!sys) return <p className="mut">Chargement…</p>;
  const real = sys.engines.filter((e) => !e.simulated);
  const sims = sys.engines.filter((e) => e.simulated);

  return (
    <div>
      <h1>Moteurs & coûts</h1>
      <p className="sub">Vous n'avez pas besoin de cette page pour produire — elle sert à savoir
        <b> honnêtement</b> ce qui est prouvé, ce qui reste à valider sur GPU, et ce que ça coûte.
        Un moteur « branché » qui n'a jamais rendu une vidéo jugée à l'œil n'est pas un moteur de production.</p>

      {sys.blockers.map((b, i) => <div key={i} className="banner">⚠ {b}</div>)}
      <p className="mut">{sys.ffmpeg} · Modal {sys.modal_enabled ? "activé" : "désactivé (aucun coût GPU possible)"}</p>

      <h2>Moteurs réels</h2>
      <div className="card"><table>
        <thead><tr><th>Moteur</th><th>Rôle</th><th>GPU</th><th>Validation</th><th>État ici</th></tr></thead>
        <tbody>{real.map((e) => (
          <tr key={e.name}><td><b>{e.label}</b><div className="mut">{e.name}</div></td>
            <td>{e.kind}</td><td>{e.gpu}</td>
            <td><span className={`badge ${MATURITY[e.maturity]?.cls}`}>{MATURITY[e.maturity]?.label ?? e.maturity}</span></td>
            <td>{e.available ? <span className="badge ok">Disponible</span> : <span className="mut">{e.unavailable_reason}</span>}</td></tr>
        ))}</tbody></table></div>

      <h2>Scènes de référence (benchmarks)</h2>
      <p className="sub">Chaque capacité doit gagner sa place en production sur ces scènes courtes et
        comparables — sources et résultats conservés côte à côte, judged à l'œil (voir docs/BENCHMARKS.md).
        Protocole : créer une production par scène, générer avec les deux moteurs (mode avancé), comparer A/B, noter.</p>
      <div className="grid">
        {BENCHMARKS.map((b) => (
          <div key={b.id} className="card">
            <span className="badge acc">{b.id}</span> <span className="badge warn">À exécuter sur GPU</span>
            <h3>{b.title}</h3><p className="mut"><b>Protocole :</b> {b.proto}</p>
            <p className="mut"><b>Critères :</b> {b.crit}</p>
          </div>
        ))}
      </div>

      <h2>Simulations (plaques de test)</h2>
      <p className="mut">{sims.length} moteur(s) de simulation : ils valident la chaîne studio
        (jobs, montage, sous-titres, QC, export) sans aucun modèle IA. Leurs sorties portent
        toujours le filigrane SIMULATION et un badge dans l'interface. En production client :
        lancer le serveur avec <code>STUDIO_ALLOW_MOCK=0</code> pour les interdire.</p>

      <h2>Activer les vrais rendus GPU (Modal)</h2>
      <div className="card">
        <ol style={{ lineHeight: 1.9 }}>
          <li>Ajouter les secrets Modal au dépôt GitHub <b>UGCv2</b> (Settings → Secrets → Actions) : <code>MODAL_TOKEN_ID</code> et <code>MODAL_TOKEN_SECRET</code> — les mêmes que l'ancien studio.</li>
          <li>Lancer le workflow <b>« Modal — diagnostic (0 GPU) »</b> : vérifie le compte et les modèles sans dépenser.</li>
          <li>Déployer les nouveaux workers un par un (face, lipsync, perf, voice) via le workflow <b>« Modal — benchmark »</b> en commençant par la scène S1/S2, <code>confirm_spend: oui</code>.</li>
          <li>Sur la machine qui sert le studio : <code>STUDIO_MODAL_ENABLED=1</code> + jeton Modal local, puis cocher la confirmation de dépense dans le plan de production.</li>
        </ol>
        <p className="mut">Détail pas à pas (iPhone inclus), garde-fous et coûts : <b>docs/MODAL.md</b> dans le dépôt.
          Les moteurs LTX-2.5 et LongCat Avatar sont déjà déployés et prouvés sur votre compte Modal : aucune réinstallation nécessaire.</p>
      </div>
    </div>
  );
}
