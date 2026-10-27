# Première preuve audiovisuelle : audit du 27 octobre 2026

État : trois vrais MP4 produits après autorisation explicite de dépense dans le chat.
Le troisième remplace la personne, les vêtements et le décor. PR #1 toujours draft.
La demande a été précisée : remplacer toute la personne et le décor. FaceFusion
reste limité au visage ; le test minimal utilise le worker LTX existant, sans
déployer de nouvelle application. Ce choix est une hypothèse à tester, pas une
preuve que LTX conservera les gestes ou remplacera complètement la scène.

## Vérifications et corrections

- Base inspectée : `cc22a0aee546f5a02a862b8fb0d9621e39e3d965`.
- CI GitHub relancée sans GPU, succès :
  https://github.com/saillardsimon71-del/UGCv2/actions/runs/40497929507
- Tests locaux : échec Windows reproduit dans le filtre de sous-titres des
  plaques de test, chemin corrigé ; les 12 tests passent ensuite, dont un nouveau
  contrôle du garde-fou du benchmark. Les tests de pipeline
  valident la plomberie avec simulations étiquetées, pas les modèles.
- Build TypeScript/Vite réussi. Syntaxe Python et YAML vérifiée.
- FaceFusion 3.5.1 : deux options inexistantes corrigées en
  `--output-video-encoder` et `--output-video-quality`. Valeur 90 sur l'échelle
  0-100, sans confusion avec CRF. Vérification statique contre le parseur officiel :
  https://github.com/facefusion/facefusion/blob/3.5.1/facefusion/program.py
- Suppression du repli silencieux sur la branche courante de FaceFusion et
  montage du cache au chemin réellement utilisé, `.assets/models`.
- Le diagnostic Modal ne lance plus de build ni de fonction distante sans
  `confirm_compute: oui`. Les erreurs de déploiement ne sont plus masquées.

## Accès et limites observés

- Aucun secret Actions du dépôt ni variable Actions n'est configuré. Aucune valeur
  de secret n'a été ajoutée au dépôt ni transférée vers GitHub.
- Un profil Modal local authentifié est disponible. L'identité du workspace
  et les métadonnées des apps ont été vérifiées par lecture seule.
- `pvs-ltx` et `pvs-longcat-avatar` sont déployées avec zéro tâche active au
  moment de la lecture. La fonction `pvs-ltx/render_clip` existe. Cela ne prouve
  ni les poids disponibles ni la version du code effectivement déployé. Le premier
  essai a ensuite démontré que sa version déployée ignore la vidéo source.
- Aucun appel `doctor.remote()`, téléchargement de poids ou préparation de modèle
  n'a été lancé. Après autorisation, un rendu a utilisé le déploiement existant
  et deux rendus ont exécuté temporairement le code du checkout avec `App.run`.
  L'application déployée existante n'a pas été remplacée. Le solde et la facture
  du compte ne sont pas attestés. La GTX 1060 locale dispose de 3 Go de mémoire ;
  aucune inférence locale n'a été tentée.
- Le workflow GPU S1 ne génère pas de vidéo : il déploie des workers, ignore
  certaines erreurs et cite `scripts/benchmark_modal.py`, absent du dépôt.
  Ne pas le prendre pour une preuve de rendu ni l'utiliser pour ce test.
- Le dry-run WanGP `validate` réserve un GPU. Les builds voix/lipsync/WanGP
  comportent des dépendances non épinglées et des erreurs ignorées. Ils restent
  hors du chemin de cette preuve.
- Les coûts du studio sont des estimations partielles et ne couvrent pas les
  échecs sans résultat. Ne pas les présenter comme une facture.
- Les entrées directes des anciens workers peuvent lancer du calcul sans le
  garde-fou de l'interface. Le script ci-dessous exige sa propre confirmation.

## Test préparé

Source : ANTONI SHKRABA production, Pexels 8135878 :
https://www.pexels.com/video/a-man-talking-to-the-camera-8135878/

Licence consultée : https://www.pexels.com/license/
Elle permet les modifications avec restrictions, notamment sur l'usage offensant
et le soutien implicite à un produit. Aucun accord individuel spécifique au
remplacement de visage n'est attesté. Le test reste une démonstration technique
neutre ; l'utilisateur a demandé de remplacer la personne et la scène.

Extrait de 2,00 à environ 8,04 secondes, rééchantillonné à 24 images/s :
145 images, 1344 x 768, durée 6,042 secondes. Source sans piste audio.
Objectif : femme fictive en chemise bleue dans une cuisine, avec ambiance sonore
native LTX. Aucun clonage de voix. Pas de photo d'identité réelle nécessaire.

