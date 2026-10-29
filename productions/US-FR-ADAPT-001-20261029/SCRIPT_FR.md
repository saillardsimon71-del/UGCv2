# SCRIPT FR ORIGINAL — PILOTE 001
**Titre : « J'ai automatisé les demandes de devis d'un artisan avec l'IA (sans coder) »**

> Durées = **objectifs de montage**, pas timecodes démontrés. Lecture + pauses de capture : viser ~7 minutes. Toutes les captures d'exécution doivent être réellement obtenues. L'artisan et les données du test sont fictifs. Ce script n'est ni la traduction ni la paraphrase linéaire de la vidéo US.

### 01 — 00:00–00:35 — Accroche [avatar original, puis capture écran]
Imagine : tu tiens une petite entreprise de plomberie, tu rentres d'un chantier et tu découvres sept nouveaux messages. Une fuite, un remplacement de robinet, une demande de prix… Pour chaque message, tu dois comprendre le besoin, estimer l'urgence, préparer une réponse. Aujourd'hui, je vais construire un mini assistant qui fait le premier tri et prépare un brouillon en français. Tu gardes le contrôle : aucun e-mail ne part sans validation. Et pour le construire, on va utiliser n8n et un modèle IA.

### 02 — 00:35–01:20 — Cas d'usage français [captures de la demande fictive]
Notre exemple est fictif : « Atelier Seine Plomberie », à Rouen. Une personne écrit : « Bonjour, l'eau coule sous mon évier depuis ce matin. Je suis disponible demain après-midi. Pouvez-vous intervenir et me dire ce qu'il faut préparer ? » Ce n'est pas un vrai client et je ne vais pas prétendre avoir gagné des heures grâce à ce test. L'objectif, c'est de montrer un mécanisme utile que tu pourras adapter à ta propre activité. On va demander au système de produire trois choses : une catégorie de demande, un degré d'urgence indicatif, et un brouillon de réponse. Mais le prix et le délai réel resteront à confirmer par l'artisan.

### 03 — 01:20–02:05 — Comprendre le workflow [infographie originale]
Avant de toucher à l'outil, retiens une seule idée : une automatisation, c'est une chaîne d'étapes. Il y a d'abord un événement qui lance le processus. Ensuite, des actions qui manipulent les informations. Enfin, un résultat qui arrive au bon endroit. Dans notre cas, on va commencer très simplement avec un déclencheur manuel. Pourquoi ? Parce qu'on veut vérifier chaque étape sans risquer de traiter un vrai message par accident. Plus tard, le déclencheur pourra être remplacé par un formulaire ou une boîte de réception, avec les autorisations nécessaires. Aujourd'hui, on se concentre sur le cœur du système, pas sur la promesse d'une usine magique.

### 04 — 02:05–02:45 — Préparer les données [capture n8n réelle requise]
Dans n8n, je crée donc un nouveau workflow. Première étape : déclenchement manuel. La seconde étape prépare une fausse demande avec quatre champs : le prénom, le type de problème, le texte reçu et la ville. Ces données sont inventées pour cette démonstration. Je lance une première fois et je vérifie que la bonne information passe au nœud suivant. C'est un réflexe à prendre : si l'entrée est mauvaise, même un excellent modèle produira une réponse peu fiable. Et c'est aussi beaucoup plus facile de corriger un workflow quand on teste étape par étape.

### 05 — 02:45–03:50 — Ajouter l'IA [capture réelle de paramètres, secrets masqués]
Maintenant, la partie intéressante : le modèle IA. Dans cette version j'utilise l'API Mistral, appelée depuis un nœud HTTP de n8n. La clé reste dans la configuration privée de l'outil, jamais dans la vidéo et jamais dans GitHub. Mon instruction ne demande surtout pas d'inventer un tarif ou d'assurer que le plombier viendra demain. Elle demande d'identifier le besoin, de signaler une urgence probable, puis de proposer un texte de réponse court et professionnel. On ajoute aussi une contrainte importante : si une information manque, le système doit poser une question plutôt que l'inventer. C'est la différence entre un simple texte généré et une automatisation que tu peux envisager d'utiliser sérieusement.

### 06 — 03:50–04:45 — Voir la sortie [capture réelle ; ne pas inventer le résultat]
À l'exécution, on regarde les données retournées par l'API. [MONTRER LE RÉSULTAT RÉEL DU TEST, PAS UNE SIMULATION RECONSTITUÉE.] Ce qu'on cherche à vérifier, c'est d'abord que le modèle a compris la fuite sous l'évier, ensuite qu'il ne promet aucun déplacement ou tarif, et enfin qu'il formule une réponse facile à corriger. Si le résultat n'est pas bon, on ajuste l'instruction et on recommence le **test de données**, pas une grande génération vidéo. Le but est d'obtenir un exemple clair et vérifiable à l'écran.

### 07 — 04:45–05:40 — L'étape oubliée : validation [schéma + capture du brouillon]
Et là, il y a un piège que je vois souvent dans les démonstrations d'automatisation : on saute directement à « envoyer ». Personnellement, pour une demande client, je ne ferais pas ça au premier jour. L'IA ne connaît pas les disponibilités réelles, les conditions commerciales ni l'état de l'intervention. Je préfère afficher un brouillon que l'artisan valide, corrige ou refuse. On peut même lui demander de confirmer le numéro du dossier et les informations manquantes. Dans ce pilote, on s'arrête volontairement au brouillon : aucune action ne contacte le faux client, encore moins un vrai.

### 08 — 05:40–06:40 — Adapter à d'autres secteurs [schémas originaux, pas de faux résultats]
Le principe peut servir à beaucoup de métiers français. Pour une agence immobilière, il pourrait trier des demandes de visite. Pour un garage, préparer une liste de questions à poser avant un rendez-vous. Pour une boutique, suggérer une réponse à une demande de retour. Mais attention : chaque métier a ses propres contraintes et données sensibles. Si tu traites de vrais messages, tu dois examiner les accès, la sécurité, les durées de conservation et les obligations de protection des données. Il faut aussi mesurer le coût des appels API et le temps passé à contrôler les brouillons. Une automatisation n'est rentable que si elle fait vraiment mieux que le processus qu'elle remplace.

### 09 — 06:40–07:25 — Conclusion + récapitulatif [avatar + écran récap]
Au final, on a construit un premier système compréhensible : une demande entre, des informations sont préparées, une IA propose une analyse et une réponse, puis une personne prend la décision finale. Le point important, ce n'est ni l'outil ni la marque du modèle, c'est le problème précis qu'on résout. Si tu veux reproduire cette démonstration, commence avec des données fictives comme moi, fais fonctionner un seul exemple, puis ajoute progressivement les vraies connexions. Et dans une prochaine vidéo, on pourra aller plus loin : mesurer le temps réellement gagné et transformer ce brouillon en véritable workflow de suivi.

---

## Contrôles éditoriaux obligatoires
- Ne **pas** dire « voici ce que Mistral a répondu » sans présenter la vraie sortie du test.
- Ne pas afficher une clé API, un nom/adresse client réel, ou une capture américaine.
- Les captures d'écran n8n doivent être tournées depuis le workflow FR du pilote.
- La voix peut être synthétique, mais elle ne doit pas imiter la personne de la vidéo source.
- Aucun délai, tarif ou résultat commercial fictif présenté comme acquis.
- Adapter les durées au débit réel de la voix et au temps de lecture à l'écran ; pas de gel d'écran artificiel pour atteindre sept minutes.
