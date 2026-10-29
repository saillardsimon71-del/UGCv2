# Visual Engine CPU - résultat du pilote

Base unique : `production/us-fr-adapt-ai-automation-pilot-20261029`, commit
`cb6df9e008e1014a3dbbb0cf6a583daabd2a363b`.
Branche de livraison : `production/visual-engine-us-fr-pilot-20261029`.

## Résultat réellement produit

[MP4 de 53,766 s](VISUAL_OUTPUT/PILOTE_VISUAL_ENGINE_FR.mp4), 1920x1080,
30 images/s, H.264 + AAC stéréo 48 kHz. Taille : 3 001 319 octets.
Voix originale du script FR, synthétisée localement par Microsoft Hortense Desktop.
Aucune voix ni image de la référence américaine dans le résultat.

Cinq templates paramétrables : accroche avec cartes animées, workflow à connexions
animées, maquette pédagogique avec révélation du brouillon, graphique explicatif,
récapitulatif. Fondus, rapprochement de caméra et panoramique discrets sont rendus
sur CPU. Les barres illustrent un ordre de contrôle, pas une performance mesurée.

Chaque scène affiche ILLUSTRATION - DONNÉES FICTIVES. La maquette porte aussi
MAQUETTE ANIMÉE et BROUILLON ILLUSTRATIF. Aucune exécution n8n/Mistral revendiquée.

## Code et réutilisation

- `backend/app/visuals.py` : templates, limites typographiques, narration/cache,
  calcul des durées et rendu image par image.
- `backend/app/engines/visual.py` : moteur `cpu_visual`, sélection explicite via le
  registre existant, compatible EngineRequest/EngineOutput.
- `backend/app/visual_source.py` : ingestion URL, transcription analytique,
  chapitres, détection de changements et estimation OCR des types de visuels.
- `backend/app/visual_storyboard.schema.json` : contrat JSON.
- [VISUAL_STORYBOARD.json](VISUAL_STORYBOARD.json) : exemple complet réutilisable.
- `scripts/render_visual_pilot.py`, `scripts/visual_voice.ps1`,
  `scripts/qc_visual_pilot.py` : génération et contrôle reproductibles.

`graphics.py` et `assembly.py` sont inchangés. La narration passe par le montage
existant et ses fondus/loudnorm. Sans narration, un assemblage vidéo seul évite
l'erreur NaN observée dans loudnorm sur le silence numérique avec ce FFmpeg.
Les moteurs Modal, l'interface, les anciens projets et le plan des captures
réelles restent inchangés.

## Reproduction

Depuis la racine du dépôt, dans l'environnement backend existant :

```powershell
python -m pip install -r backend/requirements-visual.txt
python scripts/render_visual_pilot.py --source-url https://youtu.be/KSOxkhWs2Ic --narration cached
python scripts/qc_visual_pilot.py productions/US-FR-ADAPT-001-20261029/VISUAL_OUTPUT
python -m pytest tests productions/US-FR-ADAPT-001-20261029/tests/test_visual_engine.py -q
python productions/US-FR-ADAPT-001-20261029/tests/validate_project.py
```

Le cache livré contient uniquement les cinq WAV utilisés, avec signature des textes.
`--narration cached` ne contacte aucun service et fonctionne sans System.Speech.
Pour régénérer la voix sous Windows, supprimer le manifeste de cache puis utiliser
`--narration required`. `--narration none` produit un MP4 sans piste audio.
Un nouveau dossier `--out` demande sa propre voix/cache.

La police du rendu livré est Segoe UI, déjà installée sur cette machine.
Sous Linux, DejaVu Sans est le repli. `STUDIO_VISUAL_FONT` permet d'indiquer
un TTF installé. Les empreintes de police, storyboard et MP4 sont enregistrées.
La reproduction est fonctionnelle ; l'identité binaire entre OS/polices/encodeurs
différents n'est pas promise. Les fichiers de police Windows ne sont pas redistribués.

Analyse réseau séparée, sans réemploi de la source :

```powershell
python scripts/render_visual_pilot.py --source-url https://youtu.be/KSOxkhWs2Ic --analysis-only
```

yt-dlp récupère des sous-titres et un flux vidéo de référence limité à 360p/80 Mo
dans un dossier temporaire. FFmpeg et Tesseract travaillent dessus, puis ce dossier
est supprimé. Seules les statistiques analytiques sont livrées. Tesseract est une
dépendance système optionnelle pour l'estimation des types visuels.

## Analyse réelle de la référence

