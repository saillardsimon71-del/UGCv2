# Décisions moteurs — octobre 2026

Ce document est une **décision argumentée**, pas un catalogue. Pour chaque
capacité du brief : le moteur retenu en production, le challenger mesuré en
benchmark, et pourquoi. Règle du studio : un moteur n'entre en « production »
qu'après avoir gagné sa scène de référence à l'œil (voir BENCHMARKS.md).
Tant que ce n'est pas fait, son statut honnête est `benchmark_planned`.

## Principe directeur

> Partir d'une vraie performance filmée quand elle existe, ne remplacer que
> ce qui doit l'être. Générer de zéro est le dernier recours, pas le défaut.

Conséquence pratique : les moteurs de **transformation** (face swap, lip-sync,
conversion de voix, remplacement de personne) sont le cœur du studio ; la
génération texte→vidéo sert les plans sans source filmée.

## Décision en une page

| Capacité (brief) | Production retenue | Challenger / brouillon | État réel |
|---|---|---|---|
| A. Remplacement de visage | **FaceFusion** (swap + restauration GFPGAN) | Animate 2 mode remplacement (premium, occlusions) | Worker écrit, benchmark S1 à exécuter |
| B. Remplacement de personne | **Wan2.2 Animate 2** via WanGP headless | **SCAIL-2** via WanGP | Worker + validate écrits, S3 à exécuter |
| C. Transfert de mouvement | **Animate 2** mode animation | SCAIL-2 end-to-end | Idem S3 |
| D. Synchronisation labiale | **LatentSync 1.6** (512 px) | MuseTalk 1.5 = brouillon rapide | Worker écrit, S2 à exécuter |
| E. Voix — synthèse | **Chatterbox Multilingue V3** | (VoxCPM2/Qwen3-TTS plus tard si besoin) | Parcours validé dans le studio précédent ; worker à ré-écouter en S4 |
| E. Voix — conversion | **Seed-VC** (garde le jeu, change le timbre) | — | Worker écrit, écoute S4 |
| F. Avatar parlant | **LongCat Avatar 1.5** | InfiniteTalk (dublage vidéo long) | **LongCat prouvé sur notre Modal** (MP4 FR 720×1280) ; limite pilote 3,72 s/segment à dépasser en S4 |
| H. Création de zéro | **LTX-2.5** (plans) + storyboard + montage studio | MiniMax H3 (existant dans l'ancien studio) | **LTX prouvé sur notre Modal** |
| Substrat d'exécution GPU | **Modal** (0 € au repos) + **WanGP** headless pour la famille Wan | ComfyUI (déjà le socle du worker LTX prouvé) | Voir MODAL.md |

## Justifications par capacité

### A. Visage — pourquoi FaceFusion d'abord, diffusion en premium
Le face swap par identité encodée (famille inswapper/simswap, orchestrée par
FaceFusion avec détection, occlusion et restauration) reste l'outil de
référence en production vidéo : il conserve **par construction** expressions,
regards, clignements, lumière et gestuelle puisqu'il ne régénère pas la scène.
Ses limites connues : résolution du visage échangé (128–512 px selon modèle)
→ passe d'enhancement indispensable en gros plan ; profils extrêmes et
occlusions lourdes peuvent trahir « l'effet masque ». Pour ces plans héros,
le niveau **Premium** du routeur bascule sur Animate 2 en mode remplacement
(diffusion vidéo, bien plus lent). La scène S1 tranche avec une main devant
le visage et un 3/4 — pas avec des scores automatiques.
⚠️ Licence des poids inswapper à vérifier avant usage commercial
(LICENCES_A_VERIFIER.md) ; alternatives simswap/hyperswap prévues au worker.

### B/C. Personne & mouvement — Animate 2 vs SCAIL-2, jugés sur S3
Les deux modèles 14B de 2026 ont abandonné le squelette intermédiaire :
- **Wan2.2 Animate 2** (Alibaba, août 2026) : end-to-end, multi-personnages,
  contrôle caméra par texte, variante distillée 10 pas ; étude aveugle de
  l'éditeur favorable (>70 % vs Animate v1, comparable à Kling MotionControl
  selon les auteurs — à vérifier chez nous, pas à croire sur parole).
- **SCAIL-2** (Z.ai, juin 2026) : conditioning in-context, fort sur les
  interactions humain-objet et les occlusions, LoRA DPO (mains) et relighting ;
  réputé plus lent.
