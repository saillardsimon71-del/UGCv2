# Test unique — fraise de verre découpée (5 secondes)

**Hypothèse à trancher :** LTX-2.5 peut-il conserver un véritable geste de couteau sur une fraise, tout en changeant la matière et en faisant apparaître l'intérieur cosmique ?

## Pourquoi ce chemin change réellement le test
L'essai précédent utilisait trois PNG fixes et LTX image-vers-vidéo. Résultat : l'image était esthétique, mais la coupe physique n'était pas crédible. Ce test conditionne au contraire le modèle sur **121 images d'une véritable découpe filmée**. Il utilise le **graphe vidéo-vers-vidéo du code présent sur la branche**, via une app Modal éphémère : l'audit UGCv2 a prouvé que la version anciennement déployée sous `pvs-ltx` ignorait la vidéo source. Ne jamais utiliser l'ancien déploiement comme preuve V2V.

- Source filmée sélectionnée : https://www.pexels.com/video/slicing-a-fresh-strawberry-fruit-with-a-knife-4081319/ (licence Pexels ; pas de faux témoignage).
- Sélection temporelle automatique : fenêtre autour du mouvement maximal ; cette heuristique **ne garantit pas** qu'il s'agit bien de la coupe. Le guide brut et une planche de 5 images sont archivés pour inspection.
- Conditionnement : 768 × 1344, 24 fps, 121 images ; video_mp4_base64 transmis à LTX. Un seul appel GPU, pas de retries.
- Workspace strict : `lucj76861`. Aucun redéploiement ni remplacement de `pvs-ltx`, aucun téléchargement de poids volontaire, pas de changement des secrets.
- Génération : un plan brut, censé préserver le geste, la lame et la séparation des deux moitiés ; extérieur verre bleu opaque puis intérieur galaxie après la coupe.
- Sound design : tentative de récupérer un **véritable fichier CC0** de Till Behrend (https://opengameart.org/content/glass-break). Si indisponible, sortie brute conservée et manque de son rapporté, jamais une fausse piste dite réelle.
- Sorties GitHub Actions : vidéo brute, éventuelle version sonore, source réelle, planches d'images, rapports de métadonnées et coûts techniques.
- Si la source Pexels ne peut pas être récupérée ou validée sur GitHub Actions, **arrêt avant tout GPU**.

## Critère de décision
Regarder les 5 secondes dans leur intégralité : 1) la lame touche réellement le fruit, 2) le fruit reste le même, 3) la coupe suit le couteau, 4) les deux moitiés se séparent réellement, 5) l'intérieur est révélé uniquement après pénétration. Au moindre échec majeur, **ne pas poursuivre LTX avec des variantes du même prompt** : basculer vers un autre moteur/approche.

**Aucune publication TikTok. Aucun verdict esthétique automatique.** Une validation technique GitHub Actions n'est pas un certificat de qualité.
