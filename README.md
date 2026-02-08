# Warpocalypse

Warpocalypse est un **outil audio expérimental** de transformation et de re-composition sonore.  
Il permet de charger un fichier audio, de le fragmenter, le déformer, le re-synthétiser et d’exporter le résultat en WAV.

L’objectif n’est pas la fidélité, mais **l’accident contrôlé**.

---

## ✨ Fonctionnalités principales

- Chargement de fichiers audio :
  - WAV (lecture directe)
  - MP3 / FLAC / OGG / AIFF / M4A (via ffmpeg)
- Analyse et affichage de la forme d’onde
- Système de **grains** (durée min / max)
- Paramètres de :
  - Shuffle
  - Reverse probabiliste
  - Gain aléatoire
  - Intensité globale
- Moteur **Warp** :
  - Time-stretch aléatoire
  - Pitch-shift aléatoire
  - Probabilité de warp
- Seed reproductible (même seed → même résultat)
- Pré-écoute audio
- Export WAV
- Thèmes visuels multiples (sombres, clairs, expérimentaux)

---

## 🧠 Philosophie

Warpocalypse n’est pas un plugin “chirurgical”.  
C’est un **instrument**.

- Les paramètres influencent des probabilités
- Le résultat peut être subtil ou radical
- Le chaos est borné, jamais totalement libre
- La seed est là pour *dompter* l’aléatoire, pas pour l’annuler

---

## 🖥️ Prérequis

### Python
- Python **3.10+** recommandé

### Dépendances Python
Principales dépendances :
- `numpy`
- `soundfile`
- `sounddevice`
- `pydub`
- `tkinter` (inclus avec Python sur la plupart des systèmes)

Installation typique :
```bash
pip install -r requirements.txt
