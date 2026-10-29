# Pilote 001 — Automatiser les demandes de devis avec l'IA (France)
## Cible : tutoriel YouTube FR original, 6:45–7:45

**Référence de veille (pas média source)** : https://www.youtube.com/watch?v=KSOxkhWs2Ic (The AI Advantage, `AI Automation: Complete Beginners Guide`).
**Preuve d'analyse** : transcription complète anglaise récupérée le 29/10/2026 ; elle explique un trigger nouveau fichier Dropbox, appel ChatGPT via Zapier, sauvegarde du texte, publication du Zap. La vidéo n'est ni de Liam Ottley ni un tutoriel présentant trois business différents.

**Notre réalisation FR originale** :
- Titre de travail : **« J'ai automatisé les demandes de devis d'un artisan avec l'IA (sans coder) »**.
- Démo française **fictive, identifiée** : entreprise de plomberie fictive à Rouen recevant une demande de dépannage ; aucun client ni résultat commercial réel revendiqué.
- Outils : n8n + Mistral API. Workflow exécuté **manuellement** pour la démo (pas d'envoi automatique au client), test sur entrée fictive.
- Valeur pédagogique : montrer l'enchaînement entrée structurée → classification et brouillon IA → **validation humaine**, avec coûts, erreurs et RGPD.
- Différences substantielles : nouveau problème métier, nouvel exemple et données, nouveaux outils, démonstration originale, logique d'approbation humaine, règles françaises, texte et visuels nouveaux.
- Pas de téléchargement, face swap, doublage ou remploi des images, extraits ou voix de la vidéo américaine.

## Pipeline UGCv2 SANS modification du moteur

1. **SCRIPT_FR.md** : narration originale, ~7 minutes, 9 passages, ton direct.
2. **PLAN_SHOTS.json** : liste de plans, sources et preuves demandées. La majorité de la vidéo est constituée de **captures n8n réelles** et de narration.
3. **n8n/demo_devis_mistral.json** : brouillon de workflow n8n importable, credentials absentes volontairement. Rien n'est envoyé à un vrai client.
4. **tests/validate_project.py** : valide localement JSON, entrée fictive, cohérence des connexions et la présence d'un vrai moteur IA dans la proposition.
5. Une fois le workflow n8n importé et la clé Mistral **configurée dans n8n**, capturer une vraie exécution avec des données fictives, des résultats réellement observés et ses éventuels messages d'erreur.
6. La voix doit être rendue par un moteur **vérifié à l'écoute** ; `ugc-voice` est écrit mais **non encore prouvé** dans la branche stable. Une voix témoin inventée ou un écran de démonstration ne doit pas être présenté comme une vraie exécution.
7. Montage FFmpeg via UGCv2, QC technique (loudness/sous-titres) + QC humain (voix, vérité des écrans, lisibilité, rythme). Pas d'upload public automatique.

**État aujourd'hui** : projet préparé ; **pas de vidéo finale produite, pas de faux workflow exécuté**. Pour produire le pilote audiovisuel, il faudra fournir les captures d'écran de l'exécution, valider une voix, puis assembler.

## Confidentialité et honnêteté
- Utiliser des coordonnées de test `example.com`, jamais de vrais messages clients ou clés API dans Git.
- Pas d'envoi d'e-mail automatique dans ce pilote ; le modèle propose des brouillons à approuver.
- Ne pas promettre d'économie de temps, de revenu, de résultat ou de conformité RGPD sans mesure et vérification.
- Mettre à jour le statut réel de production uniquement après les étapes effectivement testées.

## Note coût
n8n autohébergé n'est pas forcément « gratuit » en exploitation (hébergement et maintenance), et l'API de Mistral peut être facturée. Les appels Modal ne sont **pas autorisés** par ce dossier de préparation ; toute génération GPU demandera une décision séparée.

## Pilote Visual Engine CPU

Un extrait graphique original de 53,8 secondes est maintenant produit dans
`VISUAL_OUTPUT/PILOTE_VISUAL_ENGINE_FR.mp4`. Il comporte une voix française locale,
des schémas et des maquettes portant le badge ILLUSTRATION - DONNÉES FICTIVES.
Ce pilote ne constitue pas une capture d'exécution n8n/Mistral ni le film complet.
Le statut de préproduction de `PLAN_SHOTS.json` reste donc valable pour les
captures réelles demandées dans ce plan.

Code, reproduction, résultats des tests et limites : [VISUAL_REPORT.md](VISUAL_REPORT.md).
