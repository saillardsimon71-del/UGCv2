# PROBLÈME / SOLUTION : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Le papier frémit à peine ; la surcharge est ajoutée par typographie au montage.
- Cadrage : Produit et espace pour accroche
- Caméra : Rapprochement de 2 cm
- Lumière : Lumière de bureau diffuse, papier crème lisible ; aucune écriture générée.
- À préserver : Nombre de pages visibles, couverture mouchetée, stylo transparent et ombres ; pas d'ajout de texte génératif sur le papier.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 7657397.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Trois petits clics puis souffle de sortie
- Raccord : Coupe nette au passage produit
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Clear conversion-focused stationery commercial using this exact real photograph. Preserve the unbranded notebook with cream pages and patterned cover, transparent ballpoint pen and original desktop arrangement. Restrained two-centimeter optical push, soft diffuse daylight, crisp tactile paper. Only a very slight natural page-edge tremble, with all objects remaining in their original positions. Leave the pages blank and clean; all commercial typography will be added in postproduction. No writing generated on paper, no new hands or objects, no logo, no product substitution, no cuts. No speaking or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Une feuille déjà entrouverte se soulève de quelques millimètres puis se repose.
- Cadrage : Macro tranche et feuilles ouvertes
- Caméra : Fixe
- Lumière : Lumière de bureau diffuse, papier crème lisible ; aucune écriture générée.
- À préserver : Nombre de pages visibles, couverture mouchetée, stylo transparent et ombres ; pas d'ajout de texte génératif sur le papier.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 7657397.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Froissement papier court
- Raccord : Coupe sur la page posée
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Tactile stationery demonstration from this actual notebook photo. Tight view of the exact cream paper edges and patterned notebook cover already visible in the photograph. Locked camera, a single existing loose page edge lifts only a few millimeters in a gentle air movement and settles once. Preserve the paper count, binding, cover pattern and pen position. Natural white desktop, soft shadows, realistic paper thickness and restrained commercial clarity. The sheets remain completely blank. No new notebook, no hands, no page morphing, no printed or handwritten text, no logos, no cuts. No speech or music.
```

## Plan 03 : 10.0-15.0 s

- Description : L'image se stabilise et la promesse émotionnelle apparaît au montage.
- Cadrage : Packshot papier et stylo
- Caméra : Très léger recul
- Lumière : Lumière de bureau diffuse, papier crème lisible ; aucune écriture générée.
- À préserver : Nombre de pages visibles, couverture mouchetée, stylo transparent et ombres ; pas d'ajout de texte génératif sur le papier.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 7657397.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Arrêt des clics, petite résolution
- Raccord : CTA PASSEZ AU PAPIER
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Minimal premium notebook campaign closing shot from the same authentic photograph. Same cream blank paper, patterned notebook cover, transparent pen and pale desk. Very slight slow camera pullback, final stable packshot. Honest soft daylight, precise pen geometry and paper texture. Keep the original arrangement rigid with believable shadows, pages blank, no hand, no generated writing, no new object, no logos, no cut. Clean negative space for postproduced copy. No voice or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : UNE PAGE / Faites place à vos idées.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.

