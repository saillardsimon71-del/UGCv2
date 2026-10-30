# Audit de la méthode de référence UGCv2

## Référence vérifiée

- Run : https://github.com/saillardsimon71-del/UGCv2/actions/runs/40957764927
- Commit : `406e8d6fd27ba6fdd9c120b92ee2cb6154d09176`.
- MP4 : `UGCv2_FR_60s_TBDub_HYBRID_TEST.mp4`, 13 856 195 octets.
- SHA-256 recalculé : `346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d`.
- 1 500 images, 1920 x 1080, 25 i/s, 60 s. Décodage complet contrôlé.
- Artefact 12934462682, ZIP SHA-256 annoncé par Actions :
  `c39e292f019f08bea97e276825677026b103fa9f83ccb980a8d8257912d8dec6`.

Le run est daté du 29 octobre à 21:26 UTC. Le nom "méthode du matin" est une
référence qualitative utilisateur ; l'identifiant et l'empreinte ci-dessus
identifient précisément le fichier audité, sans déduction fondée sur son nom.
Les scripts historiques et les quatre workers utilisés sont identiques entre ce
commit et la base `ab4544d` de cette branche, comparaison Git effectuée.

Les reçus récupérés, leurs empreintes et les sept phrases réellement choisies
sont conservés dans
[`SOURCE_REFERENCE_EVIDENCE.json`](../productions/UGCV2-FROZEN-RECIPE-20261030/SOURCE_REFERENCE_EVIDENCE.json).
Les médias restent dans les artefacts d'origine et les copies locales de travail.
Une archive durable est aussi conservée dans le volume Modal privé existant,
préfixe `reference/source-performance-346b8a25/` : source, mix voix, remplacement
de visage et hybride. Le master a été relu depuis ce volume et vérifié par SHA.
La référence de comparaison ne dépend donc plus de l'expiration des artefacts Actions.

## Chaîne réellement exécutée

| Étape | Entrée et traitement constatés | Preuve |
|---|---|---|
| Import | Vidéo `KSOxkhWs2Ic`, fenêtre 42-102 s, normalisée à 25 i/s. Import via le pont vidIQ existant, pas via LTX. | Run 40942927735 ; `source_and_scenes.py` et reçu source |
| Alignement | Transcription anglaise horodatée pour repérer les plages de parole. | Run 40944640728 ; `transcribe_timing.py` |
| Français | Sept textes adaptés aux actions visibles, écrits dans `BLOCKS`. Synthèse Chatterbox Multilingual, `t3_model="v3"`, `language_id="fr"`, voix générique intégrée, aucun clonage du présentateur. | `build_french_voice_and_preview.py`, `modal_chatterbox_v3_fr_pilot.py` |
| Reprises voix | 7 x 2 auditions initiales (40945609860), reprise des cinq dernières phrases (40947229775), dernière phrase seule (40948222718). Les premières prises acceptées sont réutilisées. | `retake_overfast_blocks.py`, `retake_final_folder_line.py` et métadonnées finales |
| Mix voix | Prises complètes insérées à leurs débuts anglais, pauses conservées, aucune accélération ni étirement global. | WAV SHA `f6423ee2de8340ecbf5fc2609a2b29dae1525d336e678310be39e7c4f06506cf` ; timeline des prises |
| Identité | FaceFusion 3.5.1, `face_swapper` + `face_enhancer`, `inswapper_128_fp16` + `gfpgan_1.4`, sélection `one`, ordre `large-small`, A10G. Quatre plans seuls. | Run 40955263301 ; `render_selected_faces_60s.py`, `modal_fr60_faceswap_selected.py` |
| Lèvres | Entrées : ces vidéos issues de la source et l'audio FR extrait aux mêmes temps. TBDub Student v1.1, L40S, deux pas, sigma 1.0, seed 42, `--motion-from-latents`. | `composite_hybrid_tbdub_60s.py`, `modal_tbdub_fr_worker.py`, quatre résultats vérifiés par SHA |
| Montage | Réinsertion des quatre résultats à leurs temps source, fond de montage issu de la vidéo originale traitée par FaceFusion. Audio FR complet ajouté une fois. H.264 CRF18, AAC192k, 48kHz. | Étape `assemble` du compositeur historique |

