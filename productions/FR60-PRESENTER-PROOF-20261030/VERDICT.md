# Verdict : pas encore prêt pour lancer la minute complète

Les deux vrais extraits sont produits. La nouvelle méthode résout visiblement le changement d'identité et le décor sur les images examinées. La validation du lipsync en lecture continue avec le son reste à faire ; je ne déclare donc pas les deux tests acceptés et je n'ai pas lancé le rendu de 60 secondes.

## Fichiers réels

| Fichier | Durée | Vidéo | Audio |
|---|---|---|---|
| `Clip_A_gros_plan.mp4` | 4,000 s | 1920x1080, 25 images/s, H.264 | Français validé, AAC 48 kHz stéréo |
| `Clip_B_PiP.mp4` | 4,000 s | 1920x1080, 25 images/s, H.264 | Français validé, AAC 48 kHz stéréo |

Les MP4 sont livrés dans le dossier local `outputs/UGCv2_tests_identite/`. Le dépôt public conserve le code, la référence synthétique, les prompts et les rapports, sans publier les extraits dérivés de la vidéo source.

## Evaluation honnête

| Critère | Constat |
|---|---|
| Visage réellement différent | Oui sur les images examinées : nouvelle morphologie, tête rasée, peau foncée, absence de barbe et de casquette. Il ne s'agit pas d'une recoloration du visage source. |
| Nouveau décor propre | Oui sur les images examinées : bureau clair cohérent avec l'acteur, sans bord de silhouette, trou dans le visage ou bavure du détourage rejeté. |
| Même acteur dans A et B | Oui : même référence photographique et même master animé, avec deux synchronisations françaises différentes. Cohérence observée sur les contacts des deux clips. |
| Retour de l'acteur source dans la PiP | Aucun observé. Les 100 images du rectangle PiP correspondent intégralement au nouveau plan dans le composite sans perte. L'ancien rectangle n'est jamais révélé avant l'encodage final. |
| Conservation des interfaces | Vérifiée sur les 100 images : pixels hors caméra identiques avant compression. Après H.264, PSNR hors caméra de 52,26 dB, avec une marge de deux pixels autour du bord pour la mesure RGB. |
| Narration française et rythme | Extraits exacts du MP4 validé, sans changement de texte ni de vitesse. La corrélation audio après encodage AAC dépasse 0,99985 à décalage nul pour A et B. Ceci vérifie la conservation de l'audio, pas la synchronisation des lèvres. |
| Lipsync acceptable | TBDub Student v1.1 a réellement traité les deux clips. Les bouches sont animées et les durées concordent. L'acceptabilité phonétique et perceptive n'est pas validée par ces seuls contrôles. |
| Qualité au moins équivalente à la référence | Non certifiée. Le nouveau master LTX est natif en 1344x768 puis mis au format 1080p ; le gros plan conserve une certaine douceur. Le rendu du visage et la synchronisation doivent être comparés à la référence en lecture continue. |

Inspection effectuée : 32 images réparties sur le gros plan A, une image A en pleine définition, 25 vues de la PiP B et une image B en pleine définition. Les 100 images de chaque export ont été décodées sans erreur. Il n'y a pas eu de visionnage audiovisuel continu ni d'écoute humaine revendiqués.

## Calcul limité

- Une génération image-vers-vidéo de 97 images : 121,373 secondes internes du worker L40S.
- Une synchronisation A : 70,93 secondes internes.
- Une synchronisation B : 68,00 secondes internes.
- Total mesuré dans ces trois fonctions : 260,303 secondes. Ce total exclut notamment l'attente, les builds, la préparation CPU et la génération de la photographie ; ce n'est pas une facture.
- Les deux applications temporaires sont arrêtées, zéro tâche active. Les déploiements existants n'ont pas été remplacés.

## Condition pour continuer

La lecture des deux MP4 avec leur son doit confirmer un lipsync crédible et une qualité de visage au moins équivalente à la référence. Les huit secondes de tests ne prouvent pas encore la continuité de toute la minute. Le futur montage devra couvrir toutes les plages de `AUDIT.md`, y compris le visage derrière "TRIGGER" et la PiP finale, sans boucler ces quatre secondes de master pour fabriquer une minute.
