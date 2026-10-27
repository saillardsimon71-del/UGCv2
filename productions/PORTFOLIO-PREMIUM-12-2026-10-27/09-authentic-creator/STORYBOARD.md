# AUTHENTIC CREATOR : storyboard de production

Durée cible : 22.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-7.0 s

- Description : Petites expressions, lèvres synchronisées à la voix ; aucun produit ajouté dans les mains.
- Cadrage : Portrait face caméra, référence de casting
- Caméra : Fixe smartphone
- Lumière : Fenêtre diffuse, cadrage smartphone stable et sans effet glamour.
- À préserver : Identité de l'interprète de stock et tenue, lèvres et dents stables ; flacon identique à l'insert.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 7959590.
- Moteur : LongCat Video Avatar 1.5, INT8, 480p ; pvs-longcat-avatar/render_avatar ; A100-80GB.
- Son : Voix : première phrase du script
- Raccord : Coupe franche sur insert produit
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
A clearly scripted product presenter performance using the same adult stock model in the reference photo, preserving her exact face, short blonde hair, cream jacket and white top. Static natural smartphone camera. She speaks the separately provided French narration with relaxed eye contact, subtle blinks and small believable expressions. Hands remain still and out of the close framing. Preserve facial identity, teeth, lips, clothes and soft neutral background. No new product in her hands, no extra fingers, no beauty filter, no exaggerated expression, no logos or generated text. This is an actor role, not a customer testimonial.
```

## Plan 02 : 7.0-13.0 s

- Description : Flacon immobile sous la narration.
- Cadrage : Insert sérum fidèle
- Caméra : Fixe, léger reflet
- Lumière : Fenêtre diffuse, cadrage smartphone stable et sans effet glamour.
- À préserver : Identité de l'interprète de stock et tenue, lèvres et dents stables ; flacon identique à l'insert.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 8101534.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Voix continue, détail verre très bas
- Raccord : Retour vers portrait
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Natural skincare insert from the authentic source photograph. Preserve the exact burgundy bottle, completely blank white label, glass pipette with white bulb, wooden support and frosted jar. Static camera, subtle soft window reflection, realistic glass and paper. No moving container, no label text, no logos, no hands or added product. Single continuous photographic shot. No speech or music in the generated source track; a licensed narration is added later.
```

## Plan 03 : 13.0-20.0 s

- Description : Fin de phrase et pause, sans sourire figé ni geste commercial.
- Cadrage : Même portrait
- Caméra : Fixe
- Lumière : Fenêtre diffuse, cadrage smartphone stable et sans effet glamour.
- À préserver : Identité de l'interprète de stock et tenue, lèvres et dents stables ; flacon identique à l'insert.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 7959590.
- Moteur : LongCat Video Avatar 1.5, INT8, 480p ; pvs-longcat-avatar/render_avatar ; A100-80GB.
- Son : Fin de voix, pause de 0,5 s
- Raccord : Mention présentation scénarisée
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Continuation of the same scripted French presenter performance from the provided reference. Preserve the exact adult stock model's face, short blonde hair, cream jacket, white top and neutral background. Static smartphone framing and natural window light. Accurate gentle lip synchronization to the provided final phrase, subtle natural head motion, a relaxed pause after speaking. No exaggerated smile, no nod loop, no identity drift, no new objects, no product endorsement or customer-testimonial acting, no generated words or logos.
```

## Plan 04 : 20.0-22.5 s

Carton fixe CPU : LE GESTE SIMPLE / Présentation scénarisée.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.

## Suspension

SUSPENDU_AVATAR_ET_CASTING : photographie de personne réelle, rôle scénarisé seulement. Pas d'avatar fictif garanti, pas d'autorisation individuelle de parole synthétique attestée et aucun benchmark premium de LongCat sur ce casting. Aucun coût GPU engagé pour ce film.

Les images présentes sont des références de casting, pas une personne fictive créée ni une autorisation de lui faire prononcer un texte.

Script exact envisagé :

Pour ce rituel, tout commence par un geste simple. On prend le temps de regarder la texture, puis on laisse le produit trouver sa place. Une goutte, un moment, et une présentation qui va à l'essentiel.

Sous-titres : transcription mot pour mot après production d'une voix autorisée ; aucune vitesse ou synchronisation déclarée avant écoute.