`scripts/benchmark_ltx_minimal.py` valide localement les dimensions, le nombre
d'images et le payload/graphe du worker du dépôt. Par défaut il n'appelle aucun
calcul distant. En exécution autorisée, il cible la fonction déjà déployée ou,
avec `--use-checkout-worker`, exécute temporairement le code de la PR. Aucun
déploiement permanent ni nouvel essai automatique. La source effectivement
utilisée est vérifiée par son SHA-256 dans les métadonnées et par les noeuds
vidéo présents dans le graphe embarqué dans le MP4.

Exemple depuis la racine du dépôt, pour le précontrôle sans calcul :

```powershell
python scripts/benchmark_ltx_minimal.py --source ../../outputs/source_test_6s.mp4 --output-dir ../../outputs/preuve_v2v_strong_6s --workspace kulejean567 --use-checkout-worker
```

Le passage au calcul exige `--execute --confirm-spend oui` après autorisation
humaine explicite, accordée pour les trois essais de cet audit. Attente limitée
à 300 secondes puis demande d'annulation du
conteneur. Ce délai client n'est pas un plafond de facture garanti.

Après rendu : conserver le MP4 brut, vérifier toutes les images par décodage,
durée et audio ; produire un comparatif avec source à gauche, résultat à droite,
et mesurer le niveau audio et les secondes déclarées par le worker. Revue humaine
requise : personne et décor réellement remplacés, continuité des gestes, mains,
dents, texture de peau, scintillement et son. Aucun verdict visuel donné sans MP4.

## Résultats mesurés

| Essai | Calcul interne du worker | Estimation GPU + CPU + RAM | Résultat |
|---|---|---|---|
| Déploiement existant | 117,904 s | 0,0930 $ | Vrai MP4, mais source ignorée ; rejet comme preuve V2V |
| Checkout, sigma 0,85 | 112,849 s | 0,0890 $ | Source utilisée ; visage changé, décor et vêtements conservés |
| Checkout, sigma 0,975 | 106,886 s | 0,0843 $ | Personne, vêtements et décor changés ; gestes réinterprétés |

Total interne mesuré : 337,639 secondes. Estimation de ces ressources : 0,2664 $,
hors démarrage préalable, builds, arrêt et stockage. Ce n'est pas la facture.
Le sigma initial 0,85 retenait trop de l'image source. Le benchmark à 0,975 utilise
les quatre dernières étapes du calendrier de la première passe déjà présent dans
le worker ; ce réglage permet le remplacement complet sur cet extrait.

Troisième MP4 : H.264, 1344 x 768, 145 images à 24 images/s, 6,042 s.
Audio natif AAC stéréo 48 kHz, 6,010 s ; niveau intégré -31,7 LUFS,
crête vraie -15,5 dBTP. Ambiance discrète, aucune voix source à conserver.
Décodage intégral sans erreur et comparatif source à gauche / résultat à droite.

Revue visuelle sur images réparties et deux images pleine résolution : la femme
fictive en chemise bleue et la cuisine remplacent l'homme en polo dans le bureau.
L'identité et le décor sont cohérents dans les images examinées. La gestuelle et
le cadrage sont réinterprétés : pas de transfert fidèle du jeu d'acteur démontré.
La continuité fine du mouvement et l'écoute restent à juger par l'utilisateur.
Aucun moteur promu en production ; FaceFusion n'a pas été exécuté sur GPU.
Ce benchmark appelle directement le worker et ne prouve pas l'intégration V2V
dans l'interface du studio.

Le prototype a donc produit une première preuve audiovisuelle réelle et mesurée.
Il ne dispose pas encore d'une validation de qualité professionnelle générale.
Les applications temporaires sont arrêtées et aucune tâche du test ne reste active.

## Base de calcul des coûts

Tarifs consultés le 27 octobre 2026 : https://modal.com/pricing
Hypothèse : worker L40S, 8 coeurs CPU, 64 Gio RAM, tarifs standards.
GPU 0,000542 $/s + CPU 8 x 0,0000131 $/s + RAM 64 x 0,00000222 $/s
= 0,00078888 $/s. Scénarios : 60 s = 0,0473 $ ; 300 s = 0,2367 $.
Ce ne sont pas des durées prédites ni un devis. Démarrage, arrêt, stockage,
variations de ressources et tarifs effectifs peuvent modifier le total.
Le timeout du worker source est de 5400 s par défaut, environ 4,26 $ de ressources
à ces tarifs si l'annulation client échoue ; la configuration distante n'est pas attestée.
La facture réelle reste à consulter dans Modal ; les valeurs ci-dessus sont
des estimations fondées sur les temps retournés par les trois workers.
