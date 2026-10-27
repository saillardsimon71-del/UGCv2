# Exécution contrôlée

La branche de production dédiée réutilise exactement les fonctions Modal déjà déployées. Le nouveau fichier Actions est un lanceur de campagne et une conservation des médias, sans application, modèle ou infrastructure à créer.

1. Vérifier sans GPU : `python PRODUCTION/run_campaign.py check` depuis le dossier de campagne.
2. Déclenchement persistant du pilote beauté : commit vide dont le message est exactement `RUN_PREMIUM_03`, sur la branche `production/portfolio-premium12-20261027` d'UGCv2.
3. Chaque appel reçoit son PNG préparé, son prompt exact et son seed ; un essai, une fonction GPU à la fois. Les prises 01 et 02 sont archivées avant l'appel suivant. Le moindre échec interrompt le film. Aucune régénération automatique.
4. Récupérer l'artefact de livraison du run. Vérifier le dashboard, les trois prises et le montage. Le pilote intérieur se déclenche de même avec `RUN_PREMIUM_05` après contrôle de consommation.
5. Arrêter après les deux pilotes. La série nécessite une décision sur les vrais MP4 et une liste de films autorisés. Le lanceur refuse les autres films tant que `HUMAN_PILOT_APPROVAL.json` ne consigne pas une vraie validation ; ce fichier ne doit jamais être fabriqué pour contourner le contrôle humain.

Annulation : `gh run cancel RUN_ID --repo saillardsimon71-del/UGCv2`. Le lanceur intercepte SIGTERM et demande `FunctionCall.cancel(terminate_containers=True)`. Une étape Actions demande également l'annulation en cas d'échec. Pour un arrêt externe brutal, reprendre les call_id dans REPORTS et lancer `python PRODUCTION/run_campaign.py cancel --film IDENTIFIANT`. Ne pas arrêter une app partagée entière.

L'annulation est une demande à vérifier dans le dashboard. Si la confirmation d'extinction ou la consommation manque, suspendre les nouveaux appels. Le timeout client et le timeout Actions ne garantissent pas la facture. Le plafond workspace a été abaissé à 20 USD ; du stockage peut continuer à être comptabilisé. Cette mission ne démarre donc pas de série nocturne sans surveillance.

Les fichiers entrants sont Pexels. Les MP4 finaux ne sont créés que si les trois vrais rendus existent et passent le décodage. Un échec ne sera jamais remplacé par un diaporama ou une simulation. La miniature et le carton ne constituent pas des vidéos produites.
