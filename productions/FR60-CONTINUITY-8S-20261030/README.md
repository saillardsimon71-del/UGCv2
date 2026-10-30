# Test de continuité de huit secondes

Base : `test/fr60-new-presenter-two-clips-20261030`, commit `b7ac6e05fd7dbae5aa66b59e04aab089a156feec`.

`recipe.json` fige les paramètres, références, empreintes et l'adaptation contrôlée de l'image initiale. `graph-trial-1.json` conserve le graphe LTX réellement exécuté. Les reçus LTX/TBDub, `environment.json` et `verification.json` documentent le résultat.

Depuis la racine du dépôt, les étapes de ce test sont :

```powershell
python productions/FR60-CONTINUITY-8S-20261030/run.py prepare
python productions/FR60-CONTINUITY-8S-20261030/run.py animate --trial 1
python productions/FR60-CONTINUITY-8S-20261030/run.py dub --trial 1
python productions/FR60-CONTINUITY-8S-20261030/finish.py --trial 1
python productions/FR60-CONTINUITY-8S-20261030/verify.py
```

Les étapes déjà exécutées refusent une nouvelle génération sous le même numéro. La limite est de deux générations LTX et deux synchronisations. Aucun nouvel essai n'est lancé par les vérifications.

Entrées locales : sources et sorties du test validé, dont les empreintes sont contrôlées, et `../reference-hybrid/UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4` obtenu depuis l'artifact du run 40957764927. Aucun téléchargement de modèle n'est prévu. Les deux workers existants sont importés sans modification.

Les MP4 et intermédiaires privés restent dans `RENDERS/` et `CACHE/`, exclus du dépôt public. Les MP4 livrés sont également disponibles dans le dossier `outputs/UGCv2_continuite_8s/` du chat.
