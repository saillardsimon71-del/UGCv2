# Recette source-performance v1

L'audit est dans [SOURCE_PERFORMANCE_AUDIT.md](SOURCE_PERFORMANCE_AUDIT.md).
La recette machine est dans
[`source_recipe.json`](../productions/UGCV2-FROZEN-RECIPE-20261030/source_recipe.json).
Cette branche ajoute une orchestration au studio existant. L'adaptateur
`modal_source_lips.py` réutilise l'image, les modèles et l'inférence TBDub
existants ; il ne constitue pas un nouveau moteur et n'a pas été déployé.

## Commande

```bash
python production.py --youtube "URL" --avatar default --voice default
```

La commande enregistre son analyse puis retourne actuellement `BLOCKED`, code
de sortie 2, avant synthèse/GPU. Elle ne livre pas de MP4 automatiquement tant
que les qualifications essentielles manquent. Pour demander seulement l'analyse :

```bash
python production.py --youtube "URL" --avatar default --voice default --cpu-only
```

`--source fichier.mp4` réutilise une copie autorisée existante pour éviter le
téléchargement. Son empreinte est conservée avec l'identifiant YouTube déclaré ;
cela ne constitue pas une vérification indépendante de cette provenance.
`--run-id mon-run` reprend exactement le même état. Sans identifiant, la clé est
dérivée de la source, de la recette et du code. Les données restent sous
`data/source-production/`, ignoré par Git.

Avec `--private-remote`, les fichiers et le journal utilisent le volume Modal
privé existant `ugcv2-production-private`, dans l'espace `lucj76861`. Les secrets
existants sont utilisés par Actions, sans modification ni déploiement de worker.
Les artefacts publics du nouveau workflow contiennent uniquement des métadonnées.

## Étapes fixes et état réel

| Phase | Comportement implémenté | Qualification actuelle |
|---|---|---|
| Import | yt-dlp existant, limite 15 min/1 Go ; ou copie locale ; normalisation paysage 1080p25 | Copie locale et média réel testés ; accès YouTube distant non prouvé dans cette mission |
| Analyse | Détection MediaPipe sur chaque image, candidats plein écran/PiP/écran | Détection testée ; une absence de visage ne prouve pas une absence de personne |
| Adaptation | ASR CPU épinglée, EN vers FR existant ; FR conservé ; JSON horodatés | Traduction automatique, sans compréhension des actions à l'écran ; adaptation éditoriale générique non résolue |
| Voix | Worker V3 existant, deux prises fixes par phrase, sélection par durée, vérification des mots, mix PCM48k aux temps source | Aucun nouvel appel voix effectué ; timbre interphrases non qualifié ; worker limité à 30-310 caractères et fenêtres 4-13 s |
| Présentateur | Extraction du passage courant, FaceFusion `one`, puis détourage/fond CPU ; matte FFV1 conservée | Worker FaceFusion historique prouvé sur l'ancien avatar ; avatar récurrent actuel et contours non qualifiés |
| Lèvres | Même TBDub Student, paramètres du run de référence ; clip et audio propres à chaque passage | Nouvelle enveloppe générique 1-15 s non exécutée ; sorties d'une autre durée refusées sans gel/étirement |
| Recomposition | Temps entiers à 25 i/s, source comme fond, incrustation au rectangle PiP exact, piste FR entière | Test CPU réel sur médias synthétiques ; aucune boucle pour combler une prise |
| Contrôle | Empreintes, décodage, images/durées, fichier manquant, masque invalide, format/longueur voix, budget global | Contrôle perceptuel calibré absent ; le code bloque explicitement après les contrôles techniques |
| Export | Rapport toujours conservé après ouverture du run ; candidat conservé si rendu atteint | Aucun chemin ne promeut encore un candidat en MP4 final autonome |

Le manifest `--timeline` doit couvrir toutes les images, être lié au SHA de la
source normalisée et contenir des rectangles PiP valides. Les modes sont
`screen`, `full`, `pip`. Titres semi-transparents et occlusions complexes sont
refusés. Aucun manifest approximatif n'est fabriqué à partir de quatre temps fixes.

## Références et paramètres

- Avatar récurrent : portrait existant `FR60-PRESENTER-PROOF-20261030/ASSETS/presenter-studio.png`,
  SHA `bd5ce8b0b67fd7cae6f197fc4608e7dff8b78882c162aba54c9e177d6e37bea3`.
- Décor : photo de bureau vide de Cup of Couple, Pexels 6177557, JPEG conservé
  dans `assets/default-background.jpg`, empreinte et crédits figés. Recadrage
  centré couvrant l'image cible, sans recoloration ni génération.
