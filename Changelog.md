# Changelog — Warpocalypse

Toutes les modifications notables de ce projet sont documentées ici.  
Le format suit l’esprit de *Keep a Changelog*, sans rigidité dogmatique.


---

## [1.1.3] 2026/02/10

### Modifié

 - Ajout de double traits (blanc et noir) pour sélectionner la zone à boucler

---

## [1.1.2] 2026/02/09

### Modifié

 - ne plus appeler sd.stop() depuis le thread UI
 - déléguer l’arrêt de la lecture au même thread que celui qui a lancé sd.play()
 - synchroniser l’arrêt via un threading.Event

---

## [1.1.1] 2026/02/09

### Ajouté

 - Mode Loop
 - license GNU

--- 

## [1.1.0] 2026/02/08

### Ajouté

- Ajout d’une image splash dans l’aide, 
- centrage du texte AIDE.md
- intégration de Pillow pour le redimensionnement

### Modifié

- corrections de bugs de syntaxe

---

## [1.0.0] 2026/02/08

### Ajouté

- Correction du warp : garde-fous sur la taille des grains + n_fft adaptatif

### Modifié

- Stabilité améliorée sur fichiers courts, suppression des warnings DSP

---

## [0.9.0] 2026/02/08

### Ajouté

- Affichage de la version dans la fenêtre principale
- Centralisation du versionnage (`APP_NAME`, `APP_VERSION`)
- UI épurée :
  - suppression des titres redondants (“Fichier”, “Preset”)
  - bouton de chargement plus explicite
  - réduction de la hauteur de la forme d’onde
- Système de potards rotatifs (Warp / Stretch / Pitch / Prob)

### Modifié

- Flux principal clarifié : charger → écouter → rendre → exporter
- Paramètres Warp regroupés et synchronisés avec l’UI
- Gestion des thèmes améliorée (cohérence fond / accents)

### Corrigé

- Import prématuré de pydub supprimé (warning ffmpeg au lancement)
- Détection et usage de ffmpeg fiabilisés
- Séparation claire des responsabilités :
  - UI
  - audio I/O
  - moteur
  - warp engine

---

## [0.8.0] 2026/02/07

### Ajouté

- Moteur Warp (time-stretch et pitch aléatoires)
- Potard d’intensité globale
- Seed reproductible
- Pré-écoute audio
- Export WAV

### Modifié

- Refonte du moteur de rendu
- Normalisation du flux mono
- Meilleure gestion des erreurs utilisateur

---

## [0.7.0] 2026/02/06

### Ajouté

- Chargement audio multi-formats (WAV / MP3 / FLAC / OGG / AIFF / M4A)
- Affichage de la forme d’onde
- Presets (sauvegarde / chargement JSON)

---

## [0.6.0] et antérieur

### Ajouté

- Prototype initial
- Moteur de grains
- Shuffle, reverse probabiliste, gain aléatoire
- Interface Tkinter de base

---

## Notes de version

- Les versions **0.x** peuvent introduire des changements de comportement
- La **v1.0** marquera une stabilité d’usage et d’interface
- Le moteur restera expérimental par nature, même après 1.0

---
