// Toutes les requêtes sont relatives : en dev Vite proxifie /api vers le
// backend, en production le même process sert UI + API. Jamais de localhost.
async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`${r.status} ${txt.slice(0, 300)}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  system: () => req<any>("/api/system"),
  recipes: () => req<any>("/api/recipes"),
  projects: () => req<any[]>("/api/projects"),
  project: (id: string) => req<any>(`/api/projects/${id}`),
  createProject: (b: unknown) => req<any>("/api/projects", { method: "POST", body: JSON.stringify(b) }),
  patchProject: (id: string, b: unknown) => req<any>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
  deleteProject: (id: string) => req<any>(`/api/projects/${id}`, { method: "DELETE" }),
  plan: (id: string) => req<any>(`/api/projects/${id}/plan`),
  costs: (id: string) => req<any>(`/api/projects/${id}/costs`),
  storyboard: (id: string) => req<any>(`/api/projects/${id}/storyboard`, { method: "POST" }),
  addShot: (pid: string, b: unknown) => req<any>(`/api/projects/${pid}/shots`, { method: "POST", body: JSON.stringify(b) }),
  patchShot: (sid: string, b: unknown) => req<any>(`/api/shots/${sid}`, { method: "PATCH", body: JSON.stringify(b) }),
  deleteShot: (sid: string) => req<any>(`/api/shots/${sid}`, { method: "DELETE" }),
  generate: (sid: string, b: unknown) => req<any>(`/api/shots/${sid}/generate`, { method: "POST", body: JSON.stringify(b) }),
  exportProject: (pid: string) => req<any>(`/api/projects/${pid}/export`, { method: "POST", body: "{}" }),
  jobs: () => req<any[]>("/api/jobs?limit=30"),
  job: (id: string) => req<any>(`/api/jobs/${id}`),
  cancelJob: (id: string) => req<any>(`/api/jobs/${id}/cancel`, { method: "POST" }),
  rate: (aid: string, rating: number) => req<any>(`/api/artifacts/${aid}/rate`, { method: "POST", body: JSON.stringify({ rating }) }),
  assets: () => req<any[]>("/api/assets"),
  analyse: (aid: string) => req<any>(`/api/assets/${aid}/analyse`, { method: "POST" }),
  characters: () => req<any[]>("/api/characters"),
  createCharacter: (b: unknown) => req<any>("/api/characters", { method: "POST", body: JSON.stringify(b) }),
  deleteCharacter: (id: string) => req<any>(`/api/characters/${id}`, { method: "DELETE" }),
  voices: () => req<any[]>("/api/voices"),
  createVoice: (b: unknown) => req<any>("/api/voices", { method: "POST", body: JSON.stringify(b) }),
  deleteVoice: (id: string) => req<any>(`/api/voices/${id}`, { method: "DELETE" }),
  upload: async (file: File, projectId = "", role = "source", rightsNote = "") => {
    const fd = new FormData();
    fd.append("file", file); fd.append("project_id", projectId);
    fd.append("role", role); fd.append("rights_note", rightsNote);
    const r = await fetch("/api/assets/upload", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

export const assetUrl = (id: string) => `/api/assets/${id}/file`;
export const takeUrl = (id: string) => `/api/artifacts/${id}/file`;
export const exportUrl = (id: string) => `/api/exports/${id}/file`;

export const fmtUsd = (n: number) => (n < 0.01 && n > 0 ? "< 0,01 $" : `${n.toFixed(2)} $`);
export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
