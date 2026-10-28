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

## Exécution observée le 27 octobre

Le précontrôle GitHub 40569251898 a réussi et archivé les douze préparations. Le premier job pilote 40569401219 a été annulé pendant l'installation Ubuntu de ffmpeg ; ses trois étapes GPU ont été sautées. Une seule reprise CPU, 40570877880, a atteint son délai de cinq minutes à la même étape et s'est arrêtée sans appel GPU.

Le secours `PRODUCTION/local_pilot.py --film 03-skincare-sensoriel` réutilise les mêmes payloads et la fonction Modal déjà déployée. Il tourne dans un processus Windows séparé, fenêtre cachée, et écrit LOCAL_JOB.json, reçus par prise et journaux dans le dossier de campagne. Il survit à l'arrêt de la conversation mais ne démarre qu'un film explicitement sélectionné. Les prises sont séquentielles, sans reprise GPU automatique ; le premier échec arrête le processus. Le second pilote exige un lancement séparé après contrôle de consommation.

Le workflow dispose aussi d'un job d'archivage qui n'installe aucun outil et ne reçoit aucun secret Modal : message de commit `ARCHIVE_PREMIUM_PILOTS`. Il sert uniquement à conserver les vrais MP4 et rapports déjà produits localement.

## Lot validé le 28 octobre

Réponse humaine reçue : "Valider et lancer le lot de deux films". Le périmètre consigné dans HUMAN_PILOT_APPROVAL.json autorise exclusivement GOLDEN REVEAL puis ACCESSORY ICON. Le solde avant ce lot est de 29,20 USD, l'usage du cycle de 0,80 USD et la limite workspace de 20 USD. Les UGC 09 et 10 restent suspendus. La sélection pour publication reste ultérieure.

Le même lanceur local persistant accepte ces deux identifiants, avec un lancement séparé par film. Le second attend la revue du premier et son relevé de consommation. Aucune régénération automatique, aucun appel parallèle, aucune modification des workers. Annulation de la prise active : `python PRODUCTION/run_campaign.py cancel --film 02-golden-reveal` ou `--film 12-accessory-icon`. Vérifier ensuite l'absence d'entrée active et de file d'attente.

L'archive dédiée au lot se déclenche uniquement par le message `ARCHIVE_PREMIUM_LOT_02_12`. Elle conserve les quatre films réels, leurs sources, reçus, scripts et rapports pendant 90 jours, sans calcul Modal.

## Lot 07 + 08

Réponse humaine du 28 octobre : "Valider et lancer le prochain lot de deux films", après présentation du parfum V2 et du sac. Le même budget autorise PROBLÈME / SOLUTION puis PRODUCT ENERGY, un seul GPU, aucune reprise automatique. Le premier film est rejeté C pour incohérence des pages et élément ajouté en bas du plan final. Son vrai MP4 et ses coûts sont conservés. PRODUCT ENERGY poursuit ses trois prises sans dépendre de ce rejet. Le message ARCHIVE_PREMIUM_LOT_07_08 conserve les six dossiers comprenant l'essai C, sans calcul Modal.
