# Consommation : estimation provisoire au 28 octobre

Workspace : lucj76861. Quatre films réels, douze prises IA abouties et un démarrage annulé pendant les pilotes. Aucun secret, moteur, modèle ou profil recréé. Aucun téléchargement de poids ou build Modal par cette campagne.

| Mesure | Valeur | Nature |
|---|---:|---|
| Crédits avant la mission | 29,80 USD | Tableau de bord arrondi |
| Usage du cycle avant la mission | 0,20 USD | Tableau de bord arrondi |
| Crédits avant le lot 02 + 12 | 29,20 USD | Relevé du 28 octobre |
| Crédits après le lot 02 + 12 | 28,55 USD | Relevé provisoire |
| Usage total du cycle après les quatre films | 1,45 USD | Relevé provisoire |
| Consommation estimée de la campagne | Environ 1,25 USD | Différence des crédits, pas une facture |
| Consommation estimée du lot 02 + 12 | Environ 0,65 USD | Différence des crédits, pas une facture |
| Somme interne des douze rendus aboutis | 1,1315 USD | Estimation worker partielle |
| Dont lot 02 + 12 | 0,5936 USD | Six prises abouties, zéro relance |
| Facture définitive de campagne | Non disponible | Non déclarée connue |
| Limite mensuelle totale configurée | 20 USD | Vérifiée dans le dashboard |
| Réserve à préserver | 10 USD | Solde observé supérieur à la réserve |

Le dashboard reste asynchrone : le dernier total est 1,45 USD pour 28,55 USD de crédits, mais la ventilation affiche 1,40 USD d'apps déployées et 0,20 USD d'apps éphémères. Ces lignes ne s'additionnent pas au total. Ne pas les présenter comme une facture rapprochée. Les relevés datés et captures sont conservés localement ; les captures financières ne sont pas publiées dans le dépôt.

Les estimations worker multiplient les secondes internes retournées par le scénario L40S + 8 coeurs CPU + 64 Gio. Elles omettent une partie du démarrage préalable, de l'extinction, du stockage et d'éventuels dépassements mémoire. Les prises échouées ne valent jamais zéro par défaut. Le montant réellement facturé par film n'est pas attesté.

Les deux premiers pilotes totalisent 0,5379 USD de worker partiel. Un premier appel avait été annulé vers 22 secondes à cause d'une erreur d'attente du lanceur ; un seul nouvel essai manuel a été effectué après correction testée sur CPU. Le lot 02 + 12 n'a connu aucun échec ni régénération. Les V2 du sérum et du parfum sont des recoupes CPU des vrais rendus, avec musique remélangée et effets recadrés.

Les deux jobs GitHub interrompus à l'installation CPU n'ont exécuté aucune étape GPU. Les frais éventuels de minutes ou stockage GitHub ne sont pas certifiés par ce relevé Modal.

Les processus des quatre films sont terminés. LTX indique zéro entrée active, zéro file d'attente et zéro conteneur. Aucun appel UGC n'a été lancé. La limite workspace et les délais client ne constituent pas une garantie inventée de facture exacte : aucune série payante nocturne sans surveillance. Ce relevé clôt le lot 02 + 12, avant le démarrage du lot 07 + 08 validé ensuite par le client.
