# UGCv2 — recette Work figée (étape 1, sans GPU)

Objectif : **ne plus perdre la bonne vidéo** par régénération accidentelle. Cette première étape stabilise les références; elle ne prétend pas encore produire une nouvelle vidéo YouTube.

Scripts comparés dans le dépôt :
- `productions/FR60-PRESENTER-PROOF-20261030/proof.py` (premiers essais Work)
- `productions/FR60-CONTINUITY-8S-20261030/run.py` et `finish.py` (prolongement + montage Work)
- `productions/FR60-RHYTHM-FIX-20261030/trim_pause.py` (correction de silence)
- `productions/FR60-20S-GITHUB-20261030/render_20s.py` (**essai rejeté**, à ne pas reprendre comme recette)

## Verrou des références exactes

Conserver localement les **deux fichiers privés envoyés par l'utilisateur** :
- `UGCv2_recette_et_sources_courtes.zip`
- `UGCv2_RACCORD_RYTHME_V2_6p52s.mp4`

Vérifier avec Python 3, FFmpeg et ffprobe :

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/golden.py verify \
  --work-zip UGCv2_recette_et_sources_courtes.zip \
  --approved-mp4 UGCv2_RACCORD_RYTHME_V2_6p52s.mp4
```

Rejouer **sans générer ni réencoder** le master validé :

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/golden.py replay \
  --work-zip UGCv2_recette_et_sources_courtes.zip \
  --approved-mp4 UGCv2_RACCORD_RYTHME_V2_6p52s.mp4 \
  --output UGCv2_RECETTE_GOLDEN_REPLAY.mp4
```

Le script refuse les changements de SHA, les durées incorrectes et les pistes manquantes. Il compare toutes les images décodées et toutes les trames audio du remux avec l'original.

**Validation CPU réelle du 30/10/2026 :** 6,52 secondes, 163 images 1080p25, 6 sources Work validées, audio et vidéo décodés bit-identiques après remux; aucun appel GPU/Modal/Work.

## Ce qui reste à programmer avant « URL YouTube → MP4 »

1. Découpage de narration **aux phrases entières** (pas de durée arbitraire ni de phrase tronquée).
2. Réutilisation des prises approuvées, **jamais leur régénération silencieuse**.
3. Prolongement LTX image de fin du master retenu, TBDub quatre secondes, sauvegarde du master natif.
4. Contrôle qualité audiovisuel et des raccords : arrêt/reprise ciblée en cas de défaut.
5. Assemblage écran/présentateur/PiP et final vidéo, un seul verdict humain.

**Ne pas publier les sources ni la vidéo de référence dans un dépôt public.** Ce test reprend une vidéo YouTube tierce dont l'autorisation de republication n'est pas établie.

La stabilité technique de ce replay n'est **pas** une preuve que les nouveaux plans générés seront naturels ; cette seconde partie devra être qualifiée séparément.
