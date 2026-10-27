# ARCHITECTURAL LIVING : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Lumière stable ; une ombre végétale respire très légèrement.
- Cadrage : Plan d'ensemble vertical depuis l'entrée
- Caméra : Travelling avant de 4 cm maximum
- Lumière : Fenêtre existante à gauche, lumière chaude naturelle, ombres directionnelles constantes.
- À préserver : Fenêtre, montants, fauteuil, tapis, plante, console et lampe, proportions et perspective de la même pièce.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 15743373.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Ambiance de pièce feutrée
- Raccord : Coupe vers la matière du fauteuil
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
High-end architectural living film using this authentic interior photograph as the exact reference. Preserve the same room, window frame and muntins, dark slim armchair, rug, wood floor, plant, console and table lamp in their original positions. Very slow straight four-centimeter camera push into the room, no orbit, no pan. Natural warm window daylight, consistent perspective, detailed wood and fabric, restrained cinematic contrast. Only an almost imperceptible natural plant shadow movement. All furniture and architecture stay rigid and stationary. No new objects, people, doors or windows, no changing furniture, no text, no logo, no cut. Quiet indoor room tone only, no voice or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Le faible déplacement révèle texture et contact au sol, sans faire bouger le meuble.
- Cadrage : Plan rapproché fauteuil et parquet
- Caméra : Glissement latéral de 2 cm
- Lumière : Fenêtre existante à gauche, lumière chaude naturelle, ombres directionnelles constantes.
- À préserver : Fenêtre, montants, fauteuil, tapis, plante, console et lampe, proportions et perspective de la même pièce.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 15743373.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Détail textile subtil et souffle de transition
- Raccord : Raccord de lumière vers cadre final
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Premium furniture detail cinematography from the same real interior photo. Preserve the exact dark slim chair frame, textile seat, nearby rug, wood floor grain and original window light direction. A very short two-centimeter lateral optical slide reveals tactile upholstery and believable contact shadows. The chair is completely rigid and stationary; legs remain straight and on the floor. Natural warm neutral color, soft window highlights, elegant restrained depth of field. Same room layout and geometry throughout. No furniture substitution, no bending metal, no added person, no new decor, no text, no logo, no cut. Soft room ambience, no speech or music.
```

## Plan 03 : 10.0-15.0 s

- Description : L'espace s'apaise pour accueillir la signature.
- Cadrage : Composition fauteuil, fenêtre, plante
- Caméra : Fixe, respiration de la lumière uniquement
- Lumière : Fenêtre existante à gauche, lumière chaude naturelle, ombres directionnelles constantes.
- À préserver : Fenêtre, montants, fauteuil, tapis, plante, console et lampe, proportions et perspective de la même pièce.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 15743373.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Fin musicale ouverte, aucun impact
- Raccord : Carton HABITER
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Final high-end interior campaign composition from this exact real reference room. Keep the window frame, dark armchair, pale rug, wood floor, tall plant, console and small lamp exactly as photographed. Locked camera with no perspective change. Very gentle daylight breathing across the existing floor, no day-to-night transition and no furniture movement. Refined warm natural materials, clear spatial depth, realistic architectural verticals and contact shadows. Preserve every object count and position. No people, new decor, text, brands, changing walls or impossible geometry, no cut. Quiet realistic room tone, no dialogue or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : HABITER / L'espace prend son temps.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.
