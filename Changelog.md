# Changelog — Warpocalypse

Toutes les modifications notables de ce projet sont documentées ici.  
Le format suit l’esprit de *Keep a Changelog*, sans rigidité dogmatique.

---

## [Unreleased]
### À venir
- Amélioration visuelle des potards (anti-aliasing / style)
- Affichage optionnel d’un fond graphique dans la forme d’onde
- Menu “À propos”
- Documentation détaillée des paramètres
- Stabilisation finale avant v1.0

---

## [0.9.0] — en cours
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

## [0.8.0]
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

## [0.7.0]
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
