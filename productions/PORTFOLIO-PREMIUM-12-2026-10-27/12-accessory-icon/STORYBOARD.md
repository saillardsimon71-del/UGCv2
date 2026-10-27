# ACCESSORY ICON : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Un reflet souligne le fermoir ; aucune ouverture.
- Cadrage : Macro grain et fermoir
- Caméra : Glissement de 1 cm
- Lumière : Fenêtre diffuse, reflet doré doux sur fermoir, lumière stable sur cuir grainé.
- À préserver : Grain, surpiqûres, rabat, fermoir doré, poignée, absence de marque ; pas de changement de couleur ni de quincaillerie.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 4830923.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Petit tintement métallique amorti
- Raccord : Raccord fermoir vers poignée
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Premium leather-accessory macro from this exact real photograph. Preserve the same structured deep teal handbag, fine grain, flap edge, stitching and single gold clasp. Tight optical detail framing, one-centimeter lateral camera slide and a soft reflection along the existing clasp. The bag remains closed, rigid and motionless on its original stool. Natural window light, tactile leather, refined metal response. No opening, no new hardware, no lettering or logos, no new hand, no brand, no product deformation, no cut. No speech or music.
```

## Plan 02 : 5.0-10.0 s

- Description : Le mouvement appartient à la caméra ; le sac garde sa géométrie.
- Cadrage : Sac complet, poignée et silhouette
- Caméra : Très lent rapprochement de 2 cm
- Lumière : Fenêtre diffuse, reflet doré doux sur fermoir, lumière stable sur cuir grainé.
- À préserver : Grain, surpiqûres, rabat, fermoir doré, poignée, absence de marque ; pas de changement de couleur ni de quincaillerie.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 4830923.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Frottement de matière très léger
- Raccord : Coupe vers mise en situation
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Luxury accessory product motion shot using this authentic teal handbag photo. Preserve the exact deep teal structured bag, black top handle, gold clasp, flap, stitching and stool. A restrained two-centimeter camera push gives subtle optical parallax and moving reflections, while the bag itself remains stationary and grounded. Soft natural room light, precise shape and leather grain. Keep all proportions and hardware identical. No handle bending, no color shift, no added strap or label, no hand, no opening, no cut, no text, no logo. No voices or music.
```

## Plan 03 : 10.0-15.0 s

- Description : Révélation de l'objet dans son environnement réel, sans ajouter de personne.
- Cadrage : Mise en situation sur tabouret dans pièce claire
- Caméra : Recul de 3 cm
- Lumière : Fenêtre diffuse, reflet doré doux sur fermoir, lumière stable sur cuir grainé.
- À préserver : Grain, surpiqûres, rabat, fermoir doré, poignée, absence de marque ; pas de changement de couleur ni de quincaillerie.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 4830923.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Accord final et souffle court
- Raccord : Carton OBJET DE LIGNE
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Final premium accessory lifestyle reveal from this exact authentic interior photo. Same deep teal structured handbag with black handle and gold clasp, sitting on the black stool in the original bright room beside the white cabinet and plants. A slow straight three-centimeter camera pullback reveals its real setting. Preserve bag proportions, grain, clasp, stool, cabinet and plant positions. Soft natural daylight, grounded contact shadows and elegant commercial composition. No new person, new bag, added branding, text, moving furniture, color changes or impossible geometry, no cut. No voice or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : OBJET DE LIGNE / Le détail fait présence.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.

