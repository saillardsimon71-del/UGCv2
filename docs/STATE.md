# État réel — 2026-10-27

Règle : *« ça compile » ≠ « ça marche » ≠ « c'est crédible pour un spectateur ».*
Les trois niveaux sont séparés ci-dessous. Environnement de construction :
sandbox **sans GPU et sans accès Modal** — aucun rendu IA de ce dépôt n'a
encore été exécuté ni regardé. Tout ce qui suit est daté et vérifiable.

## ✅ Fonctionne et mesuré ici (CPU)

| Fonction | Preuve | Mesure |
|---|---|---|
| API complète (projets, plans, prises, assets, perso/voix, jobs, exports, coûts) | 11 tests pytest verts | ~7 s |
| Routeur de production (recette → étapes/moteurs/blocages/coût) | tests unitaires dédiés | 7 recettes, 3 qualités |
| Garde-fou dépense GPU (refus sans `confirm_spend`) | test unitaire | — |
| Analyse vidéo (probe PyAV, vignettes, noirs/figés, loudness) | test API bout-en-bout | vignettes ×6 |
| Storyboard local FR (5 plans) + branche LLM optionnelle | test API (LLM non appelé : pas de clé) | — |
| Montage ffmpeg (2 passes, xfade, ASS + SRT, loudnorm, poster) | démo + QC mesuré | 1080×1920@30, **−13,9 LUFS**, QC **8/8 pass** |
| UI React (productions, studio, bibliothèque, moteurs) | build TS strict | 181 Ko JS / 5,5 Ko CSS |
| Export de démonstration de la chaîne | `data/exports/demo_SIMULATION_chaine_studio.mp4` | 13,6 s — **100 % plaques de test étiquetées** |

## ✅ Prouvé sur GPU — dans l'ancien studio, réutilisé tel quel

- **LTX-2.5** (`pvs-ltx`, L40S) et **LongCat Avatar 1.5** (`pvs-longcat-avatar`,
  A100) ont produit de vrais MP4 sur votre compte Modal (avatar FR 720×1280,
  3,72 s ; LongCat ~308 s, LTX ~109 s à chaud). Le nouveau studio appelle ces
  mêmes apps. À re-confirmer par le workflow diagnostic (ils n'ont pas été
  re-contactés depuis ce dépôt, faute d'accès Modal ici).

## ⏳ Écrit, NON exécuté — benchmarks requis avant tout usage client

| Worker | Capacité | Premier pas |
|---|---|---|
| `deploy/modal_face_worker.py` | Face swap (FaceFusion) | diagnostic → S1 |
| `deploy/modal_lipsync_worker.py` | LatentSync 1.6 / MuseTalk | `prepare` (poids) → S2 |
| `deploy/modal_voice_worker.py` | Chatterbox V3 / Seed-VC | doctor → écoute S4 |
| `deploy/modal_perf_worker.py` | Animate 2 / SCAIL-2 / InfiniteTalk (WanGP) | `validate` (dry-run) → S3/S4 |

Points d'incertitude assumés, écrits dans les workers : clés média du
settings WanGP (validées par dry-run, pas encore fait), chemins de sortie
MuseTalk/Seed-VC (repérage par fichier le plus récent), limite pilote
LongCat 3,72 s/segment, tailles base64 du contrat v1 (clips courts).

## ❌ Volontairement pas (encore) fait

- Retake temporel fin (régénérer 2 s d'un plan) : la mécanique d'assemblage
  existe (splice hérité), pas l'UI ni le branchement moteur — après S5.
- Transfert de gros fichiers via Volume Modal (le base64 suffit aux benchmarks).
- Upscale/finition (RealESRGAN/Topaz-like open source) : à décider après S1–S3.
- Multi-utilisateur/auth : dimensionnement mono-poste assumé.

## Prochaine décision importante

Lancer le **workflow diagnostic** (secrets à ajouter par l'humain, 2 min),
puis **S3-validate** + une première voix. Ensuite seulement, juger S1/S2 à
l'œil et promouvoir les gagnants. Voir MODAL.md §3.
