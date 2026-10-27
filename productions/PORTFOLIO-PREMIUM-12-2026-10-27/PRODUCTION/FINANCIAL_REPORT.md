# Consommation : estimation provisoire

Workspace utilisé par la mission : lucj76861. Aucun secret, profil, moteur déployé ou modèle n'a été recréé. Pas de téléchargement de poids ni de build Modal par cette production.

| Mesure | Valeur | Nature |
|---|---:|---|
| Crédits avant la mission | 29,80 USD | Tableau de bord arrondi |
| Usage du cycle avant la mission | 0,20 USD | Tableau de bord arrondi |
| Crédits après les deux pilotes | 29,20 USD | Relevé provisoire |
| Usage du cycle après les deux pilotes | 0,80 USD | Relevé provisoire |
| Différence attribuée à la fenêtre de campagne | Environ 0,60 USD | Estimation par différence, pas une facture |
| Somme interne des six rendus aboutis | 0,5379 USD | Estimation partielle GPU + CPU/RAM réservés |
| Facture définitive de campagne | Non disponible | Non déclarée connue |
| Limite mensuelle totale configurée | 20 USD | Vérifiée après rechargement |
| Réserve à préserver | 10 USD | Solde observé supérieur à la réserve |

La ventilation du dashboard a temporairement affiché 0,62 USD d'apps déployées et 0,20 USD d'apps éphémères pour un total de 0,80 USD. Au dernier rechargement, elle affiche 0,60 USD d'apps déployées + 0,20 USD d'apps éphémères = 0,80 USD, avec 29,20 USD de crédits. Les compteurs visibles sont alors cohérents, sans constituer une facture définitive. Les captures restent dans le dossier local, sans être publiées dans le dépôt.

Les 0,5379 USD résultent des secondes internes retournées par six vrais rendus, multipliées par le scénario de ressources L40S + 8 coeurs CPU + 64 Gio. Ce chiffre n'est pas une facture complète. Démarrage préalable, ressources réellement consommées au-delà de la réservation, extinction, éventuel stockage/egress et un démarrage annulé ne sont pas intégralement ventilés par ces reçus. La différence de dashboard donne une estimation plus large, toujours provisoire.

Un premier appel a été annulé vers 22 secondes à cause d'une erreur d'attente du lanceur. Il est conservé dans le journal des sept appels ; son coût n'est pas considéré comme nul faute de MP4. Après correction testée sur CPU, un unique nouvel essai manuel a produit le plan. Aucun autre plan n'a été régénéré. La V2 du sérum a uniquement été recoupée sur CPU.

Les deux jobs GitHub interrompus à l'installation CPU n'ont exécuté aucune des trois étapes GPU. Ils ne constituent pas une dépense Modal de rendu. Le coût éventuel de stockage/minutes GitHub n'est pas certifié par ce relevé Modal.

La limite mensuelle est une protection supplémentaire, pas une garantie inventée de facture exacte par script. Aucune série payante nocturne n'est lancée. Les deux processus locaux sont terminés et les compteurs LTX indiquent zéro entrée active, zéro file d'attente et zéro conteneur. Le prochain lot attend la validation artistique des vrais pilotes, dans le budget de campagne déjà autorisé.
