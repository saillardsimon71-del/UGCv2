# Fraise cosmique - plan d'exécution

Objectif autorisé : préparer trois plans de cinq secondes, déclencher un seul run GitHub Actions puis arrêter Work dès confirmation du lien.

Base : production/portfolio-premium12-20261027, 388934c98aab6f6b47d2766f43e6983c3bbe78e1. Aucun fichier de cette campagne ni worker déployé ne sera modifié.

1. Créer trois PNG réels par génération d'image intégrée puis éditions avec référence, conserver les originaux, normaliser à 768x1344 pour LTX et inscrire les SHA-256. Inspecter visuellement les trois états.
2. Ajouter uniquement cette production et un workflow ciblant la branche production/fruit-cosmic-asmr-20261029. Réutiliser les helpers command/probe/save et le validateur LTX existants. Le petit lanceur dédié évite les hypothèses Pexels, musique et carton final propres à l'ancienne campagne.
3. Tester refus d'image absente/modifiée, de relance et de reçu existant avant tout accès distant. Vérifier les vrais fichiers, les secrets présents et le workspace lucj76861. Lister les cinq modèles existants sans les télécharger, sans doctor ou redéploiement.
4. Un seul processus, trois appels maximum à pvs-ltx/render_clip, zéro nouvel essai. Chaque appel a un délai client de 600 secondes puis annulation. Interdire GITHUB_RUN_ATTEMPT > 1 et refuser une fonction occupée. Aucun autre modèle, service ou compte.
5. Montage ffmpeg CPU : trois coupes de cinq secondes, 360 images à 24 i/s, 1080x1920. Pas de texte, narration, musique ou carton. Bruitages synthétisés originaux, pistes natives exclues. Placement des quatre accents affiné sur les pics de mouvement dans les fenêtres de coupe prévues. Cette heuristique requiert une écoute et une revue visuelle ultérieures, hors mission.
6. Tests CPU de l'assemblage sur fixtures explicitement identifiées comme tests, validation syntaxique et contrôle du diff. Un seul push avec le message de déclenchement dédié. Lire uniquement l'identifiant du run correspondant au SHA puis STOP. Aucun suivi de résultat, log ou téléchargement.

Limites : LTX génère 121 images en 768x1344 par prise, recadrées/agrandies au montage. La continuité animée, la précision des coupes et une boucle parfaite ne sont pas garanties par les images de départ. Aucun rendu n'est annoncé avant sa production. Aucun export n'est publié automatiquement.
