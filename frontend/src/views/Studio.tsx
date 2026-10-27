import { useCallback, useEffect, useRef, useState } from "react";
import { api, assetUrl, exportUrl, fmtUsd, takeUrl } from "../api";
import type { Character, Plan, Project, Shot, Take, Voice } from "../types";

const HUMAN_CHECKS: Record<string, string[]> = {
  avatar: ["Identité stable (visage, peau, cheveux) du début à la fin", "Lèvres synchrones, consonnes et fermetures nettes",
    "Regard, clignements et respiration naturels", "Gestuelle cohérente avec le propos (pas de photo qui parle)", "Dents/langue sans déformation visible"],
  lip_sync: ["Bouche synchronisée sur toute la durée, sans dérive", "Dents et langue crédibles aux consonnes", "Expressions compatibles avec le nouveau dialogue", "Aucun halo/flou autour de la bouche"],
  face_swap: ["Le visage semble avoir toujours été là (pas d'effet masque)", "Raccord cou/mâchoire et lumière cohérents", "Occlusions (mains, cheveux, objets) propres", "Identité constante malgré les rotations de tête"],
  person_replace: ["Morphologie et posture crédibles en mouvement", "Mains et interactions avec le décor propres", "Intégration lumière/ombre dans la scène", "Identité stable d'un bout à l'autre"],
  motion_transfer: ["Le rythme et l'intention de la référence sont respectés", "Physique crédible (contacts, poids, inertie)", "Identité stable malgré les mouvements amples"],
  voice_only: ["Diction naturelle, respirations crédibles", "Timbre stable, aucune note métallique", "Émotion et rythme justes pour l'usage"],
  b_roll: ["Respect du prompt et du cadrage", "Aucun artefact (mains, texte, morphologie)", "Lumière et textures photoréalistes"],
};

