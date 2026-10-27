# Modal — activer les vrais rendus GPU

État de départ : votre compte Modal contient déjà, **prouvés par des MP4
réels** (ancien studio), `pvs-ltx` (LTX-2.5, L40S) et `pvs-longcat-avatar`
(LongCat 1.5, A100 80 Go) avec leurs volumes de poids. Le nouveau studio les
appelle tels quels — rien à réinstaller pour la vidéo et l'avatar.
Les 4 nouvelles capacités ont leurs propres apps/volumes `ugc-*`, déployées
une par une, benchmark après benchmark. **Aucune ne tourne au repos**
(`min_containers=0`, `scaledown_window=2`, `max_containers=1`).

## 1. Secrets GitHub (une fois, ~2 minutes, faisable depuis l'iPhone)

Dans **ce** dépôt (UGCv2) : Settings → Secrets and variables → Actions →
*New repository secret* :
- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`

Valeurs : dashboard Modal → Settings → API Tokens (les mêmes que ceux de
l'ancien studio si vous les avez conservés). **Ne les envoyez jamais dans un
chat.** Recommandé : variable `STUDIO_MODAL_WORKSPACE` = nom du workspace
affiché dans le dashboard (le studio refusera de dépenser sur un autre compte).

## 2. Diagnostic sans calcul par défaut

Onglet **Actions** → *Modal - diagnostic (lecture seule par défaut)* → Run workflow :
- prouve l'identité du compte **lue sur le jeton** (seuls workspace et utilisateur sont affichés) -
  le nom d'une app ne prouve jamais un compte ;
- liste apps et volumes existants ;
- Sans `confirm_compute: oui`, seules les métadonnées du compte sont lues.
- Avec `confirm_compute: oui`, `deploy_first: true` déploie un worker (build d'image CPU) puis lance son
  `doctor()` (état des modèles, versions). Le premier build peut prendre
  plusieurs minutes. Builds, calcul CPU et stockage peuvent être facturés :
  aucun de ces appels n'est gratuit par le seul fait de ne pas utiliser de GPU.

## 3. Ordre de mise en service recommandé

| Étape | Workflow / action | Coût | Ce qu'elle prouve |
|---|---|---|---|
| 1 | Diagnostic (`confirm_compute: non`) | Aucun calcul distant | Le compte, les apps et volumes déjà là, pas l'état des poids |
| 2 | Benchmark `S3-perf-validate` (`confirm_spend: oui`) | quelques minutes de conteneur | Le format WanGP est accepté (dry-run) avant tout rendu long |
| 3 | Déployer `ugc-voice`, tester une voix dans le studio | L4, secondes | Écoute réelle Chatterbox FR |
| 4 | `S2` : prepare lipsync (CPU) puis scène studio | A10G, minutes | MuseTalk vs LatentSync à l'œil |
| 5 | `S1` : déployer `ugc-face`, scène studio | A10G, minutes | Face swap jugé |
| 6 | `S3/S4` complets, puis `S5` | L40S/A100 | Promotion production par capacité |

## 4. Brancher le studio (machine qui sert l'UI)

```bash
pip install -r backend/requirements-modal.txt
modal token set --token-id <id> --token-secret <secret>   # ou `modal setup`
STUDIO_MODAL_ENABLED=1 STUDIO_MODAL_WORKSPACE=<workspace> STUDIO_ALLOW_MOCK=0 make run
```

Dans l'UI, chaque production affiche alors les moteurs réels dans son plan ;
**la dépense part uniquement si la case « Je confirme la dépense GPU » est
cochée** (garde-fou aussi côté moteur : sans `confirm_spend`, refus explicite).

## Garde-fous intégrés

- Annuler un job dans l'UI tue le conteneur GPU (`terminate_containers=True`).
- Timeout dur 35 min côté studio ; 1 GPU à la fois (`max_containers=1`).
- Le workspace est vérifié sur le jeton si `STUDIO_MODAL_WORKSPACE` est défini.
- Les rendus réussis retournent des secondes utilisées pour une estimation GPU.
  Le studio ne comptabilise pas actuellement les échecs sans résultat, le démarrage,
  le CPU/RAM et le stockage. La facture Modal reste la référence.
- Le solde Modal n'est pas lisible par API : il se vérifie dans le dashboard
  (Settings → Billing). Aucun de nos écrans ne prétend l'avoir vérifié.

## Dépannage fréquent

- « Application injoignable » → le worker n'est pas déployé : workflow
  diagnostic avec `deploy_first: true` pour ce worker.
- « Poids absents » (lipsync) → `modal run deploy/modal_lipsync_worker.py --mode prepare`.
- Settings WanGP refusés → voir la sortie du dry-run, ajuster
  `_build_settings` dans `deploy/modal_perf_worker.py` (clés média), re-valider.
- LongCat accepte une piste WAV jusqu'à 40 s avec continuation native. Une
  production anglaise de 35,12 s a été générée et décodée intégralement avec
  ce chemin. Les segments restent liés dans le moteur ; aucun redémarrage
  indépendant n'est requis entre les phrases.
