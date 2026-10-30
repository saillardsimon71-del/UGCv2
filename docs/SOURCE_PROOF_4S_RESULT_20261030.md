# Preuve réelle 4 secondes — mouvement guidé par la source

GitHub Actions : https://github.com/saillardsimon71-del/UGCv2/actions/runs/41081121485  
Branche : `test/source-performance-4s-proof-20261030`  
PR : https://github.com/saillardsimon71-del/UGCv2/pull/9  
Statut GitHub : **success**  
Statut qualité vidéo : **DIAGNOSTIC_PRIVATE_UNVALIDATED** — jamais approuvée automatiquement.

## Reçus du job GitHub

- `FACEFUSION_PASS_COMPLETE` ; une seule invocation A10G, avatar de référence inchangé
- `BACKGROUND_PASS_COMPLETE` ; segmentation + nouveau décor CPU
- `FACE_PREFLIGHT_PASSED` ; avant toute invocation TBDub
- `TBDUB_PASS_COMPLETE` ; une seule invocation L40S
- Aucun appel Chatterbox ou LTX
- 4 secondes, 100 images, 1920 x 1080, 25 i/s
- MP4 SHA-256 : `cd31de8d7ecd9f5a8bf407753cde3cf5166d90b1bb47e55fc55e1aeb673a3e46`
- Audio FR SHA-256 d'entrée : `fd8b89cd036c29eba0ef41187f3024647cebdaba76dd67b029d909ed3487238e`
- Corrélation PCM zéro décalage de la voix source avec le mux : `0.999986`, sans étirement
- Réservations GPU maximales : 3 000 secondes au total **non représentatives du coût facturé**
- Aucune nouvelle minute, aucun déploiement des workers historiques
- Visage entier, casquette/cheveux/torse, contours du micro, qualité bouche et naturel : **À ÉVALUER À L'ŒIL**
- Le compte rendu ne prétend pas que tous les attributs de l'avatar soient remplacés ni que le décor soit parfait

## Récupérer les vrais fichiers sur le PC

Utiliser le profil Modal existant `lucj76861`, depuis PowerShell, puis :

```powershell
modal volume get ugcv2-production-private /source-proof-results/source-performance-4s-once-20261030 .\UGCv2_4s_result
```

À regarder : `UGCv2_SOURCE_PERFORMANCE_4s_PRIVATE_DIAGNOSTIC.mp4`, `original-source-4s.mp4`, `identity-facefusion-4s.mp4`, `new-background-4s.mp4`, `review-before.jpg`, `review-identity.jpg`, `review-new-background.jpg`, `review-after-tbdub.jpg`.

Tous les fichiers sont dans le volume privé; **aucune vidéo de référence ou donnée privée dans GitHub Actions public**. Ne pas fusionner ni déduire qu'une URL quelconque fonctionnera avant validation visuelle.
