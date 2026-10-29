# Visual Engine CPU - plan d'exécution

Spécification : mission utilisateur du 29/10/2026 et SCRIPT_FR.md.
Choix d'implémentation : Pillow + FFmpeg, sans modifier graphics.py ni assembly.py.
Les scènes sont des illustrations originales, sans média source. La voix utilise
System.Speech local si une voix fr-FR est disponible ; silence explicite sinon.

- [x] Contrat JSON validé : templates, durée, données fictives, provenance.
- [x] Tests d'abord : refus de médias externes, géométrie/texte, temps de transition,
  durée voix, encodage réel, annulation et contrat Engine UGCv2.
- [x] Templates paramétrables : accroche, workflow, interface, graphique, conclusion.
- [x] CLI reproductible, voix locale en cache, montage via AssemblyEngine existant.
- [x] Entrée URL : analyse séparée, état partiel explicite en cas d'accès refusé.
- [x] Pilote uniquement, 30-60 s, H.264 1080p30, QC décodage + images inspectées.
- [x] Rapport mesuré et tests existants.
- Livraison : commit/push de cette seule branche.

Limites à vérifier : accès YouTube sans authentification ; classification visuelle
CPU indicative ; qualité de la voix locale ; captures n8n réelles hors pilote.
Pas de génération du film complet, déploiement, publication ni appel Modal.
