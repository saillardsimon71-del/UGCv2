# Préflight du 29 octobre 2026

- Base opérationnelle inspectée : production/portfolio-premium12-20261027, commit 388934c98aab6f6b47d2766f43e6983c3bbe78e1. main ne contient que le README.
- Secrets GitHub MODAL_TOKEN_ID et MODAL_TOKEN_SECRET présents, noms seulement lus. Leur workspace effectif sera contrôlé avec ces secrets sur le runner avant tout appel GPU.
- Profil Modal local authentifié : lucj76861, vérifié par Workspace.from_context().hydrate().name.
- Fonction existante hydratée : pvs-ltx/render_clip, environnement main, identifiant fu-Bs1p74vExLZMqQv9n3CHZP. Zéro entrée active et zéro backlog lors du préflight.
- Volume existant : studio-ltx25-models, vo-TH2UPlCqfA2pj7kBVhOtD3. Les cinq fichiers ont été listés et leurs tailles vérifiées par API de métadonnées, sans téléchargement, doctor ou calcul distant. Noms et tailles exacts dans PRODUCTION_PLAN.json ; vérification répétée sur le runner avant GPU.
- Les trois PNG 768x1344 ont été décodés et inspectés, avec originaux et SHA-256 conservés. Le WAV original stéréo 48 kHz dure exactement 15 secondes. Les trois payloads passent le validateur LTX existant.
- Huit tests CPU passent : fichiers absents/modifiés, relance GitHub, reçu préalable, mauvais workspace, modèles absents, annulation sur timeout sans nouvel essai, durée/absence d'écrêtage du WAV.
- Montage complet et décodage final vérifiés sur fixture CPU testsrc2 explicitement séparée de la production. Aucun MP4 de production n'existe encore. Résultat dans CPU_VERIFICATION.json.
- Workflow contrôlé avec actionlint 1.7.12 et parseur YAML. Déclenchement uniquement sur le push de la branche dédiée et message exact RUN_FRUIT_COSMIC_ASMR_20261029. Aucun workflow_dispatch, cron ou déclenchement d'une autre production.
- Calcul autorisé par la présente mission : trois appels maximum, un à la fois, un essai par plan. Délai client de 600 secondes par appel, annulation et arrêt au premier échec. Relances GitHub interdites par github.run_attempt et par le lanceur. Aucun déploiement, nouveau modèle ou publication.
- Le budget de workspace documenté par la campagne précédente est de 20 USD par mois, dernière observation le 28 octobre : 26,74 USD de crédits. Ces valeurs historiques ne sont pas prétendues actuelles. Trois fois 600 secondes au taux partiel du lanceur existant donnent environ 1,42 USD ; démarrage, retard d'annulation et facturation effective restent hors garantie. Aucun changement de budget effectué.
- Après le push : lire seulement l'identifiant et l'URL du run associé au commit puis arrêter immédiatement. Aucun suivi de rendu, logs, résultat ou artefacts dans Work.
