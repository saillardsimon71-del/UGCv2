# Architecture

```
Navigateur ──HTTP même origine──► FastAPI (1 process)
                                     ├─ UI statique (frontend/dist)
                                     ├─ SQLite : projets, plans, prises, jobs, coûts
                                     ├─ Jobs (thread, 1 GPU à la fois, reprise au boot)
                                     ├─ CPU réel : analyse, montage ffmpeg, sous-titres, QC
                                     └─ Moteurs (contrat unique engines/base.py)
                                          ├─ locaux : analysis, ffmpeg_assembly, plaques SIMULATION
                                          └─ Modal (spawn + sondage, annulation = kill conteneur)
                                               pvs-ltx* · pvs-longcat-avatar*   (* prouvés, réutilisés)
                                               ugc-face · ugc-lipsync · ugc-voice · ugc-perf · ugc-talk
```

## Concepts produit

- **Production** = un projet + une **recette** (intention métier, jamais un
  nom de modèle) + un niveau de qualité (Brouillon / Production / Premium).
- **Routeur** (`backend/app/recipes.py`) : traduit recette + sources +
  qualité en étapes et moteurs, liste les blocages lisibles par un non-expert,
  estime le coût GPU (hypothèses étiquetées). C'est le seul endroit où vivent
  les choix par défaut — les benchmarks les font évoluer là.
- **Plan** : l'unité de travail. Porte dialogue, intention visuelle, sources,
  état, QC, revue humaine et l'historique de ses **prises**. Régénérer =
  ajouter une prise ; l'original n'est jamais écrasé. Comparaison A/B et
  notation dans l'UI ; la prise retenue alimente l'export.
- **Personnages & voix** : bibliothèque globale réutilisable entre
  productions (références + case d'autorisation d'usage).
- **QC deux niveaux, jamais confondus** : automatique (conteneur, durée,
  ratio, audio, segments noirs/figés, loudness EBU R128 — « aucun défaut
  d'emballage ») et **humain** (identité, lèvres, jeu, mains/dents) via une
  checklist par type de plan + note /5 + verdict. Livrable client seulement
  à ≥ 4/5 tout coché. Aucun modèle ne prétend juger la crédibilité.
- **Coûts** : chaque job GPU enregistre secondes et tarif, échecs inclus →
  la métrique qui compte est le **coût par vidéo acceptée**.
- **Honnêteté système** : `simulated` est une propriété de première classe
  (moteur, job, prise, export). Sans moteur réel, le studio le dit partout
  et les plaques portent un filigrane. `STUDIO_ALLOW_MOCK=0` en production.

## Exécution

- Jobs en SQLite + dispatcher thread (0,4 s) + `ThreadPoolExecutor(1)` :
  un GPU = un rendu à la fois ; annulation coopérative (et, côté Modal,
  terminaison du conteneur). Au redémarrage, les jobs `running` repartent.
- Pipelines composés dans `jobs.py` : avatar/doublage = voix (si aucun audio
  fourni — une vraie performance n'est jamais régénérée) → moteur → QC auto.
- Montage : normalisation 2 passes → xfade/concat → sous-titres ASS incrustés
  + `.srt` → lit musical optionnel → loudnorm −14 LUFS → H.264/AAC faststart.
  Le graphe ffmpeg exact est conservé avec chaque export (audit).
- Contrat Modal v1 : fichiers en base64, `spawn()` sondé, MP4 probé avant
  acceptation, timeout 35 min. Limite assumée : clips courts ; les longs
  formats passeront par un Volume Modal (roadmap).

## Ce qui vient de l'ancien studio — et ce qui n'en vient pas

Réutilisé car **prouvé** : workers Modal LTX-2.5 et LongCat (tels quels),
moteur de montage, QC, probe PyAV, patrons jobs/coûts, photo de référence
benchmark. Réécrit : produit (recettes plutôt que moteurs), données
(assets/sources, revue humaine), routeur, UI complète, et les 4 nouveaux
workers (face, lipsync, voice, perf). L'ancienne accumulation de branches
expérimentales n'a pas été importée.
