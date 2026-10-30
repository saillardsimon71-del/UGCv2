# Stabilisation de la performance source

Exécution directe autorisée par la mission utilisateur. Branche isolée
`stabilization/source-performance-recipe-20261030`, basée sur `ab4544d` pour
réutiliser les checkpoints existants. La recette LTX antérieure reste intacte.

Objectif : industrialiser la chaîne du run 40957764927 sans recréer les gestes
depuis une photographie. Python 3.11, FFmpeg, FaceFusion 3.5.1, Chatterbox V3,
TBDub Student v1.1. Aucun nouveau moteur vidéo, déploiement ou secret.

- [x] Audit : empreintes des artefacts, provenance des modèles et paramètres,
  limites exactes de sélection des plans, reprises vocales, différences avec I2V.
- [x] Recette et orchestration : point d'entrée racine, neuf étapes explicites,
  conservation de chaque intermédiaire, checkpoints privés Modal, budgets nuls
  par défaut, reprise par plan et refus des appels payants de résultat incertain.
- [x] CPU : analyse automatique réutilisée, composition de masques et PiP,
  placement des voix à vitesse naturelle, contrôle des images et de l'audio.
- [x] Validation : tests de corruption, reprise après erreur, source modifiée,
  débordement vocal, plan manquant, PiP, protections avant dépense. Test court CPU
  sur les fichiers existants, CI GitHub, revue indépendante et PR non fusionnée.

Interfaces : `production.py --youtube URL --avatar default --voice default`;
recette `productions/UGCV2-FROZEN-RECIPE-20261030/source_recipe.json`;
implémentation `source_production.py`, `source_media.py` dans ce même dossier.
`RunState`, `RunLock`, `PrivateVolume`, `model_call`, ASR et traduction existants
sont réutilisés. Les moteurs fonctionnels restent inchangés.

Risques à tester : modification silencieuse de source; retrait d'une étape
terminée après crash; duplication d'un appel distant; mots tronqués par une
fenêtre trop courte; présence source dans les titres et les petites PiP.

La validation perceptuelle automatique, le détourage des objets/occlusions,
le décor récurrent sans présentateur et la stabilité du timbre sont des
qualifications à établir, jamais des booléens à inventer. La commande doit
conserver son analyse et retourner un rapport bloqué avant GPU si elles manquent.

Validation réelle : 76 tests locaux, 4 sous-tests ; quatre workflows GitHub
réussis (SOURCE_STATUS.json). Référence archivée et relue depuis Modal ; reprise
de l'analyse française dans un nouveau dossier sans recalcul. Défauts de budget
global et de vérification Student relevés par revue indépendante, tests RED puis
GREEN et corrections conservés. Les workers historiques sont inchangés.
La couverture automatique arbitraire des titres/PiP, la stabilité du speaker,
les validateurs perceptuels et l'export final autonome restent non réalisés.
