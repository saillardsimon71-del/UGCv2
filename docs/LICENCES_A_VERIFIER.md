# Dépendances à vérifier avant usage commercial

Le brief place les licences **hors périmètre de la première mission
technique** ; ce fichier consigne ce qu'il faudra vérifier avant de vendre
des prestations. Rien ici n'est un avis juridique.

| Dépendance | Usage dans le studio | Point à vérifier |
|---|---|---|
| InsightFace / inswapper_128(_fp16) | Face swap (FaceFusion) | Code MIT mais **modèles à usage non commercial** par défaut d'après l'éditeur ; licence commerciale séparée. Alternatives à benchmarker : simswap 256/512, hyperswap. |
| Poids LatentSync 1.6 | Lip-sync | Code Apache-2.0 ; poids annoncés sous licence de type OpenRAIL++ (restrictions d'usage) — confirmer la version exacte téléchargée. |
| MuseTalk | Lip-sync brouillon | Code MIT, modèle utilisable commercialement ; dépendances (Whisper, VAE) chacune sous leur licence ; matériel de test du dépôt non commercial (nous n'utilisons que nos sources). |
| Wan2.2 Animate 2 / SCAIL-2 | Personne/mouvement | Annoncés Apache-2.0 — confirmer sur les model cards des checkpoints réellement téléchargés par WanGP (variantes quantifiées DeepBeepMeep incluses). |
| WanGP | Substrat d'exécution | Licence du dépôt + celles des modèles qu'il télécharge (au cas par cas). |
| LongCat-Video-Avatar 1.5 | Avatar | Poids MIT d'après le dépôt — confirmer la version 1.5. |
| LTX-2.5 | Génération vidéo | Conditions Lightricks du checkpoint exact présent dans le volume existant. |
| Chatterbox (Resemble AI) | TTS | Licence du dépôt/modèle multilingue V3 + conditions d'usage des voix clonées. |
| Seed-VC | Conversion de voix | Licence du dépôt et des encodeurs utilisés. |
| GFPGAN / CodeFormer | Restauration visage | Licences respectives des poids téléchargés par FaceFusion. |
| Droits à l'image / à la voix | Toutes références | Autorisation écrite des personnes (ou personnages synthétiques). Le studio exige une case de confirmation par référence, mais ne peut pas la vérifier. Mentions légales de contenu généré selon plateforme/pays de diffusion. |

Règle de conduite d'ici la vérification : benchmarks uniquement sur sources
autorisées, aucune livraison client sur un moteur dont la ligne ci-dessus
n'est pas close.
