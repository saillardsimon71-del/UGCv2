# Lancement et limites

## Nouveau diagnostic 4s, strictement privé et non validé

Le profil `work-diagnostic-4s-v1` raccorde une clause inutilisée de la source
autorisée à la traduction CPU, à une seule voix V3 (conditionnement par défaut et
réglages de référence), puis à un unique LTX et un unique TBDub. Il continue le
dernier master natif conservé. Tous les mots et échantillons de la nouvelle voix
doivent tenir naturellement dans 4s; sinon arrêt avant LTX, sans accélération.

```bash
gh workflow run ugcv2-golden-cpu.yml --repo saillardsimon71-del/UGCv2 --ref stabilization/work-golden-locked-20261030 -f profile=work-diagnostic-4s-v1 -f run_id=work-new4s-20261030-once
python productions/UGCV2-FROZEN-RECIPE-20261030/production.py fetch-diagnostic --run-id work-new4s-20261030-once --output ./diagnostic-prive
```

L'identifiant de cette mission est fixe : changer d'identifiant ne réinitialise
pas les limites. Le journal réserve au maximum un appel par moteur, sans retry.
Un seul candidat voix est produit. Les poids voix sont ceux déjà en cache,
snapshot épinglé, avec téléchargement de modèles désactivé. Les workers existants
ne sont pas modifiés ni redéployés.

La commande de récupération normale refuse le statut
`DIAGNOSTIC_PRIVATE_UNVALIDATED`. Seule `fetch-diagnostic` récupère ce résultat
pour examen humain, avec `publish_allowed: false`. Aucun fichier média n'est
publié par Actions. Les contrôles perceptifs demeurent non qualifiés, même si le
décodage, le visage détecté et l'intégrité audio passent. Les WAV de référence et
de la nouvelle prise sont conservés pour une comparaison à l'écoute.

Résultat du dispatch unique 41048730461 : arrêt `NARRATION_TEXT_MISMATCH`
avant tout appel LTX/TBDub. La nouvelle voix complète est conservée (1,84 s),
mais l'ASR ne confirme pas tous les mots attendus. Ce contrôle seul ne distingue
pas une prononciation TTS incorrecte d'une erreur ASR. Aucun autre modèle relancé.
Il n'existe donc pas de nouveau MP4 présentateur pour cette exécution.

Récupérer les fichiers existants du run bloqué, comme diagnostic privé :

```bash
modal volume get ugcv2-production-private /runs/work-new4s-20261030-once ./diagnostic-echec
```

Branche : `stabilization/work-golden-locked-20261030`, PR #7, sans fusion.
Ce n'est pas encore un moteur qualifié pour une nouvelle URL quelconque.

## Exécution du passage approuvé, sans agent

Le catalogue privé Work a été installé une fois dans le volume Modal
`ugcv2-production-private`, workspace `lucj76861`. Il contient maintenant aussi
le premier master LTX natif manquant dans le ZIP initial. Les références sont
contrôlées par SHA-256 et restent privées. Aucun secret existant remplacé.

```bash
gh workflow run ugcv2-golden-cpu.yml --repo saillardsimon71-del/UGCv2 --ref stabilization/work-golden-locked-20261030 -f profile=work-reference-v1 -f youtube_url=https://www.youtube.com/watch?v=KSOxkhWs2Ic -f run_id=ma-reference-001
```

Cela utilise uniquement la fenêtre privée 49,60-57,60 s déjà travaillée, la voix
française et les deux prises réellement approuvées. Ce n'est pas un nouveau
téléchargement YouTube, une nouvelle traduction ou une nouvelle performance.
`studio.py` réalise le montage plein cadre, titre déjà composé, PiP et démonstration.
La coupe de silence est commune aux images et aux échantillons audio.

Le rapport seul est disponible dans les artifacts GitHub. Aucun MP4, master,
audio ou transcript privé n'est publié dans les artifacts du dépôt public.

