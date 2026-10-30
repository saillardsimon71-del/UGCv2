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


## Étape 2 — orchestrateur sans agent et sans GPU (PR #7)

Le nouveau module `planner.py` fabrique des demandes de plans de quatre secondes maximum à partir d'une **vidéo à images/s fixes**, de la liste de scènes (écran / plan caméra / PiP), et d'un alignement **mot par mot**. Les frontières sont prises entre deux mots, jamais à une durée arbitraire. Il produit des plans **PENDING**, et ne lance ni LTX ni TBDub.

Exemple de lancement, avec des fichiers vidéo et JSON locaux qui ne sont **pas** publiés :

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/planner.py \
  --source /private/source.mp4 \
  --words /private/words.json \
  --scenes /private/scenes.json \
  --output /private/plan.json
```

`studio.py` assemble seulement les vraies prises **APPROVED** référencées par chemin relatif + SHA-256 dans le manifeste. Il **refuse** toute prise manquante, modifiée, trop courte, non approuvée ou toute timeline discontinue. Il vérifie par décodage que la narration source est restée strictement identique.

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/studio.py check \
  --manifest /private/plan_approuve.json --media-root /private
python productions/UGCV2-FROZEN-RECIPE-20261030/studio.py assemble \
  --manifest /private/plan_approuve.json --media-root /private \
  --output /private/sortie.mp4
```

**Contrat :** le manifeste déclare `schema: ugcv2.approved-timeline/v1`,
`allow_regeneration: false`, `source: {path, sha256}`,
`word_timing: [{text,start_s,end_s}]`, une couverture en images `shots:
[{start_frame,end_frame,mode,take,take_offset_frame,rectangle?}]`, et `takes:
{id: {path,sha256,status: APPROVED}}`. Les médias restent hors du dépôt.
Les titres compliqués ou non vérifiés sont **bloqués** et non recouverts de
manière hasardeuse.

`test_autopilot.py` utilise des **vidéos synthétiques** pour dix tests réels,
dont le rendu, l'intégrité audio, les raccords, les prises non autorisées,
l'absence de fichiers et les coupures au milieu d'un mot. Les tests sont lancés
sur GitHub Actions par `.github/workflows/ugcv2-golden-cpu.yml`.

### Restant avant le vrai « URL YouTube → MP4 autonome »

L'import YouTube autorisé, la détection automatique des scènes, la transcription
et l'adaptation française alignée, la production 4s LTX/TBDub, l'ancrage effectif
sur l'image de fin approuvée et **un contrôle perceptif du lipsync/naturel**
restent à implémenter/qualifier. Ce changement n'a pas produit un nouvel acteur
ni démontré que les prochains plans générés seront de bonne qualité.

La règle acquise : **aucun nouveau master ne remplace silencieusement un master
approuvé, même avec le même seed et les mêmes réglages.**


## Étape 3 — importer localement les VRAIS masters Work, sans publication

`assets.py` a été exécuté **avec les deux fichiers privés fournis dans la conversation** :
le ZIP `UGCv2_recette_et_sources_courtes.zip` et le MP4 corrigé de 6,52 s.
Les sept fichiers ont été extraits dans un dossier privé, puis chacun
recontrôlé par SHA-256, sans GPU ni nouvel encodage.

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/assets.py \
  --work-zip UGCv2_recette_et_sources_courtes.zip \
  --approved-mp4 UGCv2_RACCORD_RYTHME_V2_6p52s.mp4 \
  --private-target ./private-ugcv2-catalog
```

Ce dossier ne doit **pas** être commité, déplacé dans un artifact GitHub public,
ni récréé en régénérant approximativement la vidéo. Il contient un `catalog.json`,
la vidéo approuvée et les vrais fichiers LTX/TBDub intermédiaires disponibles.

Limite vérifiée : le premier master natif LTX du test initial manque toujours au
ZIP fourni ; c'est indiqué explicitement dans le catalogue. Le MP4 approuvé
de 6,52s contient toutefois le passage effectivement retenu.
