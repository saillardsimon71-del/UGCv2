# LIFESTYLE DEMONSTRATION : storyboard de production

Durée cible : 22.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-7.0 s

- Description : Présentation neutre ; plan bloqué tant que source frontale et droits ne sont pas validés.
- Cadrage : Portrait au miroir, casting non validé
- Caméra : Fixe
- Lumière : Salle de bain réelle, lumière du jour cohérente dans le miroir.
- À préserver : Même adulte, pyjama bleu à liseré, miroir, lavabo, flacons et mains anatomiquement correctes.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 10222471.
- Moteur : LongCat Video Avatar 1.5, INT8, 480p ; pvs-longcat-avatar/render_avatar ; A100-80GB.
- Son : Introduction parlée sous réserve casting
- Raccord : Coupe vers mains
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
A neutral scripted French product demonstration presenter in the exact real bathroom shown in the reference. Preserve the same adult stock model, tied-back hair, pale blue piped pajamas and honest skin texture. Static camera, calm conversation, natural subtle expressions and precise audio-driven lip synchronization. The bathroom mirror must show a physically consistent reflection of the same motion. No claims of personal experience, no product endorsement, no customer testimonial, no face replacement, no new packaging, no extra fingers, no text or logos. Benchmark only until the casting and reflection have been reviewed.
```

## Plan 02 : 7.0-13.0 s

- Description : Un petit mouvement crédible au-dessus de la paume, sous narration.
- Cadrage : Démonstration pipette et paume
- Caméra : Fixe
- Lumière : Salle de bain réelle, lumière du jour cohérente dans le miroir.
- À préserver : Même adulte, pyjama bleu à liseré, miroir, lavabo, flacons et mains anatomiquement correctes.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 10222458.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Narration continue, goutte si visible
- Raccord : Retour contexte
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Realistic daily skincare demonstration using the same authentic bathroom photo. Preserve the exact adult model's face, tied-back hair, pale blue pajamas, existing dropper, open palm and amber bottle. Only a tiny controlled wrist adjustment over the open palm, then a pause. Keep five correct fingers, rigid glass, consistent reflection and unchanged room. Closed lips during this non-speaking cutaway. No new bottle, no face transformation, no text, branding or product claims, no camera move, no cut. No generated voice or music.
```

## Plan 03 : 13.0-20.0 s

- Description : Fin du geste sans déplacer la gamme.
- Cadrage : Plan vie quotidienne et produit
- Caméra : Recul de 2 cm
- Lumière : Salle de bain réelle, lumière du jour cohérente dans le miroir.
- À préserver : Même adulte, pyjama bleu à liseré, miroir, lavabo, flacons et mains anatomiquement correctes.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 10221851.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Fin de voix et ambiance
- Raccord : Mention démonstration scénarisée
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Quiet lifestyle closing insert from the exact same real bathroom source. Preserve the white sink, chrome faucet, amber bottles, pale blue pajama sleeve and original hand. Slow two-centimeter pullback, stable natural daylight and truthful product proportions. The hand relaxes without picking up an object. Keep every mirror and bottle edge consistent. No extra person, new item, lettering, logo, cut or product claim. No voice or music in the generated clip; the final narration is mixed later.
```

## Plan 04 : 20.0-22.5 s

Carton fixe CPU : LE MATIN, SIMPLEMENT / Démonstration scénarisée.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.

## Suspension

SUSPENDU_INTERACTION_HUMAINE : source actuelle avec miroir et personne réelle, inadéquate pour garantir un avatar fictif et une parole synthétique autorisée. Casting photographique frontal sous autorisation et benchmark LongCat nécessaires. Aucun GPU pour ce film.

Les images présentes sont des références de casting, pas une personne fictive créée ni une autorisation de lui faire prononcer un texte.

Script exact envisagé :

Voici une façon de présenter ce rituel du matin : d'abord le produit, puis le geste, dans son vrai décor. Le cadrage reste simple pour voir ce qui se passe. Rien à surjouer : on montre, et on laisse le produit parler.

Sous-titres : transcription mot pour mot après production d'une voix autorisée ; aucune vitesse ou synchronisation déclarée avant écoute.
