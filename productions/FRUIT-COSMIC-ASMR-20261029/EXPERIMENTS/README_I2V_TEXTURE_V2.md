# FRAISE COSMIQUE ASMR — Test I2V v2, texture + continuité + son

**Objectif** : corriger précisément les trois défauts observés par l'utilisateur dans le rendu du 29 octobre : texture artificiellement lissée, transition brutale au milieu de la coupe, audio quasi inexistant.

**Base technique** : UGCv2, LTX-2.5 22B distilled INT8, L40S sur Modal `lucj76861`, fonction `pvs-ltx/render_clip` déjà déployée et validée dans la précédente production. Aucun redéploiement ni téléchargement de poids, un appel GPU maximum.

## Diagnostic du test précédent

- L'ancien prétraitement `i2v_onecut.py` remplaçait **96 %** de la matière de la fraise dans le masque par une couleur bleue uniforme, détruisant les petites alvéoles, réfractions et micro-reflets. Le rendu I2V ne pouvait pas restituer une texture de verre riche sur cette base.
- Le MP4 brut précédent a été examiné image par image : le couteau change visiblement de trajectoire vers la moitié du plan et le fruit passe brusquement d'une fraise entière à deux disques. Ce n'est pas un cut de montage FFmpeg ; la discontinuité est générée **à l'intérieur du plan LTX**.
- La piste audio était absente (`audio_mode=silent`), ce qui contredisait l'objectif de véritable ASMR.

## Changements proposés et réellement codés

1. **Texture** : même image haute qualité d'origine `shot-02-firstframe.png`, même couteau et marbre ; assombrissement radial limité au noyau lumineux. Alvéoles de graines, reflets spéculaires, facettes, gouttelettes et microstructure préservés. Pas de masque couvrant la fraise entière.
2. **Mouvement** : le prompt insiste sur une seule trajectoire constante avec contact lame/fruits continu jusqu'à la fin. Il retire l'ordre de soulever le couteau et l'ordre de faire apparaître deux moitiés à 3 secondes ; séparation **en toute fin**, sans étape nouvelle. Limite empirique : un prompt ne garantit pas la conservation de la géométrie physique par le modèle.
3. **Réglage I2V** : `image_strength=0.78` (avant 0.72) ; même résolution native 768×1344, 121 frames à 24 i/s et même pipeline GPU, nouveau seed explicite.
4. **Audio** : `audio_mode=native` pour obtenir la piste multimodale LTX ; mention directe du micro-ASMR dans le prompt (frottement, fissure, tintement, pas de musique). Post-mix CPU avec un **vrai enregistrement de verre** CC BY 4.0 à niveau faible vers 2,4 s. Le timing est indicatif et doit être validé à l'écoute et à l'image, pas certifié automatiquement.
5. **Contrôle** : fichier source, graphe I2V et enregistrement audio réels vérifiés *avant* l'appel GPU. Blocage si le sample manque. Export brut (avec son natif), export mixé, image source et rapports conservés dans GitHub Actions.

## Son réel utilisé et attribution obligatoire

- « **Glass breaking (Gravity Sound).wav** », par **Gravity Sound**.
- Source : https://commons.wikimedia.org/wiki/File:Glass_breaking_(Gravity_Sound).wav
- Licence : https://creativecommons.org/licenses/by/4.0/ (**CC BY 4.0**).
- Modifications : son atténué, raccourci, légèrement fondu, décalé et mélangé avec la piste native LTX. L'attribution du compositeur et de la licence devra accompagner toute diffusion publique.
- Si la ressource audio ne peut pas être récupérée sur le runner, aucun calcul GPU n'est autorisé.

## Critères de réussite créative (non automatisés)

- Même couteau, fraise et arrière-plan pendant **tout** le plan ; pas de scène invisible de remplacement, pas de coupe de montage.
- Contact physique continu et une seule trajectoire de lame cohérente, jusqu'au dernier instant.
- Graine/alvéoles réfractives, épaisseur du verre, surfaces riches et très détaillées ; ni plastique ni couleur unie.
- Son clair et audible en continu, craquement net proche du contact, pas de gros bruit d'explosion / musique / voix.
- **Si une seule de ces exigences majeures échoue, ne pas déclarer la vidéo réussie.** Aucun rerender automatique.

Références ASMR consultées : https://www.youtube.com/watch?v=7Js8b9B3CaU et https://www.youtube.com/watch?v=uhnfIfI1LKw (références de qualité et de direction, sans copie de contenu).
