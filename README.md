# Studio UGC v2 — studio audiovisuel IA professionnel

**On commande une vidéo, pas un pipeline.** Vous décrivez le résultat voulu,
vous fournissez vos sources (vidéo filmée, photos, voix, texte), le studio
choisit la méthode, génère plan par plan, vous gardez les meilleures prises,
il monte, sous-titre et exporte un fichier livrable.

Philosophie : partir d'une **vraie performance filmée** quand elle existe et
ne remplacer que ce qui doit l'être (visage, personne, dialogue, timbre).
La génération de zéro est un outil parmi d'autres, pas le défaut.

## Les 7 productions

| Intention | Vous fournissez | Le studio fait |
|---|---|---|
| 🪞 Remplacer un visage | vidéo + photo | même performance, autre visage |
| 👤 Remplacer la personne | vidéo + photo | même jeu/décor, autre personne |
| 🎭 Transférer une performance | vidéo de référence + photo | vos mouvements, joués par elle/lui |
| 💬 Faire dire un autre texte | vidéo + texte/audio | nouvelle voix + lèvres resynchronisées |
| 🎙️ Avatar parlant | photo + texte/audio | personne qui parle face caméra |
| 🗣️ Voix seule | texte, ou votre enregistrement | synthèse clonée, ou timbre converti en gardant votre jeu |
| 🎬 Créer de zéro | brief | storyboard → plans → voix → montage → export |

Moteurs (open source, GPU Modal à la demande, 0 € au repos) : FaceFusion,
Wan2.2 Animate 2 & SCAIL-2 via WanGP, LatentSync 1.6 / MuseTalk,
LongCat Avatar 1.5, LTX-2.5, Chatterbox V3, Seed-VC. Choix argumentés dans
[docs/DECISIONS_ENGINES.md](docs/DECISIONS_ENGINES.md) ; honnêteté d'état dans
[docs/STATE.md](docs/STATE.md) — **aucun moteur n'est vendu comme « production »
avant d'avoir gagné sa scène de benchmark à l'œil**
([docs/BENCHMARKS.md](docs/BENCHMARKS.md)).

## Démarrer

```bash
make install   # venv Python + interface
make run       # UI + API sur http://localhost:8000 (données de démo amorcées)
make test      # 11 tests : routeur, pipeline, montage, QC, garde-fous
make demo      # chaîne studio complète sans GPU (export SIMULATION étiqueté)
```

Sans GPU, tout fonctionne sauf les rendus IA (plaques « SIMULATION »
explicitement étiquetées — jamais présentées comme des rendus). Pour les
vrais rendus : 2 secrets GitHub + workflow diagnostic, voir
[docs/MODAL.md](docs/MODAL.md). LTX-2.5 et LongCat Avatar sont déjà déployés
et prouvés sur le compte Modal existant.

## Documentation

- [Guide utilisateur](docs/GUIDE_UTILISATEUR.md) — produire en 6 temps, réflexes qualité
- [Décisions moteurs](docs/DECISIONS_ENGINES.md) — pourquoi ces modèles, par capacité
- [Benchmarks S1–S5](docs/BENCHMARKS.md) — protocoles, seuils, journal des résultats
- [Modal](docs/MODAL.md) — mise en service GPU, garde-fous de dépense, dépannage
- [Architecture](docs/ARCHITECTURE.md) — routeur, plans/prises, QC deux niveaux, coûts
- [Licences à vérifier](docs/LICENCES_A_VERIFIER.md) — avant tout usage commercial

## Règle qualité du studio

Un plan n'est livrable qu'à **≥ 4/5 en revue humaine**, checklist complète
(identité, lèvres, expression, mains/dents). Le QC automatique ne juge que
l'emballage (format, durée, audio, noirs, loudness) — la crédibilité pour un
spectateur reste un jugement humain, tracé dans chaque plan.
