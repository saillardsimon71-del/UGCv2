# UGCv2 — Essai US → FR de 60 secondes : tutoriel à visuels mixtes

## Source et preuve

- Vidéo étudiée : https://www.youtube.com/watch?v=KSOxkhWs2Ic
- Fenêtre : **00:42.00–01:42.00** (60 secondes réelles).
- Vérification : GitHub Actions [40942927735](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40942927735) ; URL importée préexistante, empreinte du fichier intégral confrontée à l'audit source d'origine.
- Artifacts : `source_window_60s.mp4`, `contact_60s_real_frames.jpg`, `scene_analysis.json`, `source_provenance.json`.
- **Aucun GPU Modal utilisé à ce stade.**
- Usage strictement **privé de validation technique**. Ne pas publier la vidéo dérivée sans les droits nécessaires.

## Inspection visuelle effectuée sur les images authentiques

| Temps source (approx.) | Image | Politique de montage |
|---|---|---|
| 00:42.00–00:47.76 | Interface Zapier, PIP du créateur | Conserver les pixels de l'interface ; remplacer/masquer spécifiquement la PIP, sans recréer l'UI |
| 00:47.76–00:54.00 | Présentateur plein cadre | Reprise V2V ciblée puis TBDub FR sur ce seul plan |
| 00:54.00–00:57.36 | Titre plein cadre « TRIGGER » | Conserver le graphisme et sa durée ; éventuellement ajouter une traduction distincte en sous-titre |
| 00:57.36–01:03.12 | Interface Zapier et animation de dominos | Conserver l'animation et les cadres d'origine, aucune génération IA |
| 01:03.12–01:08.88 | Présentateur plein cadre | Reprise V2V ciblée puis TBDub FR |
| 01:08.88–01:11.76 | Capture d'écran bureau | Conserver la capture et les clics |
| 01:11.76–01:13.20 | Présentateur plein cadre (très court) | Éviter les passages incohérents : traiter ou remplacer par un cutaway source fidèle |
| 01:13.20–01:38.56 | Démonstration Zapier/Dropbox avec PIP | Conserver intégralement la lisibilité de l'interface. Remplacer PIP par avatar cohérent, ou l'omettre si l'overlay détruit l'UI |
| 01:38.56–01:42.00 | Présentateur plein cadre | Reprise V2V ciblée puis TBDub FR |

Les bornes de plan sont des **estimations vérifiées sur les contacts** et doivent être ajustées à la frame après inspection ; le scan automatique a trouvé 18 forts changements d'image, pas 18 décisions créatives certaines.

## Voix : préserver la diction et l'énergie d'origine

- **Ne jamais étirer ou comprimer l'intégralité du son français** pour le forcer à tenir dans 60 secondes.
- Extraire la piste de parole anglaise comme **référence de rythme** pour les silences, respirations et emphases (sans copier l'identité vocale du créateur sans autorisation).
- Traduire par **phrases synchronisées avec les actions affichées**, pas par un paragraphe monolithique.
- Six blocs de 10 secondes *au maximum*, et de préférence les frontières naturelles de la narration ; chaque bloc possède sa propre pause et durée cible.
- Chatterbox Multilingual V3 déjà installé : privilégier une voix conversationnelle *sans l'accélération ressentie dans le précédent test*. Comparer des réglages de débit à l'oreille avant le GPU des lèvres.
- Si une prise française ne rentre pas naturellement dans son intervalle, **adapter le texte** plutôt que monter la vitesse avec `atempo`.
- TBDub Student v1.1 uniquement sur les segments de visage réellement visibles, avec l'audio exact utilisé pour le mix final.

## Acceptation du test d'une minute

1. Durée finale 60,0 s ± 0,2 s, 16:9, piste française continue.
2. Images de Zapier, Dropbox, titre et dominos conservées nettes, textes non hallucinés.
3. Gestes du présentateur et identité du nouvel avatar stables d'un plan à l'autre.
4. Lèvres crédibles lors de la parole ; pas de bouche déformée, ni de barbe ou dents instables.
5. Cadence, pauses et énergie comparables aux phrases anglaises, sans synthèse à débit excessif.
6. Comparaison avant/après et audio FR isolé livrés pour évaluation.
7. Rendu limité à une branche expérimentale ; rien de fusionné dans le moteur stable et aucune publication.

## Exécution suivante (non démarrée)

Faire valider/produire les **prises vocales françaises minutées** et une première composition CPU avec visuels originaux. Uniquement ensuite, lancer les **quelques plans V2V nécessaires** et la synchronisation TBDub avec plafond de coût, sans traiter les interfaces par IA.

**Statut : SOURCE ET DÉCOUPAGE VISUEL VÉRIFIÉS ; AUCUN RENDU 60S TRANSFORMÉ N'A ENCORE ÉTÉ EFFECTUÉ.**
