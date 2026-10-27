# DARK LUXURY : storyboard de production

Durée cible : 17.5 s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.

## Plan 01 : 0.0-5.0 s

- Description : Un reflet froid glisse sur le bord du flacon, le produit reste immobile.
- Cadrage : Très gros plan épaule et bouchon
- Caméra : Travelling latéral de 2 cm maximum
- Lumière : Source latérale étroite, noirs détaillés, liseré froid ; fond rouge du stock désaturé en préparation CPU.
- À préserver : Silhouette ronde, bouchon fermé, proportions, noir mat ; aucun ajout de pulvérisateur ou gravure.
- Image initiale : [PNG réel](ASSETS/shot-01-firstframe.png), Pexels 5994299.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Impact sub très discret à 0,15 s, souffle court
- Raccord : Coupe sur le reflet
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Premium fragrance cinematography from this authentic photograph. Preserve the exact unbranded matte black round bottle, short cylindrical closed cap and curved shoulder. Extreme close product framing. A restrained silver rim reflection travels along the shoulder as the camera slides just two centimeters sideways. Deep charcoal blacks with visible edges, single narrow side softbox, elegant falloff and realistic material response. The bottle stays rigid and upright. No rotation, opening, liquid, mist, hands, labels, lettering or additional props. One continuous optical take. No speech, voices or music.
```

## Plan 02 : 5.0-10.0 s

- Description : La lumière dessine la courbe mate ; aucune transformation du flacon.
- Cadrage : Plan produit serré, épaule et corps
- Caméra : Très lent rapprochement de 3 cm
- Lumière : Source latérale étroite, noirs détaillés, liseré froid ; fond rouge du stock désaturé en préparation CPU.
- À préserver : Silhouette ronde, bouchon fermé, proportions, noir mat ; aucun ajout de pulvérisateur ou gravure.
- Image initiale : [PNG réel](ASSETS/shot-02-firstframe.png), Pexels 5994299.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Résonance métallique amortie
- Raccord : Coupe franche vers le plan large
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Luxury unbranded fragrance product film. Exactly the same black bottle, cylindrical sealed cap, matte surface and curved geometry as the photographic source. A very slow three-centimeter camera push towards the bottle. A soft controlled highlight reveals the round body against a near-black neutral backdrop. Keep every edge and the cap-to-body proportions unchanged; keep the bottle resting on its original plane. Tactile restrained photographic realism, no floating, no spinning, no new text, no logo, no smoke, no additional object, no hands. One uninterrupted take. Quiet nonverbal room tone only.
```

## Plan 03 : 10.0-15.0 s

- Description : Révélation du flacon entier ; maintien lisible pour le titre en postproduction.
- Cadrage : Packshot frontal avec espace négatif
- Caméra : Fixe, légère respiration lumineuse
- Lumière : Source latérale étroite, noirs détaillés, liseré froid ; fond rouge du stock désaturé en préparation CPU.
- À préserver : Silhouette ronde, bouchon fermé, proportions, noir mat ; aucun ajout de pulvérisateur ou gravure.
- Image initiale : [PNG réel](ASSETS/shot-03-firstframe.png), Pexels 5994299.
- Moteur : LTX-2.5 Distilled, ComfyUI 2 passes ; pvs-ltx/render_clip ; L40S.
- Son : Signature sonore grave puis silence
- Raccord : Coupe vers carton NOCTURNE
- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.

Prompt exact :

```text
Final premium perfume hero shot using this real photographic reference. Preserve the exact single unbranded matte black bottle with its closed cylindrical black cap. Full rigid silhouette, grounded on the original surface with a believable contact shadow. Locked camera. A gentle silver side light gradually defines both edges without changing the product geometry or adding objects. Dark minimal charcoal studio, refined black-on-black product photography, generous clean negative space. No generated writing, no label, no logo, no camera spin, no opening, no hand, no cut. No voice or music.
```

## Plan 04 : 15.0-17.5 s

Carton fixe CPU : NOCTURNE / Le silence a une présence.. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.