Récupérer le MP4 avec les identifiants Modal existants :

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/production.py fetch --run-id ma-reference-001 --output ./mes-resultats
```

Relancer avec le même identifiant reprend les étapes vérifiées, sans régénération.
Un changement de code, profil ou entrée impose un nouvel identifiant. Les sorties
modifiées ou incomplètes sont refusées. Un fichier rejeté ne peut pas être récupéré
comme livrable : le statut du rapport ET l'empreinte du MP4 doivent correspondre.
Les verrous locaux se libèrent même si le processus est tué. Actions sérialise les
productions. Ne pas lancer le même identifiant depuis deux machines simultanément.

## Nouvelle URL : chemin CPU et arrêt explicite

```bash
python productions/UGCV2-FROZEN-RECIPE-20261030/production.py run --url "https://www.youtube.com/watch?v=VIDEO_ID" --profile work-locked-v1 --run-id projet-001 --private-remote --max-gpu-seconds 1800
```

Le profil sait valider une URL, télécharger dans la limite de 15 minutes / 1 Go,
normaliser la vidéo, chercher les visages sur chaque image, transcrire avec le
modèle CPU épinglé, et traduire l'anglais vers le français sur CPU. Les autres
langues, téléchargements indisponibles et alignements incertains sont refusés.
La traduction automatique n'est pas une adaptation éditoriale garantie.

L'exécution s'arrête AVANT toute synthèse voix ou vidéo au contrôle
`LIPSYNC_VALIDATOR_UNQUALIFIED`. Les adaptateurs V3, LTX et TBDub existent, vérifient
les interfaces et conservent leurs sorties, mais leur enchaînement sur une nouvelle
URL n'est pas encore qualifié ni démontré. Le planificateur et la composition
audio avec extension de durée sont testés sur des médias synthétiques.

Restent bloquants :

- Vérificateur lipsync phonétique et identité, calibré sur les clips Work acceptés
  et les essais 20/60 s rejetés. Les mesures ORB de décor ne le remplacent pas.
- Classification fiable des titres superposés et rectangles PiP inconnus. La
  présence/absence d'une boîte de visage ne prouve pas la bonne composition.
- Identité vocale entre plusieurs phrases V3 et branchement complet de la chaîne
  nouvelle narration -> nouvelle timeline -> prises -> évaluation -> montage.
- Rejet/reprise individuels après contrôle perceptif : journal et adaptateurs
  existent, mais il manque le verdict automatique qualifié qui pilote ces reprises.

La réserve GPU est persistée AVANT soumission. Une reprise retrouve l'identifiant
Modal ou refuse un appel incertain, sans le resoumettre. Les quatre secondes,
seed, prompt, normalisation, versions et workers restent ceux de `recipe.json`.
Les fichiers de code sont vérifiés avec normalisation des seules fins de ligne
Windows/Linux; les médias sont toujours vérifiés octet par octet.

## Contrôles et coûts

Les tests vérifient les corruptions, reprises, appels dupliqués, budget, chemins,
frontières de mots, conservation de phrases plus longues que l'original, coupe
simultanée audio/vidéo et refus d'un livrable rejeté. Ils ne prouvent pas le naturel.
Le profil de référence compare toutes les images au MP4 approuvé, décode le MP4
entier et compare l'audio PCM sans décalage. L'ASR sur ce court extrait est un
diagnostic, pas une certification : un mot peut avoir une durée nulle en bordure.
Pour du contenu inédit, cette incertitude bloque la production.

Le test de référence n'appelle aucun GPU. Le coût CPU, stockage et transfert n'est
pas chiffré ici; seul le tableau de facturation Modal peut confirmer une facture.

```bash
python -m unittest discover -s productions/UGCV2-FROZEN-RECIPE-20261030 -v
```

Installation locale : Python 3.11 et FFmpeg, puis
`pip install -r productions/UGCV2-FROZEN-RECIPE-20261030/requirements-production.txt`.
La traduction nécessite aussi PyTorch >=2.6; le workflow installe PyTorch 2.8 CPU.
