# Audit nécessaire à la production

27 octobre 2026. Aucune migration, recréation de secret ou modification de modèle effectuée.

- UGCv2 : main ne contient que le README. La base opérationnelle est `arena/e9d26fb3-ugcv2`, commit vérifié `6662985c97e9b4e6a72f2a30ab0ee421c16d3f8a`, celui du [diagnostic réussi](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40559624267).
- Profil local actif : lucj76861. Volumes existants : `studio-ltx25-models` et `pvs-longcat-models`. Le reçu de migration existant atteste les cinq fichiers LTX, 39 689 918 812 octets. Il est réutilisé, sans nouveau téléchargement ni nouveau doctor payant.
- Déploiements lus : `pvs-ltx`, app `ap-kFsOQpOnaDv4Qd2Zv8jCvq`, et `pvs-longcat-avatar`, app `ap-Yv4IodjzGDTrdKbsL8WJr1`. Zéro tâche active à l'inspection initiale. Une app déployée ne suffit pas à prouver sa qualité artistique.
- Interface LTX réellement lue : `render_clip(payload)`, PNG base64, prompt, durée 1-15 s, aspect 9:16, seed, `image_strength`, audio natif ou silencieux. Sortie `video_base64` et `metadata`. Pour les pilotes : 5 s demandées, 121 images / 24 i/s = 5,042 s, 768 x 1344, INT8 distilled, 8 étapes puis passe d'agrandissement latent. Montage coupe à 5,000 s. Le master 1080 x 1920 sera recadré et agrandi, pas une génération native 1080p.
- Modèles LTX : révision `49b093a39c19169a8a81721dcc541e07e945232f`. ComfyUI : `d49e888586dd8ae012c0667b33466b815fee07f7`, d'après le code et le diagnostic conservé. Les reçus de rendu permettront de vérifier la version réellement retournée.
- Limites LTX source : L40S, 8 coeurs CPU et 64 Gio réservés, un conteneur, extinction après 2 s, timeout de fonction source 5400 s. L'annulation client à 600 s ne garantit pas un plafond financier. Pas de changement de configuration distante.
- Interface LongCat réellement lue : `render_avatar(image_b64, audio_b64, prompt)`, PNG et PCM WAV, jusqu'à 40 s, segments natifs 93 puis 80 images à 25 i/s, INT8 480p, A100-80GB. La sortie 720 x 1280 est recadrée/agrandie. Les films 09 et 10 restent suspendus faute de casting photographique adapté à une parole synthétique autorisée et de benchmark de qualité sur ces prises.
- Nouveau-studio : les précédents ECLAT 02 et PULSE 01 utilisaient H3. Les deux MP4 locaux ont été réellement décodés pour extraire des planches à 1 image/s et les planches ont été inspectées. Enseignements : garder une seule gamme de produit, des gestes courts et des raccords simples. Aucune écoute critique ni inspection continue de ces anciens films n'est prétendue ici.
- H3 n'apparaît pas parmi les apps du workspace définitif. Le réutiliser exigerait une installation ou un transfert supplémentaire ; il est écarté de cette campagne, sans accès à l'ancien compte. Les fonctions de montage ffmpeg déjà éprouvées servent de base au montage CPU adapté aux nouveaux plans.

## Recherche et droits des médias

43 photographies candidates ont été téléchargées depuis le CDN Pexels puis décodées et inspectées en planches. Seules les sources inscrites aux plans entrent dans les créations. Les packagings Chanel, Givenchy, Fire et les sacs portant des marques reconnaissables ont été rejetés. Les originaux et recadrages sélectionnés restent dans chaque dossier ASSETS avec URL et empreinte.

La [licence Pexels](https://www.pexels.com/license/) permet l'usage publicitaire et les modifications, avec notamment l'interdiction d'un soutien implicite par les personnes ou marques. Aucune collaboration avec une marque ni recommandation personnelle n'est inventée. Les personnes visibles sont des modèles de stock dans une mise en scène, jamais des clients de SiteQuiVend. Pour les avatars parlants, l'autorisation individuelle de parole synthétique n'est pas établie : suspension explicite.

Les références de grandes campagnes servent uniquement à l'étude de la lumière, de la composition et de la structure. Aucun extrait publicitaire, bande-son, logo ou personnage de ces campagnes n'est incorporé. Les pages, descriptions et images disponibles ont été consultées ; aucune revue intégrale de leurs films n'est prétendue.

Musique exécutée : Reverie et Catalyst, Scott Buckley. Le téléchargement direct du fournisseur a répondu HTTP 406 pendant la préparation ; les fichiers complets déjà présents dans les précédentes productions sont réutilisés, avec crédit et licence [Reverie](https://www.scottbuckley.com.au/library/reverie/) / [Catalyst](https://www.scottbuckley.com.au/library/catalyst/) vérifiés sur le site de l'auteur. Aucun achat ni génération musicale facturable. La référence créative Helios, également documentée chez l'auteur, n'est pas la piste d'exécution de ces dossiers.

La [licence LTX-2.x](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x) impose notamment un contrat commercial séparé aux entités atteignant 10 millions USD de revenus annuels. Ce seuil et les obligations de publication devront être confirmés par le responsable avant usage client ; le dossier ne constitue pas une certification juridique générale. Les pilotes sont conservés pour inspection, pas publiés.

## Conservation

La limite d'artefacts de UGCv2 lue via l'API GitHub est de 90 jours. Le workflow demande 90 jours, et l'expiration effective de chaque artefact produit devra être lue après exécution. Les anciens artefacts ECLAT/PULSE du run 40302562256 expirent le 25 novembre 2026. Le diagnostic Modal ne contient aucun artefact média : ne pas y chercher les nouveaux films.

Les nouveaux MP4 seront téléchargés localement en plus de leur artefact GitHub. Aucun showreel et aucune modification de SiteQuiVend.fr dans cette mission.
