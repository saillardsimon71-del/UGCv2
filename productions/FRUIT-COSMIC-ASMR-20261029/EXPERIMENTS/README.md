# Test unique — fraise de verre découpée (5 secondes)

## Exécution réelle du 29 octobre — diagnostic

- [Run #40857680365](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40857680365) : échec du précontrôle runner avant GPU (FFmpeg absent). Corrigé par installation préalable.
- [Run #40857883879](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40857883879) : précontrôle et FFmpeg OK ; **échec HTTP 403 sur le téléchargement Pexels direct** pendant la préparation de la source. Aucune génération Modal n'a eu lieu.
- Le workflow est volontairement **fail-closed** : aucun rendu ne démarre sans vidéo guide réelle contrôlée. Une nouvelle exécution avec le même fichier marker n'est pas lancée automatiquement.
- **Blocage actuel : source de découpe filmée directement téléchargeable et utilisable**. Éviter les tentatives GPU à partir de prompts seuls ; l'expérience initiale a déjà montré leurs limites. On peut remplacer la source par un fichier vidéo autorisé fourni dans le dépôt puis modifier explicitement la recette et le marqueur de lancement.
- **Résultat : PAS DE MP4 de test. ZÉRO appel GPU pour ces deux runs.** Ne pas annoncer de réussite audiovisuelle.


**Hypothèse à trancher :** LTX-2.5 peut-il conserver un véritable geste de couteau sur une fraise, tout en changeant la matière et en faisant apparaître l'intérieur cosmique ?

## Pourquoi ce chemin change réellement le test
L'essai précédent utilisait trois PNG fixes et LTX image-vers-vidéo. Résultat : l'image était esthétique, mais la coupe physique n'était pas crédible. Ce test conditionne au contraire le modèle sur **121 images d'une véritable découpe filmée**. Il utilise le **graphe vidéo-vers-vidéo du code présent sur la branche**, via une app Modal éphémère : l'audit UGCv2 a prouvé que la version anciennement déployée sous `pvs-ltx` ignorait la vidéo source. Ne jamais utiliser l'ancien déploiement comme preuve V2V.

- **Source réellement sélectionnée après contrôle visuel :** https://www.pexels.com/video/person-slicing-a-strawberry-9020974/ (T Leish, licence Pexels). Fichier CDN direct : https://videos.pexels.com/video-files/9020974/9020974-uhd_3840_2160_25fps.mp4. **Téléchargement GitHub Actions vérifié HTTP 200**, 3840×2160, 25 fps, 13,44 s, 21 543 220 octets, SHA-256 `f0c814bf336f241ccc8c3e96d7ac992688b1c89c77891090aebec0a31772b31f`. Audit CPU : https://github.com/saillardsimon71-del/UGCv2/actions/runs/40859447784. Une personne coupe bien une fraise entière en deux, au couteau, sur une planche en bois.
- **Fenêtre choisie visuellement : 3,5 s à 8,5 s** de la source ; recadrage portrait conservant fraise, lame, doigts et deux moitiés. Guide vérifié en local 768×1344 à 24 fps, 121 frames, 5,0417 s. Le dernier photogramme révèle les deux moitiés. Le sound design reste à valider sur le rendu IA.
- Conditionnement : 768 × 1344, 24 fps, 121 images ; video_mp4_base64 transmis à LTX. Un seul appel GPU, pas de retries.
- Workspace strict : `lucj76861`. Aucun redéploiement ni remplacement de `pvs-ltx`, aucun téléchargement de poids volontaire, pas de changement des secrets.
- Génération : un plan brut, censé préserver le geste, la lame et la séparation des deux moitiés ; extérieur verre bleu opaque puis intérieur galaxie après la coupe.
- Sound design : tentative de récupérer un **véritable fichier CC0** de Till Behrend (https://opengameart.org/content/glass-break). Si indisponible, sortie brute conservée et manque de son rapporté, jamais une fausse piste dite réelle.
- Sorties GitHub Actions : vidéo brute, éventuelle version sonore, source réelle, planches d'images, rapports de métadonnées et coûts techniques.
- Si la source Pexels ne peut pas être récupérée ou validée sur GitHub Actions, **arrêt avant tout GPU**.

## Critère de décision
Regarder les 5 secondes dans leur intégralité : 1) la lame touche réellement le fruit, 2) le fruit reste le même, 3) la coupe suit le couteau, 4) les deux moitiés se séparent réellement, 5) l'intérieur est révélé uniquement après pénétration. Au moindre échec majeur, **ne pas poursuivre LTX avec des variantes du même prompt** : basculer vers un autre moteur/approche.

**Aucune publication TikTok. Aucun verdict esthétique automatique.** Une validation technique GitHub Actions n'est pas un certificat de qualité.

## Remplacement de source : contrôle comparatif

La source initiale [Pexels 4081319](https://www.pexels.com/video/slicing-a-fresh-strawberry-fruit-with-a-knife-4081319/) a été directement téléchargée par [CPU probe #40858890053](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40858890053), 48,6 Mo, 4K, 15,47 s. Mais l'inspection a prouvé que le cadrage macro devenait inexploitable en 9:16 (texture rouge et couteau seuls, pas de fruit entier). Elle est **écartée**, malgré le succès technique du téléchargement. La deuxième source est la référence retenue. Aucun GPU utilisé pour cette sélection.
