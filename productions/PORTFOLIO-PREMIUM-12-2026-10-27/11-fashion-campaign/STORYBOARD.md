# FASHION CAMPAIGN : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Le tissu suit une respiration très légère, coutures préservées.
- Cadrage : Matière et revers du tailleur
- Caméra : Glissement de 1 cm
- Lumière : Faisceau latéral chaud et fond brun, détails dans les ombres, exposition de peau stable.
- À préserver : Même modèle, coupe, revers, manches, boutons et pantalon ; aucune marche ni changement de vêtement.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 20788943.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Froissement textile discret
- Raccord : Coupe vers regard
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Premium editorial tailoring campaign from this real studio photograph. Preserve the same beige tailored jacket lapels, seams, sleeve length, buttons and matching trousers on the seated adult model. Tight fabric-focused framing, a restrained one-centimeter lateral camera slide. The fabric moves only subtly with natural breathing while the model remains seated. Original warm directional studio light and brown background, tactile weave, refined shadow detail. No changes to garment cut, no new buttons or accessories, no logo, no text, no extra hands, no cut. No voices or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Un clignement et un léger mouvement de regard, sans tourner complètement la tête.
- Cadrage : Portrait éditorial trois-quarts
- Caméra : Fixe
- Lumière : Faisceau latéral chaud et fond brun, détails dans les ombres, exposition de peau stable.
- À préserver : Même modèle, coupe, revers, manches, boutons et pantalon ; aucune marche ni changement de vêtement.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 20788943.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Ambiance studio, note tenue
- Raccord : Coupe vers silhouette complète
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Cinematic fashion portrait using exactly the adult stock model in the reference photo. Preserve her face, short dark bob, beige tailored jacket and seated three-quarter pose. Locked camera, one gentle natural blink and a tiny eye movement towards the original light, no full head turn. Strong warm side light, brown studio background and authentic skin texture. Keep hair silhouette, facial proportions and jacket lapels stable. No speaking, no beauty filter, no identity change, no new accessories, no extra fingers, no text or logos, one continuous take. No voice or music.
```

## Plan 03 : 10.0-15.0 s

- Description : La posture reste stable et la lumière dessine la tenue.
- Cadrage : Silhouette assise entière
- Caméra : Recul de 3 cm maximum
- Lumière : Faisceau latéral chaud et fond brun, détails dans les ombres, exposition de peau stable.
- À préserver : Même modèle, coupe, revers, manches, boutons et pantalon ; aucune marche ni changement de vêtement.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 20788943.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Résolution musicale sobre
- Raccord : Carton LIGNE
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Final premium fashion campaign silhouette from this exact real reference photograph. Same seated adult model, beige tailored suit, chair, brown studio floor and warm directional light. A slow straight three-centimeter camera pullback, no orbit. The model holds the original elegant seated pose with only subtle breathing. Preserve jacket cut, lapels, sleeve length, hands, trousers, shoes and chair geometry. No standing, walking, garment swap, extra limb, new accessory, lettering or logo, no cut. Refined editorial photographic realism, no dialogue or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : LIGNE / Taillé pour la lumière.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.
