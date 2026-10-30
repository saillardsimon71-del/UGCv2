# Audit du présentateur et stratégie des deux tests

Référence : `UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4`, run GitHub 40957764927, commit `406e8d6fd27ba6fdd9c120b92ee2cb6154d09176`.
SHA-256 : `346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d`.

## Présences vérifiées dans le fichier validé

Temps locaux de la minute, intervalles [début, fin). Images numérotées depuis zéro, à 25 images/s. Ajouter 42 secondes pour retrouver la vidéo YouTube originale. Chaque frontière ci-dessous a été comparée sur les images immédiatement avant et après la coupure. Une planche toutes les 12 images complète cette inspection des frontières.

| Début | Fin | Images | Présence et traitement nécessaire |
|---|---|---|---|
| 0,00 | 0,68 | 0-16 | Tarifs Zapier, aucun visage |
| 0,68 | 5,60 | 17-139 | PiP en haut à droite |
| 5,60 | 12,00 | 140-299 | Présentateur en grand, face caméra |
| 12,00 | 14,24 | 300-355 | Présentateur encore identifiable derrière le voile blanc et le titre "TRIGGER" |
| 14,24 | 15,56 | 356-388 | PiP pendant l'explication du déclencheur |
| 15,56 | 21,08 | 389-526 | Dominos et mains, aucun visage identifiable |
| 21,08 | 24,48 | 527-611 | Présentateur en grand, vue de trois quarts |
| 24,48 | 26,80 | 612-669 | Présentateur en grand, retour face caméra |
| 26,80 | 29,64 | 670-740 | Bureau et interface, aucun visage |
| 29,64 | 31,08 | 741-776 | Présentateur en grand, plan court |
| 31,08 | 56,12 | 777-1402 | PiP sur la démonstration Zapier/Dropbox et les fenêtres Finder |
| 56,12 | 59,72 | 1403-1492 | Présentateur en grand |
| 59,72 | 60,00 | 1493-1499 | Retour de la PiP sur les sept dernières images |

Le découpage antérieur n'était pas exact. Il omettait notamment le visage derrière "TRIGGER", la PiP 14,24-15,56 et le retour final. Utiliser ses seules quatre plages ne peut pas supprimer toutes les apparitions de l'acteur source. Les changements d'interface à l'intérieur d'une plage PiP ne suppriment pas cette PiP.

## Méthode retenue

1. Créer une seule photographie synthétique du nouvel acteur et de son bureau, intégrés ensemble. Choix de cette expérimentation : homme fictif d'environ 45 ans, peau foncée, tête rasée, visage rond sans barbe, chemise bleue, bureau clair. Ces choix le distinguent immédiatement de la référence à casquette, cheveux longs et barbe. Aucun visage réel de remplacement n'est utilisé.
2. Animer cette référence une seule fois avec le chemin image-vers-vidéo LTX-2.5 existant. Aucune image de l'acteur source n'entre dans ce générateur. Le décor, l'éclairage et la silhouette sont produits dans un même plan, sans segmentation du fond.
3. Utiliser exactement le même master animé pour A et B. Exécuter le moteur TBDub Student v1.1 existant sur chaque extrait français correspondant. La narration provient de l'audio du MP4 validé, décodé puis coupé à vitesse 1,0. Aucun appel Chatterbox, aucune réécriture de texte, aucun changement de débit.
4. A utilise le nouveau plan entier. B remplace intégralement le rectangle de caméra existant, coordonnées x=1428, y=0, largeur=492, hauteur=444. Aucun mélange avec le visage original et aucune découpe suivant les épaules. La réduction et le recadrage conservent les proportions.

La détection du visage interne à TBDub sert uniquement à sa synchronisation labiale. Ce n'est pas le pipeline rejeté de détourage du fond MediaPipe. Les fichiers `deploy/modal_ltx_worker.py`, `deploy/modal_tbdub_fr_worker.py` et le moteur Chatterbox restent inchangés.

## Deux tests uniquement

| Test | Extrait de la référence | Extrait YouTube | Durée |
|---|---|---|---|
| A, présentateur en grand | 7,60-11,60 s | 49,60-53,60 s | 4,00 s |
| B, PiP | 42,00-46,00 s | 84,00-88,00 s | 4,00 s |

Un master animé de quatre secondes, deux synchronisations labiales, aucun rendu complet. Les deux prises ne démontrent pas encore la continuité de l'ensemble des 50,96 secondes où un visage apparaît dans la minute. Elles ne doivent pas être bouclées pour fabriquer le rendu final.

## Reproduction

Depuis la racine du dépôt, avec Python, FFmpeg et la connexion Modal existante :

```powershell
python productions/FR60-PRESENTER-PROOF-20261030/proof.py prepare --source CHEMIN_DU_MP4_VALIDE
python productions/FR60-PRESENTER-PROOF-20261030/proof.py animate
python productions/FR60-PRESENTER-PROOF-20261030/proof.py lips
python productions/FR60-PRESENTER-PROOF-20261030/proof.py compose
```

Les reçus empêchent une répétition automatique des calculs. Aucun déploiement permanent n'est remplacé. Les sources temporaires sont dans `CACHE/`, les deux MP4 de livraison dans `EXPORTS/`. Le prompt de photographie est conservé dans `ASSETS/presenter-prompt.txt`, le prompt d'animation et les révisions des modèles dans `animation.json`.

Statut d'évaluation : voir `VERDICT.md`, rédigé après inspection des fichiers réellement exportés.
