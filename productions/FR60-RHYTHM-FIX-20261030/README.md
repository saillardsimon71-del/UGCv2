# Raccord V2 : pause raccourcie

La piste validée contenait 1,92 s de silence autour du raccord. Suppression conjointe des images et du son de 2,92 à 4,40 s : pause restante de 0,44 s, durée finale de 6,52 s.

Aucun mot supprimé, aucun changement de vitesse. Toutes les images du titre et de la PiP sont conservées. Le passage retiré culmine à -84,3 dBFS dans le PCM. Les 163 images finales sont contrôlées contre leur image d'origine, et l'audio contre le montage PCM attendu. Le MP4 de huit secondes reste intact. Aucun appel LTX ou TBDub.

Reproduction depuis la racine, avec les fichiers locaux du test précédent :

```powershell
python productions/FR60-RHYTHM-FIX-20261030/trim_pause.py
```

Les paramètres, empreintes et résultats sont dans `edit.json`. Le script refuse d'écraser la sortie existante. Le MP4 privé est livré dans le dossier `outputs/UGCv2_continuite_rythme_v2/` du chat.