export default function Studio({ projectId, back }: { projectId: string; back: () => void }) {
  const [p, setP] = useState<Project | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [chars, setChars] = useState<Character[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [confirmSpend, setConfirmSpend] = useState(false);
  const [msg, setMsg] = useState("");
  const [compare, setCompare] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadRole, setUploadRole] = useState("video_source");

  const load = useCallback(() => {
    api.project(projectId).then(setP).catch((e) => setMsg(String(e)));
    api.plan(projectId).then(setPlan).catch(() => {});
  }, [projectId]);
  useEffect(() => { load(); api.characters().then(setChars); api.voices().then(setVoices); }, [load]);
  useEffect(() => {
    const t = setInterval(async () => {
      const js = await api.jobs().catch(() => []);
      if (js.some((j: any) => j.project_id === projectId && ["queued", "running"].includes(j.status))) load();
    }, 4000);
    return () => clearInterval(t);
  }, [load, projectId]);

  if (!p) return <p className="mut">Chargement du studio…</p>;
  const inputs = p.settings?.inputs ?? {};

  const setInput = async (key: string, value: string) => {
    await api.patchProject(p.id, { settings: { inputs: { ...inputs, [key]: value } } });
    load();
  };
  const onUpload = async (f: File) => {
    try {
      const a = await api.upload(f, p.id, uploadRole, "Source fournie par l'utilisateur (droits à confirmer dans la bibliothèque)");
      if (uploadRole === "video_source") { await setInput("video_asset_id", a.id); await api.analyse(a.id); setMsg("Vidéo importée — analyse lancée."); }
      else if (uploadRole === "audio_source") await setInput("audio_asset_id", a.id);
      load();
    } catch (e) { setMsg(String(e)); }
  };
  const generate = async (shot: Shot, engine?: string) => {
    if (plan?.requires_gpu_spend && plan.ready && !confirmSpend)
      setMsg("ℹ Ce rendu peut utiliser un GPU payant : cochez « Je confirme la dépense GPU » dans le plan de production, puis relancez.");
    await api.generate(shot.id, { engine: engine ?? null, confirm_spend: confirmSpend, seed: 42 });
    setMsg("Génération en file — suivez la progression dans la barre des jobs en bas.");
  };

  const compareTakes: Take[] = p.shots.flatMap((s) => s.takes).filter((t) => compare.includes(t.id));

  return (
    <div>
      <button className="btn ghost small" onClick={back}>← Productions</button>
      <div className="spread" style={{ marginTop: 10 }}>
        <div><h1>{p.name}</h1><p className="sub" style={{ marginBottom: 4 }}>{p.brief || "—"}</p>
          <span className="badge acc">{plan?.label ?? p.recipe}</span>{" "}
          <span className="badge">{p.format}</span>{" "}<span className="badge">Qualité : {p.quality}</span></div>
        <div className="row">
          {p.recipe === "create" && <button className="btn ghost" onClick={async () => { await api.storyboard(p.id); load(); }}>✨ Storyboard auto</button>}
          <button className="btn" onClick={async () => { await api.exportProject(p.id); setMsg("Montage/export en file."); }}>🎬 Monter & exporter</button>
        </div>
      </div>
      {msg && <div className="banner ok">{msg}</div>}

      {/* ---------- Plan de production (choix du studio, explicable) ---------- */}
      {plan && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="spread"><h3 style={{ margin: 0 }}>🧭 Plan de production — décidé par le studio</h3>
            <span className={`badge ${plan.ready ? "ok" : "warn"}`}>{plan.ready ? "Prêt à produire" : "En préparation"}</span></div>
          <ul className="steps">
            {plan.steps.map((s) => (
              <li key={s.id}>
                <span className="dot" style={{ background: s.skipped ? "#64748b" : s.available ? "var(--ok)" : "var(--bad)" }} />
                <div><b>{s.label}</b>
                  <div className="mut">{s.skipped ? s.skip_reason : s.available ? `Moteur : ${s.engine} (mode avancé ci-dessous pour changer)` : s.blocker}
                    {s.quality_note ? <><br />{s.quality_note}</> : null}</div></div>
              </li>
            ))}
          </ul>
          {plan.missing_inputs.length > 0 && <p className="mut">📥 <b>Sources manquantes :</b> {plan.missing_inputs.map((m) => m.label).join(" · ")} — importez-les ci-dessous.</p>}
          <p className="mut">Estimation (hypothèses, pas une mesure) : ~{plan.estimate.gpu_seconds} s GPU · ≈ {fmtUsd(plan.estimate.cost_usd)} pour {plan.estimate.video_seconds} s de vidéo.</p>
          {plan.requires_gpu_spend && (
            <label className="check"><input type="checkbox" checked={confirmSpend} onChange={(e) => setConfirmSpend(e.target.checked)} />
              <span><b>Je confirme la dépense GPU</b> pour les rendus de cette production (Modal, à la demande — aucun coût au repos).</span></label>
          )}
        </div>
      )}

      {/* ---------- Sources ---------- */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>📥 Sources & références</h3>
        <div className="row">
          <select value={uploadRole} onChange={(e) => setUploadRole(e.target.value)} style={{ width: 240 }}>
            <option value="video_source">Vidéo source (performance filmée)</option>
            <option value="audio_source">Audio (dialogue enregistré)</option>
            <option value="reference">Image de référence</option>
            <option value="music">Musique</option>
          </select>
          <label className="file-label">Importer un fichier<input ref={fileRef} type="file" hidden
            onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])} /></label>
          <span className="mut">Formats : MP4/MOV, PNG/JPG, WAV/MP3 — utilisez uniquement des visages/voix autorisés.</span>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <div style={{ minWidth: 240 }}><label>Personnage du projet</label>
            <select value={inputs.character_id ?? ""} onChange={(e) => setInput("character_id", e.target.value)}>
              <option value="">— aucun —</option>
              {chars.map((c) => <option key={c.id} value={c.id}>{c.name}{c.consent ? "" : " (consentement non coché !)"}</option>)}
            </select></div>
          <span className="mut">Créez les personnages et voix dans la Bibliothèque (photo/audio de référence réutilisables).</span>
        </div>
        {p.assets.length > 0 && (
          <table><thead><tr><th>Fichier</th><th>Rôle</th><th>Analyse</th><th></th></tr></thead>
            <tbody>{p.assets.map((a) => (
              <tr key={a.id}><td>{a.name}<div className="mut">{a.kind}</div></td><td>{a.role}</td>
                <td className="mut">{a.meta.analysis?.media
                  ? `${a.meta.analysis.media.width}x${a.meta.analysis.media.height} · ${Number(a.meta.analysis.media.duration_s).toFixed(1)}s` +
                    ((a.meta.analysis.warnings ?? []).length ? ` ⚠ ${a.meta.analysis.warnings!.join(" ")}` : " ✓")
                  : "—"}</td>
                <td className="row"><a href={assetUrl(a.id)} target="_blank" rel="noreferrer">voir</a>
                  {a.kind === "video" && <button className="btn ghost small" onClick={() => setInput("video_asset_id", a.id)}>Source vidéo</button>}
                  {a.kind === "audio" && <button className="btn ghost small" onClick={() => setInput("audio_asset_id", a.id)}>Audio dialogue</button>}
                  {a.kind === "video" && <button className="btn ghost small" onClick={async () => { await api.analyse(a.id); setMsg("Analyse relancée."); }}>Analyser</button>}
                </td></tr>))}
            </tbody></table>
        )}
      </div>

      {/* ---------- Comparaison A/B ---------- */}
      {compareTakes.length === 2 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="spread"><h3 style={{ margin: 0 }}>⚖️ Comparaison de prises</h3>
            <button className="btn ghost small" onClick={() => setCompare([])}>Fermer</button></div>
          <div className="compare-grid">
            {compareTakes.map((t) => (
              <div key={t.id}><p className="mut">{t.meta.engine ?? "prise"} {t.meta.simulated && <span className="badge sim">SIMULATION</span>}</p>
                <video src={takeUrl(t.id)} controls /></div>
            ))}
          </div>
          <p className="mut">Regardez en plein écran : visage, lèvres, dents, mains, raccords. Sélectionnez ensuite la meilleure prise dans son plan.</p>
        </div>
      )}

      {/* ---------- Plans ---------- */}
      <h2>🎞️ Plans ({p.shots.length})</h2>
      {p.shots.map((s) => (
        <ShotCard key={s.id} shot={s} chars={chars} voices={voices} reload={load}
          onGenerate={(eng) => generate(s, eng)}
          compare={compare} toggleCompare={(id) => setCompare((c) => c.includes(id) ? c.filter((x) => x !== id) : [...c.slice(-1), id])} />
      ))}
      <button className="btn ghost" onClick={async () => {
        await api.addShot(p.id, { title: `Plan ${p.shots.length + 1}`, kind: p.shots[0]?.kind ?? "b_roll", duration_s: 5 });
        load();
      }}>＋ Ajouter un plan</button>

      {/* ---------- Exports ---------- */}
      <h2>📦 Exports</h2>
      {p.exports.length === 0 && <p className="mut">Aucun export. Générez au moins un plan, sélectionnez la meilleure prise, puis « Monter & exporter ».</p>}
      <div className="grid">
        {p.exports.map((e) => (
          <div key={e.id} className="card">
            <video src={exportUrl(e.id)} controls />
            <div className="row" style={{ marginTop: 8 }}>
              <span className={`badge ${e.qc.verdict === "pass" ? "ok" : "warn"}`}>QC emballage : {e.qc.verdict ?? "?"}</span>
              {e.spec.contains_simulation && <span className="badge sim">Contient des simulations</span>}
              <a className="btn small" href={exportUrl(e.id)} download>Télécharger le MP4</a>
            </div>
            <p className="mut">Le QC automatique vérifie le conteneur (format, durée, audio, noirs, loudness) — jamais la crédibilité du jeu. Visionnez avant toute livraison client.</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ShotCard({ shot, chars, voices, reload, onGenerate, compare, toggleCompare }: {
  shot: Shot; chars: Character[]; voices: Voice[]; reload: () => void;
  onGenerate: (engine?: string) => Promise<void>; compare: string[]; toggleCompare: (id: string) => void;
}) {
  const [local, setLocal] = useState(shot);
  const [engine, setEngine] = useState("");
  const [review, setReview] = useState(shot.human_review ?? {});
  useEffect(() => { setLocal(shot); setReview(shot.human_review ?? {}); }, [shot]);
  const save = async (patch: Partial<Shot>) => { await api.patchShot(shot.id, patch); reload(); };
  const checks = HUMAN_CHECKS[shot.kind] ?? HUMAN_CHECKS.b_roll;
  const videos = shot.takes.filter((t) => t.kind === "video");
  const audios = shot.takes.filter((t) => t.kind === "audio");

  return (
    <div className="shot">
      <div className="spread">
        <div className="row">
          <span className="badge acc">PLAN {String(shot.idx + 1).padStart(2, "0")}</span>
          <input style={{ width: 190 }} value={local.title} onChange={(e) => setLocal({ ...local, title: e.target.value })}
                 onBlur={() => save({ title: local.title })} />
          <span className={`badge ${shot.status === "generated" ? "ok" : ""}`}>{shot.status}</span>
          {shot.qc.verdict && <span className={`badge ${shot.qc.verdict === "pass" ? "ok" : "warn"}`}>QC {shot.qc.verdict}</span>}
        </div>
        <div className="row">
          <button className="btn small" onClick={() => onGenerate(engine || undefined)}>▶ Générer ce plan</button>
          <button className="btn danger small" onClick={async () => { await api.deleteShot(shot.id); reload(); }}>Supprimer</button>
        </div>
      </div>

      <div className="row" style={{ alignItems: "flex-end" }}>
        <div style={{ flex: 2, minWidth: 260 }}><label>Dialogue (texte à dire — laissez vide si audio importé)</label>
          <textarea rows={2} value={local.dialogue} onChange={(e) => setLocal({ ...local, dialogue: e.target.value })}
                    onBlur={() => save({ dialogue: local.dialogue })} /></div>
        <div style={{ flex: 2, minWidth: 260 }}><label>Intention visuelle (prompt)</label>
          <textarea rows={2} value={local.prompt} onChange={(e) => setLocal({ ...local, prompt: e.target.value })}
                    onBlur={() => save({ prompt: local.prompt })} /></div>
        <div style={{ width: 110 }}><label>Durée (s)</label>
          <input type="number" step="0.5" min="1" max="60" value={local.duration_s}
                 onChange={(e) => setLocal({ ...local, duration_s: Number(e.target.value) })}
                 onBlur={() => save({ duration_s: local.duration_s })} /></div>
        <div style={{ width: 180 }}><label>Personnage</label>
          <select value={local.character_id ?? ""} onChange={(e) => save({ character_id: e.target.value || null })}>
            <option value="">(celui du projet)</option>
            {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select></div>
        <div style={{ width: 180 }}><label>Voix</label>
          <select value={local.voice_id ?? ""} onChange={(e) => save({ voice_id: e.target.value || null })}>
            <option value="">(par défaut)</option>
            {voices.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select></div>
      </div>

      <details style={{ marginTop: 8 }}>
        <summary className="mut">Mode avancé — forcer un moteur (sinon le studio choisit)</summary>
        <div className="row" style={{ marginTop: 8 }}>
          <input style={{ width: 280 }} placeholder="ex. modal_scail2, modal_musetalk…" value={engine} onChange={(e) => setEngine(e.target.value)} />
          <span className="mut">Voir l'onglet « Moteurs & coûts » pour les noms et leur état de validation. Utile pour comparer deux moteurs sur le même plan (benchmarks).</span>
        </div>
      </details>

      {audios.length > 0 && <div style={{ marginTop: 10 }}>{audios.map((t) => (
        <div key={t.id}><span className="mut">🔊 Voix — {t.meta.engine} {t.meta.simulated && <span className="badge sim">SIMULATION</span>}</span>
          <audio src={takeUrl(t.id)} controls /></div>))}</div>}

      {videos.length > 0 && (
        <>
          <h3>Prises ({videos.length}) — comparez, notez, gardez la meilleure</h3>
          <div className="takes">
            {videos.map((t) => (
              <div key={t.id} className={`take ${shot.selected_artifact === t.id ? "selected" : ""} ${compare.includes(t.id) ? "compare" : ""}`}>
                <video src={takeUrl(t.id)} controls preload="metadata" />
                <div className="mut">{t.meta.engine ?? "?"} {t.meta.simulated && <span className="badge sim">SIMULATION</span>}</div>
                <div className="stars">{[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} className={t.rating >= n ? "on" : ""} onClick={async () => { await api.rate(t.id, n); reload(); }}>★</button>))}
                </div>
                <div className="row">
                  <button className="btn ghost small" onClick={() => save({ selected_artifact: t.id })}>
                    {shot.selected_artifact === t.id ? "✓ Retenue" : "Retenir"}</button>
                  <button className="btn ghost small" onClick={() => toggleCompare(t.id)}>Comparer</button>
                </div>
              </div>
            ))}
          </div>

          <details style={{ marginTop: 12 }}>
            <summary><b>👁 Revue humaine</b> — la vraie question : un spectateur y croirait-il au premier visionnage ?</summary>
            <div style={{ marginTop: 8 }}>
              {checks.map((c) => (
                <label key={c} className="check">
                  <input type="checkbox" checked={!!review.checks?.[c]}
                    onChange={(e) => setReview({ ...review, checks: { ...(review.checks ?? {}), [c]: e.target.checked } })} />
                  <span>{c}</span></label>
              ))}
              <div className="row" style={{ alignItems: "flex-end" }}>
                <div style={{ width: 170 }}><label>Note globale /5</label>
                  <select value={review.score ?? ""} onChange={(e) => setReview({ ...review, score: Number(e.target.value) })}>
                    <option value="">—</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}/5</option>)}
                  </select></div>
                <div style={{ width: 200 }}><label>Verdict</label>
                  <select value={review.verdict ?? ""} onChange={(e) => setReview({ ...review, verdict: e.target.value })}>
                    <option value="">À juger</option><option value="accepted">✅ Livrable client</option>
                    <option value="rework">🔁 À reprendre</option><option value="rejected">❌ Rejeté</option>
                  </select></div>
                <div style={{ flex: 1, minWidth: 220 }}><label>Défauts observés (précis : à 0:03, la main…)</label>
                  <input value={review.notes ?? ""} onChange={(e) => setReview({ ...review, notes: e.target.value })} /></div>
                <button className="btn ghost small" onClick={() => save({ human_review: review } as Partial<Shot>)}>Enregistrer la revue</button>
              </div>
              <p className="mut">Critère du studio : livrable seulement à ≥ 4/5 avec toutes les cases cochées. En dessous : régénérez le plan (autre moteur en mode avancé) plutôt que tout le film.</p>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
