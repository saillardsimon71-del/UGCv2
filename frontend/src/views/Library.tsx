import { useEffect, useState } from "react";
import { api, assetUrl } from "../api";
import type { Asset, Character, Voice } from "../types";

export default function Library() {
  const [chars, setChars] = useState<Character[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [cName, setCName] = useState(""); const [cConsent, setCConsent] = useState(false);
  const [vName, setVName] = useState(""); const [vConsent, setVConsent] = useState(false);
  const [msg, setMsg] = useState("");

  const load = () => { api.characters().then(setChars); api.voices().then(setVoices); api.assets().then(setAssets); };
  useEffect(load, []);
  const images = assets.filter((a) => a.kind === "image");
  const audios = assets.filter((a) => a.kind === "audio");

  const uploadFor = async (f: File, kind: "char" | "voice") => {
    try {
      await api.upload(f, "", kind === "char" ? "character_ref" : "voice_ref", "Référence fournie par l'utilisateur");
      setMsg("Fichier importé — sélectionnez-le ci-dessous puis créez la fiche."); load();
    } catch (e) { setMsg(String(e)); }
  };

  return (
    <div>
      <h1>Bibliothèque — personnages & voix</h1>
      <p className="sub">Vos identités réutilisables d'une production à l'autre. Une bonne référence vaut
        mieux que dix réglages : visage net, lumière franche, plusieurs angles si possible ;
        voix propre, 10–30 s sans musique. <b>N'utilisez que des visages et voix autorisés</b> (les vôtres,
        ceux d'acteurs consentants, ou des personnages synthétiques).</p>
      {msg && <div className="banner ok">{msg}</div>}

      <h2>👤 Personnages</h2>
      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 180 }}><label>Nom</label>
            <input value={cName} onChange={(e) => setCName(e.target.value)} placeholder="Ex. Léa (présentatrice café)" /></div>
          <label className="file-label">Importer une photo<input type="file" hidden accept="image/*"
            onChange={(e) => e.target.files?.[0] && uploadFor(e.target.files[0], "char")} /></label>
          <label className="check"><input type="checkbox" checked={cConsent} onChange={(e) => setCConsent(e.target.checked)} />
            <span>Je confirme avoir l'autorisation d'utiliser ce visage</span></label>
          <button className="btn small" disabled={!cName} onClick={async () => {
            await api.createCharacter({ name: cName, ref_asset_id: images[images.length - 1]?.id ?? null, consent: cConsent });
            setCName(""); setCConsent(false); load();
          }}>Créer avec la dernière photo importée</button>
        </div>
      </div>
      <div className="grid">
        {chars.map((c) => (
          <div key={c.id} className="card">
            {c.ref_asset_id && <img src={assetUrl(c.ref_asset_id)} alt={c.name} style={{ width: "100%", borderRadius: 10, maxHeight: 260, objectFit: "cover" }} />}
            <h3>{c.name}</h3>
            <span className={`badge ${c.consent ? "ok" : "bad"}`}>{c.consent ? "Autorisation confirmée" : "Autorisation NON confirmée"}</span>{" "}
            <button className="btn danger small" onClick={async () => { await api.deleteCharacter(c.id); load(); }}>Supprimer</button>
            {!c.ref_asset_id && <p className="mut">Aucune photo — importez-en une puis recréez la fiche.</p>}
          </div>
        ))}
      </div>
      {chars.length === 0 && <p className="mut">Aucun personnage. Astuce qualité : photo verticale, visage occupant ~1/3 du cadre, regard proche caméra, pas de filtre beauté.</p>}

      <h2>🗣️ Voix</h2>
      <div className="card" style={{ marginBottom: 14 }}>
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 180 }}><label>Nom</label>
            <input value={vName} onChange={(e) => setVName(e.target.value)} placeholder="Ex. Voix de Léa — FR" /></div>
          <label className="file-label">Importer un audio (10–30 s propre)<input type="file" hidden accept="audio/*"
            onChange={(e) => e.target.files?.[0] && uploadFor(e.target.files[0], "voice")} /></label>
          <label className="check"><input type="checkbox" checked={vConsent} onChange={(e) => setVConsent(e.target.checked)} />
            <span>Je confirme avoir l'autorisation d'utiliser cette voix</span></label>
          <button className="btn small" disabled={!vName} onClick={async () => {
            await api.createVoice({ name: vName, ref_asset_id: audios[audios.length - 1]?.id ?? null, consent: vConsent });
            setVName(""); setVConsent(false); load();
          }}>Créer avec le dernier audio importé</button>
        </div>
      </div>
      <div className="grid">
        {voices.map((v) => (
          <div key={v.id} className="card">
            <h3>{v.name}</h3>
            {v.ref_asset_id && <audio src={assetUrl(v.ref_asset_id)} controls />}
            <div style={{ marginTop: 8 }}><span className={`badge ${v.consent ? "ok" : "bad"}`}>{v.consent ? "Autorisation confirmée" : "Autorisation NON confirmée"}</span>{" "}<span className="badge">{v.language}</span>{" "}
            <button className="btn danger small" onClick={async () => { await api.deleteVoice(v.id); load(); }}>Supprimer</button></div>
          </div>
        ))}
      </div>
      {voices.length === 0 && <p className="mut">Aucune voix. Deux stratégies : <b>synthèse clonée</b> (texte → votre timbre) ou <b>conversion</b> (vous jouez la scène, on change le timbre en gardant votre jeu — souvent plus naturel).</p>}
    </div>
  );
}
