# SKINCARE SENSORIEL : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Un reflet se déplace sur le ménisque teinté de la pointe ; verre immobile.
- Cadrage : Macro de la pointe de pipette et du verre visible
- Caméra : Glissement de 1 cm, lent
- Lumière : Fenêtre diffuse, ombres de feuillage déjà présentes, tons crème et prune désaturé.
- À préserver : Étiquette vierge, silhouette du flacon, pipette droite, ouverture, niveau de liquide, nombre de pots, support en bois.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 8101534.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Petit tintement et détail liquide sec
- Raccord : Coupe de 0 image sur la pipette
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Prestige skincare extreme macro cinematography from this authentic real product photograph. Preserve the exact visible section of the horizontal transparent glass pipette, its burgundy-tinted liquid and the visible edge of the burgundy bottle. Tight optical detail on the existing pipette tip and liquid meniscus. A tiny soft highlight glints at the photographed tip without changing the shape or color of the liquid. Only one centimeter of lateral camera drift. Soft ivory window light, existing leaf shadows, restrained cream and dusty plum palette, true glass refraction. The glass remains rigid and in the exact original position. Do not extend the pipette, add a cap, invent a new bottle or create a falling liquid string. No hands, text, logos or cuts. No speech, whisper, singing or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Une lumière douce révèle le verre, le papier et le bois ; produit immobile.
- Cadrage : Plan matière et étiquette
- Caméra : Rapprochement de 2 cm maximum
- Lumière : Fenêtre diffuse, ombres de feuillage déjà présentes, tons crème et prune désaturé.
- À préserver : Étiquette vierge, silhouette du flacon, pipette droite, ouverture, niveau de liquide, nombre de pots, support en bois.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 8101534.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Texture d'air légère, frottement feutré
- Raccord : Coupe vers packshot plus large
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Sensorial premium cosmetic product shot using the exact authentic photograph. Same single burgundy serum bottle, completely blank white paper label, open glass pipette with white bulb, frosted cosmetic jar and pale wooden lid. Slow two-centimeter optical push towards the bottle. A delicate natural window reflection crosses the glass, revealing real glass thickness, tactile paper and soft wood grain. Keep the photograph's object arrangement, bottle shape and dropper angle completely unchanged. Elegant creamy diffuse daylight and subtle existing plant shadows. No object moves independently, no cap changes, no extra bottle, no invented label lettering, no text, no hands, no morphing. One continuous shot. No voice, whisper, vocals or music.
```

## Plan 03 : 10.0-15.0 s

- Description : La composition se stabilise, étiquette intégralement vierge.
- Cadrage : Packshot complet avec support
- Caméra : Très léger recul, sans rotation
- Lumière : Fenêtre diffuse, ombres de feuillage déjà présentes, tons crème et prune désaturé.
- À préserver : Étiquette vierge, silhouette du flacon, pipette droite, ouverture, niveau de liquide, nombre de pots, support en bois.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 8101534.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Signature de verre puis respiration musicale
- Raccord : Carton UNE GOUTTE
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Impeccable final skincare packshot from this genuine photographic source. Preserve exactly the burgundy glass serum bottle with its blank white paper label, white dropper bulb and glass pipette in the existing open position, the frosted jar and the round wooden support. A very slight slow camera pullback, without orbiting, reveals the original elegant still life. Soft cream daylight, original leaf shadows moving almost imperceptibly, natural glass and wood texture. The product is rigid and motionless. No additional container, no new cap, no label text, no logo, no letters, no floating or morphing, no hands, no cut. No speech, no whisper, no music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : UNE GOUTTE / Le temps d'un rituel.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.