Ni l'un ni l'autre n'a tourné sur nos sources : S3 les oppose sur la même
performance (marche + saisie d'objet). Le routeur met Animate 2 par défaut
(équilibre vitesse/contrôle) et SCAIL-2 en Premium/challenger.
**Substrat** : WanGP headless (`wgp.py --process`) — il intègre déjà ces deux
modèles avec quantifications adaptées et téléchargement des poids ; réécrire
ces pipelines serait du gaspillage. ComfyUI reste le repli si le format
settings WanGP s'avérait inadapté (le worker fait un `--dry-run` avant tout
rendu pour échouer vite et presque gratuitement).

### D. Lèvres — LatentSync pour livrer, MuseTalk pour essayer
Sur une vidéo existante, LatentSync 1.6 (diffusion latente audio-conditionnée,
entraîné en 512 px) est la référence open source actuelle pour la netteté
bouche/dents/langue ; MuseTalk (inpainting latent 1 pas) est ~temps réel
mais en 256 px. Le studio exploite les deux intelligemment plutôt que de
choisir : qualité **Brouillon** = MuseTalk (valider texte et rythme en
quelques secondes), **Production/Premium** = LatentSync 1.6. InfiniteTalk en
mode v2v est le candidat pour les doublages **longs** où tête et corps doivent
aussi réagir à la nouvelle voix (challenger en S4, pas en S2 courte).

### E. Voix — la performance d'abord, la synthèse ensuite
Ordre de préférence du studio, du plus naturel au plus synthétique :
1. **L'enregistrement de l'utilisateur tel quel** (le routeur saute l'étape voix).
2. **Seed-VC** : l'utilisateur joue la scène, on change seulement le timbre
   (respirations, hésitations et rythme survivent — c'est ce qui sonne « vrai »).
3. **Chatterbox Multilingue V3** : texte → voix clonée depuis ~5 s de
   référence, français inclus, contrôle d'expressivité. Déjà le parcours
   validé du studio précédent. (IndexTTS écarté : pas de français.)
Une voix « trop propre » est un défaut : la revue humaine inclut une écoute
attentive aux respirations et à la stabilité du timbre.

### F. Avatar — LongCat 1.5 (prouvé chez nous), InfiniteTalk en challenger
LongCat-Video-Avatar 1.5 : encodeur audio Whisper-large (meilleure dynamique
labiale que wav2vec2), distillation 8 pas, INT8, continuation vidéo, et surtout
**déjà déployé et ayant produit un vrai MP4 français sur notre compte Modal**
(720×1280, 3,72 s, ~308 s sur A100 — chiffres de l'ancien studio). Sa limite
actuelle est le pilote mono-segment : S4 doit valider l'enchaînement de
segments (continuation) pour des prises de 15–30 s sans dérive d'identité.
InfiniteTalk est comparable en mono-personnage et meilleur candidat pour le
doublage vidéo→vidéo long ; HunyuanVideo-Avatar reste en veille (pas
d'avantage démontré pour notre usage face-caméra FR, coût d'intégration réel).

### H. Création complète — LTX-2.5 prouvé, le reste est du montage
Pour les plans sans source : LTX-2.5 via le worker ComfyUI déjà prouvé
(deux passes, ~109 s/plan à chaud sur L40S dans l'ancien studio), image de
référence par personnage pour la cohérence inter-plans. Le reste d'une
« production complète » n'est pas un modèle : storyboard éditable, prises
multiples comparées, montage ffmpeg (xfade, sous-titres ASS + SRT, loudnorm
−14 LUFS), QC. C'est exactement ce que le studio fait déjà en CPU.

## Ce qui peut faire changer ces décisions

- S1–S5 défavorables → le challenger devient le défaut du routeur (un seul
  endroit à changer : `recipes.py` + `registry.PREFERENCE`).
- Un modèle 2026 ultérieur nettement supérieur sur une scène → il entre par
  le même chemin : worker Modal → benchmark contre le tenant → promotion.
- Contrainte de licence confirmée → bascule documentée dans
  LICENCES_A_VERIFIER.md avant tout usage client.

## Écartés volontairement (pour l'instant)

- **LivePortrait** : excellent en portrait animé par vidéo de référence, mais
  recouvert par Animate 2/SCAIL-2 (corps entier) et LongCat (audio-driven).
- **Wav2Lip** : qualité 96 px dépassée par LatentSync/MuseTalk.
- **API fermées (HeyGen, Kling, Hedra…)** : étalon qualité, pas dépendance —
  le brief exige l'open source sans abonnement de génération.
- **ComfyUI comme produit** : backend d'exécution ponctuel, jamais l'UX.
- **LTX Desktop** : suppose un GPU local ; nous réutilisons son moteur via
  le worker Modal existant, pas son application.
