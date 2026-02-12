

Warpocalypse n’est pas un effet audio classique.  
Ce n’est ni un delay, ni un pitch-shifter continu, ni un multi-effet en chaîne.

C’est un **instrument probabiliste basé sur des grains**.

Cette page explique :

- **comment le son circule**
- **où agissent les paramètres**
- **pourquoi certains réglages semblent ne rien faire**

---

## 1. Principe général

Warpocalypse fonctionne en plusieurs étapes :

1. Le fichier audio est chargé.
2. Il est découpé en **grains** (petits fragments).
3. Chaque grain peut être :
   - déplacé
   - inversé
   - amplifié
   - transformé (warp)
4. Les grains sont ensuite **recombinés** pour produire le son final.

👉 Le traitement se fait **grain par grain**, jamais de façon continue.

---

## 2. Le flux audio (câblage interne)

Le chemin réel du signal est le suivant :

Audio source  
↓  
Découpage en grains  
↓  
Randomisation (shuffle / reverse / gain / seed)  
↓  
Warp conditionnel (stretch / pitch)  
↓  
Reconstruction  
↓  
Sortie audio  

⚠️ Point important :  
**Le warp n’est pas toujours appliqué.**  
Il dépend de probabilités.

---

## 3. Les grains : la base de tout

Un **grain** est un fragment audio très court (quelques millisecondes à quelques centaines de millisecondes).

Les grains :
- sont traités individuellement
- peuvent être tous différents
- sont la matière première du chaos contrôlé

Si les grains sont :
- très réguliers
- très similaires  
→ les transformations seront **peu audibles**

---

## 4. La partie “Randomizer” (droite de l’interface)

La section de droite **n’est pas cosmétique**.  
Elle prépare le terrain pour le warp.

### ● Shuffle
Change l’ordre des grains.

### ● Reverse
Inverse certains grains (lecture à l’envers).

### ● Gain
Modifie le volume de certains grains.

### ● Seed
Fixe ou libère l’aléatoire :
- même seed → même résultat
- seed différente → autre variation

👉 Sans cette section, les grains restent très semblables entre eux.

---

## 5. Le Warp : un traitement conditionnel

Le warp **n’est pas un effet continu**.

Il repose sur une question simple, posée pour chaque grain :

> “Ce grain va-t-il être transformé ?”

La réponse dépend du paramètre **Prob**.

---

## 6. Explication des paramètres Warp

### ● Prob (probabilité)
C’est le paramètre **le plus important**.

- Prob = 0.0 → aucun grain n’est warpé
- Prob = 0.1 → environ 10 % des grains sont warpés
- Prob = 1.0 → tous les grains sont warpés

👉 Si Prob est à 0, **les autres paramètres Warp n’ont aucun effet audible**.

---

### ● Warp (amount)
Définit **l’intensité maximale autorisée** du warp.

- faible → variations subtiles
- élevé → transformations radicales

Ce n’est pas un interrupteur.

---

### ● Stretch
Détermine l’amplitude de variation **temporelle** des grains warpés :
- grains plus courts
- grains plus longs

N’agit que sur les grains sélectionnés par **Prob**.

---

### ● Pitch
Détermine l’amplitude de variation **de hauteur** (pitch) des grains warpés.

N’agit que sur les grains sélectionnés par **Prob**.

---

## 7. Pourquoi “ça ne fait rien” parfois (comportement normal)

Il est fréquent d’observer ceci :

> “Les paramètres Warp / Stretch / Pitch changent, mais aucun changement n’est audible.”

Dans la majorité des cas, c’est normal.

Causes possibles :
- Prob trop faible ou nulle
- grains trop courts ou trop réguliers
- randomizer désactivé
- variations trop faibles pour être perceptibles

👉 Warpocalypse privilégie la **variation**, pas l’effet constant.

---

## 8. Comment entendre clairement l’effet du warp (test conseillé)

Pour comprendre rapidement le fonctionnement :

1. Prob = **1.0**
2. Warp = **1.0**
3. Stretch = **1.0**
4. Pitch = **1.0**
5. Seed fixe

👉 Le warp devient immédiatement audible, même sans randomizer.

Ensuite :
- baissez Prob
- activez le randomizer
- observez comment le chaos devient plus subtil et plus musical

---

## 9. Philosophie de l’outil

Warpocalypse est conçu pour :
- explorer des variations
- provoquer des accidents contrôlés
- générer des textures, pas des corrections

Warpocalypse n’est pas l’outil idéal lorsque l’on sait exactement ce que l’on veut obtenir.  
C’est un excellent outil pour être surpris **sans perdre le contrôle**.

---

## 10. À retenir

- Warpocalypse travaille **par grains**
- le warp est **probabiliste**
- Prob est la clé
- sans randomisation, le warp peut être mathématiquement actif mais perceptuellement discret
- le chaos a des garde-fous (volontairement)

---