Les quatre plages traitées étaient [5,76 ; 12,00[, [21,12 ; 26,88[,
[29,76 ; 31,20[, [56,56 ; 60,00[ secondes locales. Les quatre lipsyncs ont
effectivement produit un MP4, y compris le plan court. Le GPU TBDub a rapporté
230,12 s pour le lot. Ce chiffre n'est pas une facture ni le temps de toutes les
étapes en amont.

## Pourquoi les mouvements et les visuels étaient meilleurs

Les gestes, postures, regards et mouvements de tête venaient de la performance
filmée. FaceFusion modifiait une région du visage ; il ne recréait ni corps ni
mouvement complet. TBDub recevait une vidéo, puis réinsérait sa région faciale
traitée dans cette vidéo. Le fonctionnement décrit par
[l'amont TBDub](https://github.com/TaoLiveAIGC/TBDub) correspond aux arguments et
aux artefacts observés. Aucune invocation LTX ne figure dans cette chaîne finale.

Les interfaces et schémas n'étaient pas envoyés au générateur vidéo. Ils ont
subi la compression du montage final : "préservés" ne signifie donc pas
"octets vidéo strictement identiques". La narration suivait les sept débuts de
phrase source et les textes avaient été allongés après écoute/mesure, plutôt
que de ralentir artificiellement une voix trop courte.

L'appréciation de naturel et de lipsync est celle donnée par l'utilisateur à ce
fichier. Les empreintes, images, durées et reçus sont des preuves techniques ;
ils ne mesurent pas à eux seuls cette appréciation perceptuelle.

## Où l'identité et le décor restaient proches de la source

1. **Aucun remplacement de décor.** Aucune segmentation ni image de fond n'est
   utilisée dans le run final. Le visage peut changer tout en gardant casquette,
   cheveux, vêtements, silhouette, micro et pièce d'origine.
2. **PiP exclue des deux traitements.** Le script FaceFusion annonce lui-même
   `PIP_presenter: unmodified`. Le compositeur final indique également l'absence
   de lipsync sélectif PiP. Le spectateur retrouve donc directement l'acteur source.
3. **Couverture incomplète des apparitions.** L'audit ultérieur des frontières
   `FR60-PRESENTER-PROOF-20261030/AUDIT.md` recense notamment le visage derrière
   "TRIGGER", une PiP intermédiaire et le retour final. Ces passages ne sont pas
   représentés correctement par les quatre fenêtres fixes. Cet audit antérieur
   constitue la provenance du découpage détaillé ; aucune nouvelle certification
   image par image de ses frontières n'est revendiquée ici.
4. **Contrôle d'identité insuffisant.** Le test historique mesure une différence
   de pixels dans un rectangle. Les MAE observées sont d'environ 5,1 à 6,4, mais
   cette mesure ne prouve ni la ressemblance à notre avatar ni la disparition de
   l'identité source. Son message "Identity did not change" était plus affirmatif
   que son pouvoir de mesure.
5. **Sélection des visages.** Le premier worker laissait le mode par défaut
   `reference`, confirmé dans la [documentation FaceFusion](https://docs.facefusion.io/usage/cli-arguments/face-selector).
   Le correctif utilisé ici impose `one`. Cela corrige cette sélection pour une
   source à un seul intervenant ; cela ne qualifie pas automatiquement les plans
   à plusieurs visages, les profils ou les incrustations minuscules.

## Régressions des méthodes suivantes : causes vérifiables

| Changement | Conséquence technique certaine | Limite de la conclusion |
|---|---|---|
| Pilote CPU `pilot_pip_scene_consistency.py`, commit `0adb17b6d065d583f4466af7b079a391c5cc2199` | La PiP prend `cam_a_tbdub_french.mp4` en boucle via un modulo. Ses mouvements et lèvres appartiennent à un autre passage. Le script reconnaît l'absence d'alignement audio et les gestes répétés. | Explique cette désynchronisation, sans prétendre noter subjectivement tout le MP4. |
| Même pilote, détourage humain | MediaPipe conserve une matte de personne, pas une garantie sur micro, table, objets ou titre semi-transparent. Les faibles couvertures pouvaient revenir à l'image d'origine. | Le nouveau compositeur refuse ce retour silencieux et conserve la matte. |
| Photographie animée par LTX | `animation.json` indique `continuity_mode: image`, `source_video: null` ; `provenance.json` indique que la vidéo source ne conduisait pas la génération. Les gestes source ne peuvent donc pas être conservés. | Le test court a pu être apprécié ; cela ne prouve pas que LTX est mauvais en général. |
| Normalisation d'une sortie 24 i/s et image finale réutilisée | Nouvelle performance, raccords à gérer, risques de dérive et de répétition absents d'un simple traitement de la vidéo source. | La continuation courte avait des contrôles techniques réussis ; elle ne résout pas le transfert de performance arbitraire. |
| Silence retiré de la référence 8 s vers 6,52 s | Montage accepté sur cet extrait, mais changement du timing original. | Ce montage particulier n'est pas la recette générale demandée ici. |

## Décision de production

Conserver FaceFusion et TBDub comme composants existants d'une **chaîne issue
de la vidéo source**. Conserver Chatterbox V3 et la pose des phrases à leurs
temps d'origine. Réutiliser le détourage CPU déjà présent, avec refus en cas de
masque invalide. Traiter chaque PiP avec **son propre passage vidéo et son audio**.
Ne pas boucler un présentateur pour remplir une autre scène.

Le worker WanGP de transfert de performance présent dans le dépôt n'est pas une
solution démontrée : sa référence est `main`, ses clés de média sont explicitement
marquées "à confirmer" et son en-tête dit "NON EXÉCUTÉ sur GPU". Il n'a donc pas
été substitué aux composants prouvés. Aucun nouveau moteur vidéo n'a été ajouté.

Cette décision ne suffit pas à qualifier FaceFusion pour transformer un homme
avec cheveux/casquette en notre personnage chauve, ni à qualifier tous les
cadrages. Le pipeline conserve ce blocage d'identité, au lieu de présenter un
changement local de pixels comme une réussite complète.

## Limites de reproductibilité retrouvées

Le code Chatterbox est épinglé, mais son chargement `from_pretrained` n'épingle
pas toutes les révisions des poids. Sa voix intégrée n'est pas un speaker lock
vérifié entre phrases. Les bibliothèques des images Modal ne sont pas toutes
figées par un lockfile et aucun digest complet d'image exécutée n'est fourni
dans ces reçus. Les WAV candidats ne sont pas tous présents dans l'artefact final,
alors que le mix complet l'est. On peut reprendre les fichiers existants par
empreinte ; promettre leur régénération bit à bit serait injustifié.

L'autonomie complète reste bloquée par la couverture automatique fiable des
scènes/PiP/titres, l'identité complète, les contours du détourage, le timbre stable
et un contrôle phonétique calibré. Ces limites sont aussi inscrites dans la
recette et dans le rapport de fonctionnement.
