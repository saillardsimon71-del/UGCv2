# Benchmarks — démontrer avant de produire

La vraie question du brief : *« un spectateur trouverait-il cette vidéo
parfaitement crédible au premier visionnage ? »* Aucun score automatique ne
répond à cela. Chaque capacité gagne donc sa place sur une **scène courte,
comparable et conservée**, jugée à l'œil. On ne produit du long que lorsque
le court est convaincant.

## Règles communes

- Même source, même personnage, même texte pour les deux moteurs comparés.
- Sources **autorisées** uniquement (la photo `benchmarks/character_reference.png`
  fournie avec le dépôt ; vos propres vidéos/voix consenties).
- Conserver : source, chaque résultat, temps GPU, coût, notes de défauts horodatées.
- Jugement : revue humaine du studio (checklist par type + note /5).
  **Seuil de promotion en « production » : ≥ 4/5, toutes cases cochées,
  sur 2 visionnages** (dont un sans le son, un en plein écran).
- Regarder en priorité : identité dans les rotations, lèvres (b/m/p/f),
  dents/langue, mains et contacts, raccord cou, lumière, stabilité entre segments.

## Les 5 scènes

### S1 — Remplacement de visage (FaceFusion vs Animate 2 premium)
Source : vidéo 10 s, face caméra → 3/4 → main qui passe devant le visage →
retour face. Visage cible : Élise (référence du dépôt).
À trancher : effet masque ? raccord cou ? occlusion main propre ? identité en 3/4 ?
Procédure studio : recette « Remplacer un visage », qualité Production
(FaceFusion), générer ; puis mode avancé `modal_animate2`, générer ; comparer A/B.

### S2 — Nouveau dialogue (MuseTalk vs LatentSync 1.6)
Source : vidéo de parole 12 s. Nouveau texte FR piégeux, ex. :
« Bonjour, bienvenue ! Papa prépare un fabuleux buffet : pommes, mamans,
bébés — tout le monde participe, même en février. »
À trancher : fermetures bilabiales, dents stables, aucune dérive à 12 s,
halos autour de la bouche. Mesurer les secondes GPU/seconde de vidéo des deux.

### S3 — Personne & mouvement (Animate 2 vs SCAIL-2)
**Étape 0 obligatoire** : workflow « Modal — benchmark GPU », scène
`S3-perf-validate` (dry-run WanGP : valide le format settings sans générer).
Source : 8 s — marche vers la caméra, geste de la main, saisie et pose d'un
objet. Personnage : Élise. Modes animation puis remplacement.
À trancher : mains (déformations), contact objet, morphologie en marche,
intégration au décor. Le gagnant devient le défaut des recettes B et C.

### S4 — Avatar parlant & voix (LongCat 1.5 vs InfiniteTalk ; Chatterbox vs Seed-VC)
Photo Élise + texte FR de ~20 s. Deux voix : (a) synthèse Chatterbox clonée,
(b) votre propre enregistrement converti par Seed-VC. Écouter d'abord les
voix seules (respirations, timbre stable, pas de métal). Puis avatar :
LongCat (segments enchaînés — valider la continuité d'identité aux raccords),
InfiniteTalk si déployé. À trancher : naturel du jeu pendant les pauses,
regard, gestuelle liée au propos — le critère « pas une photo dont la bouche bouge ».

### S5 — Publicité complète 30 s (seulement après S1–S4 convaincants)
Storyboard 5 plans (hook avatar, problème, démo générée LTX, preuve,
CTA avatar) + montage studio. Jugement global « spectateur » + **coût par
vidéo acceptée** (tous les essais et échecs inclus, onglet coûts du projet).
C'est la scène qui décide si le studio est vendable à un client.

## Journal des résultats

| Scène | Date | Moteurs | Verdict /5 | GPU s | Défauts dominants | Décision |
|---|---|---|---|---|---|---|
| — | — | — | *aucun benchmark exécuté à ce jour* | — | — | Voir STATE.md |

Remplir une ligne par exécution, sans embellir : un échec documenté vaut
mieux qu'un succès inventé. Mettre à jour `docs/STATE.md` et, si promotion,
`maturity` dans `backend/app/engines/modal_remote.py`.
