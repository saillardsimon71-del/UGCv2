# TRANSFORMATION : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Ambiance de jour neutre ; la lampe reste à faible intensité.
- Cadrage : Plan d'ensemble lampe et rideau
- Caméra : Fixe
- Lumière : Évolution graduelle de l'intensité de la lampe ; rideau et meuble identiques ; pas de changement de soleil.
- À préserver : Dôme, base, pied, table et plis des rideaux ; aucun meuble ajouté entre les ambiances.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 4612402.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Ambiance claire sans clic
- Raccord : Raccord fixe vers l'allumage
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Realistic home lighting advertisement from this exact photograph of the white dome table lamp. Preserve its round white shade, slim straight stem, circular base, wooden table and every curtain fold. Locked camera, no object motion. Calm neutral daytime ambience with the existing lamp glow held at a low subtle level, soft cool-white room light. Keep the lamp shape, scale and contact shadows absolutely consistent. No new furniture, no moving curtains, no people, no labels, no text, no logo, no cut. No voice or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Le halo chaud augmente progressivement ; aucune transformation du décor.
- Cadrage : Même cadre strict
- Caméra : Verrouillée
- Lumière : Évolution graduelle de l'intensité de la lampe ; rideau et meuble identiques ; pas de changement de soleil.
- À préserver : Dôme, base, pied, table et plis des rideaux ; aucun meuble ajouté entre les ambiances.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 4612402.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Clic doux à synchroniser sur hausse réelle du halo
- Raccord : Coupe dans la même ambiance chaude
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
A precise lighting transformation in the exact same photographed room. Locked camera with absolutely unchanged framing. Preserve the same white dome lamp, straight stem, circular base, wooden table and cream curtain folds. Over this continuous shot the existing warm glow under the lampshade slowly increases from subtle to comfortably warm, gently illuminating the nearby curtain and wood. This is only a change in light intensity, not a scene transformation. All geometry, objects and positions remain rigid. No room redesign, no curtain morphing, no hands, no extra light source, no text, no logo, no cut. No speech or music.
```

## Plan 03 : 10.0-15.0 s

- Description : Maintien de l'ambiance finale pour le bénéfice et le CTA.
- Cadrage : Détail dôme, pied et bois
- Caméra : Recul optique de 2 cm maximum
- Lumière : Évolution graduelle de l'intensité de la lampe ; rideau et meuble identiques ; pas de changement de soleil.
- À préserver : Dôme, base, pied, table et plis des rideaux ; aucun meuble ajouté entre les ambiances.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 4612402.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Résolution douce
- Raccord : Carton JUSTE UNE LUMIÈRE
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Warm premium home lighting closing shot using the exact white dome lamp from the reference photograph. Preserve the original shade, slim stem, round base, wood table and curtains. A very slow two-centimeter camera pullback. Comfortable amber illumination remains stable beneath the shade with realistic soft spill on the curtain and warm wood grain. The lamp is stationary, grounded and geometrically unchanged. Restrained natural cinematic image, no magical particles, no new furniture, no morphing, no person, no label or text, no logo, no cut. Quiet room tone only, no music or dialogue.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : JUSTE UNE LUMIÈRE / Et l'ambiance change.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.

