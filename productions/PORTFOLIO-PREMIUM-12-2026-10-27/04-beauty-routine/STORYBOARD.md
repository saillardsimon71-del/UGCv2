# BEAUTY ROUTINE : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : La main déjà présente s'approche de 1 cm du petit flacon, sans le saisir.
- Cadrage : Gros plan main et produits sur lavabo
- Caméra : Fixe
- Lumière : Salle de bain photographiée, lumière naturelle froide adoucie, blancs préservés.
- À préserver : Même interprète de stock, pyjama bleu clair à liseré, miroir et lavabo, bouchons noirs et flacon tenu ; pas de changement d'identité.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 10221846.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Contact discret sur céramique
- Raccord : Raccord main vers geste
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Realistic premium morning skincare routine from this real photo. Preserve the same pale blue pajama sleeve, visible hand, existing amber glass skincare bottles with black caps, white sink, chrome tap and bathroom mirror. Locked camera, close shot on the hand and existing product arrangement. The hand shifts forward only one centimeter and stops beside the small amber bottle; do not pick up or replace any object. Soft natural bathroom light, truthful skin and glass detail. Keep five anatomically correct fingers, reflections consistent, all bottles rigid and labels unchanged without generating letters. No new person, product, finger, text, logo or cut. No speaking or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Le petit geste de pipette au-dessus de la paume se poursuit sans contact avec le visage.
- Cadrage : Gros plan du geste, visage de profil
- Caméra : Fixe
- Lumière : Salle de bain photographiée, lumière naturelle froide adoucie, blancs préservés.
- À préserver : Même interprète de stock, pyjama bleu clair à liseré, miroir et lavabo, bouchons noirs et flacon tenu ; pas de changement d'identité.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 10222458.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Goutte discrète uniquement si visible au rendu
- Raccord : Coupe de geste vers plan contexte
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Authentic restrained beauty routine in the actual bathroom shown in this photographic reference. Same adult woman, exact facial identity, tied-back hair and pale blue piped pajamas. She holds the existing dropper over her open palm and makes only a tiny controlled wrist adjustment, then pauses. The dropper never touches her eye or mouth. Preserve the precise bottle, fingers, sleeve, sink and mirror geometry and consistent reflection. Soft natural window light, natural skin texture, calm closed lips, fixed camera. No speaking, no extra fingers, no face smoothing, no new packaging, no text or logos, no camera spin, one uninterrupted shot. No voice or music.
```

## Plan 03 : 10.0-15.0 s

- Description : Les mains et les flacons restent stables, respiration du cadre.
- Cadrage : Contexte lavabo et gamme
- Caméra : Recul de 2 cm
- Lumière : Salle de bain photographiée, lumière naturelle froide adoucie, blancs préservés.
- À préserver : Même interprète de stock, pyjama bleu clair à liseré, miroir et lavabo, bouchons noirs et flacon tenu ; pas de changement d'identité.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 10221851.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Froissement de manche et fin musicale
- Raccord : Carton LE RITUEL
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Quiet realistic skincare campaign closing shot from this genuine photograph of the same bathroom. Preserve the exact white sink, chrome faucet, small amber skincare bottles with black caps, pale blue pajama sleeve and existing hand. A restrained two-centimeter camera pullback, no orbit, reveals the original arrangement. Natural diffuse bathroom light and honest white surfaces. Keep every bottle, cap, mirror edge and finger count unchanged. The hand rests naturally without picking anything up. No new product or person, no label text, no branding, no cut, no impossible reflection, no speech or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : LE RITUEL / Un moment pour soi.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.