- FaceFusion 3.5.1 : inswapper128fp16, GFPGAN1.4, `one`, `large-small`, qualité90.
- Chatterbox : code `5de7a54aa4e5e2baadb0182dde554908b48b85c2`, V3/FR.
  Prise `unhurried` : 0,43 / 0,63 / 0,77 ; `conversational` : 0,54 / 0,55 / 0,80
  pour exaggeration/CFG/température. Seed historique `60100 + index*10 + prise`.
- Voix retenue : phrase complète entre 62 % de la plage et sa durée moins80ms ;
  prise la plus proche de fin moins300ms ; fondu420 échantillons. Aucun mot
  tronqué, aucun étirement audio ni ralentissement de l'image pour faire tenir le texte.
- Détourage : MediaPipe0.10.21, paysage1, entrée480x270, alpha
  `clip((p-0.22)/0.52)`, gaussien7x7. Couverture2-90 %, sinon arrêt.
  Cette méthode est réutilisée du pilote CPU antérieur. Elle n'est pas un
  détourage garanti d'objets non humains ; voir la
  [documentation MediaPipe](https://chuoling.github.io/mediapipe/solutions/selfie_segmentation.html).
- TBDub : code `19e18e4ba8e2a19e6716cb38110ee2de1dae9bb3`, Student v1.1,
  deux pas, sigma1, seed42, mouvement depuis les latents source. Contrôle CPU de
  la taille/SHA Student et du landmarker avant GPU ; autres empreintes de cache
  enregistrées. Elles ne remplacent pas une référence de poids encore absente.
- Sortie technique prévue : H.264, CRF18, 25 i/s, yuv420p ; AAC192k, 48kHz.

## Reprise et coût

Chaque opération conserve ses entrées, sorties, empreintes et statut. Le journal
est remplacé atomiquement ; les données sont envoyées au volume avant le journal.
Un succès vérifié est réutilisé. Une erreur en aval ne supprime pas les succès
en amont. Une empreinte incorrecte arrête la reprise au lieu de facturer un
nouveau rendu pour masquer une corruption.

Les appels Modal conservent réservation et identifiant distant. Un appel en cours
est récupéré ; une réservation sans résultat récupérable est bloquée. La reprise
d'un appel distant ambigu exige encore une réconciliation explicite. Elle ne
peut pas être présentée comme une reprise automatique complète de toute erreur.

Budget GPU par défaut : **0**. Le besoin maximal de la chaîne est vérifié avant
le premier appel payant :1200s par phrase +1800s par plan FaceFusion +1200s par
plan TBDub. Ce sont des réservations de durée maximale, pas un devis ni les
durées constatées. Aucune augmentation du budget n'est implicite. Les cinq
qualifications de la recette sont fausses et empêchent actuellement ces appels.

## Vérifier

```bash
python -m pytest productions/UGCV2-FROZEN-RECIPE-20261030 tests -q
python -m py_compile production.py deploy/modal_source_lips.py
```

Le workflow `ugcv2-source-production.yml` exécute les tests et **un composite
CPU de quatre secondes**, extrait d'un clip existant, avec le décor figé. Il
vérifie d'abord le SHA du MP4 de référence et les quatre clips TBDub. Il ne
reconstruit pas la minute. Les images/vidéos privées ne sont pas téléversées.
Sur les pushes et exécutions manuelles, la référence est lue depuis l'archive
Modal privée durable, et non depuis un artefact Actions à durée de rétention
limitée. Les PR exécutent les tests synthétiques sans accéder aux secrets.
Une exécution manuelle peut ensuite analyser une URL avec budgetGPU0 et reprise
privée ; aucune supervision d'agent n'est nécessaire pour cette analyse.

## Preuve GPU éventuelle, préparée et non lancée

Un seul cas : 4s plein écran source, caméra fixe, visage visible, audio français
déjà validé, avatar et décor figés. Enchaîner FaceFusion puis fond CPU puis
TBDub. Pas de synthèse vocale, pas de PiP, pas de LTX, pas de nouvelle minute.
Réutiliser le résultat de chaque étape réussie. Comparer avant/après sur identité,
pose/gestes, contours cheveux/mains/micro et alignement phonétique.

Plafond de calcul proposé : une session FaceFusion et une session TBDub,
réservations maximales cumulées3000s, zéro répétition. Aucun plafond monétaire
fiable n'a encore été établi sur les tarifs du compte ; cette preuve est donc
**non autorisée à l'exécution dans cette recette**. Aucun flag ne la lance en
contournant les qualifications. Un test GPU ne résoudrait d'ailleurs pas à lui
seul la segmentation universelle ni le contrôle qualité automatique.