[Preuve structurée](VISUAL_OUTPUT/source_analysis.json) :

- 475 s annoncées par YouTube, 7 chapitres.
- 255 segments anglais analysés ; preuves lexicales : trigger, action, automation,
  Dropbox, Zapier, ChatGPT. Il ne s'agit pas d'une analyse sémantique par LLM.
- 86 changements détectés ; intervalle moyen 5,465 s, médian 2,536 s.
  Une animation ou un changement d'écran peut être compté comme une coupe.
- Sur huit échantillons, six ont une forte densité de texte, deux une faible densité.
  L'OCR ne distingue pas de façon fiable une interface d'un diagramme, ni un
  présentateur d'un autre visuel pauvre en texte.

L'adaptation originale du concept exploite le SCRIPT_FR déjà rédigé : artisan à
Rouen, n8n/Mistral envisagés, contrôle humain. Le CLI reconnaît cette URL et choisit
ce storyboard local. Pour une autre URL, l'analyse fonctionne selon l'accès YouTube,
mais le rendu exige un storyboard FR original via `--storyboard`.
La génération sémantique universelle d'un nouveau script/storyboard à partir
d'une URL seule n'est pas implémentée. Aucun résultat n'est inventé pour la simuler.

## Contrôles exécutés

[QC technique](VISUAL_OUTPUT/qc.json), [planche de contrôle](VISUAL_OUTPUT/QC/contact_sheet.jpg),
[métriques](VISUAL_OUTPUT/metrics.json).

- Décodage intégral : 1 613 images, aucun intervalle de présentation irrégulier.
  L'assemblage existant ajoute environ une image par rapport à la durée nominale.
- Aucun passage noir détecté à partir de 0,1 s.
- Voix présente ; chaque fichier vocal tient dans sa scène avant le fondu suivant.
- Niveau mesuré : -14,0 LUFS intégrés, crête vraie -1,5 dBTP.
- 17 images extraites couvrant les cinq scènes et l'avant/milieu/après des quatre
  transitions. Planche et vues 1080p inspectées : accents lisibles, mentions
  d'illustration visibles, aucune collision de texte observée.
- Les détecteurs signalent 24 passages quasi statiques à partir de 0,6 s sur ces
  panneaux pédagogiques à mouvements discrets. Ils sont conservés comme points
  de revue du rythme, et ne prouvent pas un défaut de décodage.
- L'écoute humaine n'a pas été exécutée. La qualité audible et les prononciations,
  notamment "IA" et "n8n", restent à approuver.
- Les sous-titres utilisent la durée réelle de chaque voix, avec répartition
  proportionnelle des phrases. Aucun alignement forcé mot à mot n'est revendiqué.

Tests exécutés : **29 passés** (16 existants + 13 nouveaux), avec un avertissement
de dépréciation python_multipart dans les dépendances existantes.
Le validateur de préproduction passe aussi. Aucun appel Mistral/n8n/Modal exécuté.

Les tests nouveaux couvrent notamment : médias externes interdits, fausses
exécutions interdites, limites de texte/temps, animation des cinq templates,
cache vocal périmé refusé, URLs strictes, conservation des timecodes, encodages
réels silencieux avec caméra/fondus, annulation, voix absente refusée par le QC
et fin de narration avant une transition de 0,8 s.

## Mesures et coûts

Dernière génération complète : **84,98 s de temps mural** sur Intel Core i5-7400,
4 coeurs / 4 threads, Windows, Python 3.11.6, Pillow 12.2.0, FFmpeg 8.1.1.
Ce temps inclut lecture/génération du cache voix, images, montage et sous-titres.
Il n'inclut pas préparation, essais précédents, tests ou analyse source.

- GPU demandé : **0 seconde**.
- Appels de génération payants : **0**.
- Dépense externe de génération : **0 USD**.
- CPU, électricité et temps de l'agent : non valorisés financièrement.
- Mémoire maximale et consommation électrique : non mesurées.

Le résultat est local ; aucune publication YouTube ni message client n'a été envoyé.

## Avant les sept minutes

1. Écouter et approuver la voix ; revoir le rythme et les passages quasi statiques.
2. Exécuter réellement le workflow n8n/Mistral sur les données fictives et capturer
   ses sorties, sans exposer de secrets.
3. Compléter le storyboard des sept minutes autour de ces preuves, puis rendre
   par sections et refaire le QC.
4. Pour étendre le produit au-delà de ce pilote, ajouter et tester une vraie
   adaptation sémantique URL vers scénario FR original, avec estimation de coût.
