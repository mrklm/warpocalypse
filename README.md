# Warpocalypse

Petit outil Tkinter pour "déstructurer" des samples audio avec randomisation contrôlée (seed) :
- découpe en grains aléatoires bornés
- réordonnancement partiel (shuffle + conservation d’une part originale)
- reverse probabiliste
- gain dB aléatoire borné
- preview audio + export WAV

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
