# GOLDEN REVEAL : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Une caustique traverse le verre immobile.
- Cadrage : Macro arête de verre et jus
- Caméra : Glissement latéral de 2 cm
- Lumière : Contre-jour ambré et lumière douce latérale ; rayons discrets, sans particules envahissantes.
- À préserver : Angles du verre, niveau de jus, bouchon brun et sa taille ; aucun nom de marque.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 4735929.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Tintement bref de verre
- Raccord : Raccord de couleur ambre
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Elegant luxury fragrance reveal from the real reference photo. Preserve the exact rectangular clear glass perfume bottle, pale amber liquid level and round brown closed cap. Tight macro composition around the glass body and liquid. A warm amber caustic moves gently across the glass while the camera slides two centimeters sideways. Soft optical depth of field, creamy warm backdrop, realistic refraction and glass thickness. Rigid bottle, no changes to corners or contents, no new text, no labels, no logo, no hands, no floating, no smoke, no cut. No dialogue or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Le recul découvre la silhouette sous un contre-jour chaud.
- Cadrage : Plan rapproché flacon et bouchon
- Caméra : Recul de 4 cm
- Lumière : Contre-jour ambré et lumière douce latérale ; rayons discrets, sans particules envahissantes.
- À préserver : Angles du verre, niveau de jus, bouchon brun et sa taille ; aucun nom de marque.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 4735929.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Montée d'air de 0,5 s
- Raccord : Coupe sur brillance
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Premium perfume product reveal using this authentic photograph. The exact clear rectangular bottle, pale amber contents and large round brown cap stay unchanged and sealed. The camera pulls back only four centimeters as a warm soft backlight brightens gradually behind the glass. Delicate volumetric warmth, clean creamy background, realistic shadows, controlled golden reflections. The bottle is stationary on the surface. Preserve proportions, flat faces, cap shape and liquid level. No spinning, no opening, no added accessories, no labels, no lettering, no logo, no hands, one continuous shot. No voice or music.
```

## Plan 03 : 10.0-15.0 s

- Description : Le reflet s'apaise et laisse un flacon lisible pour la signature.
- Cadrage : Hero produit entier
- Caméra : Fixe
- Lumière : Contre-jour ambré et lumière douce latérale ; rayons discrets, sans particules envahissantes.
- À préserver : Angles du verre, niveau de jus, bouchon brun et sa taille ; aucun nom de marque.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 4735929.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Accord lumineux puis décroissance
- Raccord : Carton AMBRE
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Final luxury fragrance hero frame, same authentic unbranded clear glass bottle with pale amber liquid and brown cylindrical cap. Full bottle on the same neutral surface, grounded contact shadow, quiet warm ivory background. Locked-off camera and very gentle golden light sweep across one face of the bottle, ending in a stable readable packshot. Photographic glass refraction, precise rigid geometry, restrained cinematic highlights. No change in liquid level, no vapor, no levitation, no hands, no letters, labels or logos, no additional props or cut. No dialogue or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : AMBRE / La lumière se révèle.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.
