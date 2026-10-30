# Verdict : raccord visuel reproduit

Le MP4 couvre 7,60-15,60 s de la narration validée : quatre secondes approuvées, puis quatre secondes inédites. Les 100 premières images sont identiques à celles du clip A. Les références A et B restent inchangées.

Une seule génération LTX de quatre secondes et un seul passage TBDub ont été utilisés. Même seed `2026103017`, même prompt, mêmes moteurs et réglages. L'unique adaptation d'entrée est l'image initiale : image 95 du master natif validé avant TBDub, pour reprendre sa pose de fin. Cette image est conservée dans `ASSETS/anchor-native.png` ; la photographie d'identité originale reste intacte.

Le visage, le décor, la lumière et le cadrage restent cohérents sur les images examinées. Au raccord, la boîte de détection du visage passe de `[724,202,457,457]` à `[723,203,455,455]`. La variation d'échelle du décor est inférieure à 0,01 % sur la nouvelle prise. Aucun défaut comparable au zoom du rendu de 12 secondes n'est observé.

TBDub remplace les lèvres pincées du master LTX par une articulation variable, sans dégradation évidente du reste du visage sur les images contrôlées. L'acceptabilité phonétique en lecture continue avec le son reste à confirmer par le visionnage du MP4 ; aucune certification audiovisuelle complète n'est revendiquée.

Le montage conserve le titre animé "TRIGGER", puis la PiP intégralement remplacée et la première image des dominos. Une version sans titre expose le raccord et toute la nouvelle performance. Le comparatif avant/après permet d'isoler l'effet de TBDub.

Vérifications : 200 images décodées, durée 8,000 s, 1080p25, narration continue à vitesse inchangée, corrélation audio supérieure à 0,9999. Les deux applications temporaires sont arrêtées. Aucun nouveau modèle téléchargé, moteur modifié ou rendu de 60 secondes lancé.
