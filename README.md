# ESP32 WiFi CSI presence detection

Détection de présence dans une pièce via le Channel State Information (CSI) d'un
ESP32-S3. L'ESP capture les perturbations du canal WiFi causées par le mouvement,
un script Python en tire un indicateur de mouvement affiché en temps réel.

Basé sur [ESP32-CSI-Tool](https://github.com/StevenMHernandez/ESP32-CSI-Tool),
adapté pour ESP-IDF v5+ / v6.

## Matériel

- 1× ESP32-S3 (l'ESP32 classique et le C3 ne conviennent pas)
- 1× câble USB **data** de qualité (les câbles charge-only causent des brownouts)
- Une box WiFi à laquelle l'ESP peut se connecter

## Installation

### ESP-IDF

```bash
mkdir -p ~/esp && cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh all
```

À sourcer dans chaque nouveau terminal :

```bash
. ~/esp/esp-idf/export.sh
```

### Le repo

```bash
mkdir -p ~/Documents/wifidetect && cd ~/Documents/wifidetect
git clone https://github.com/StevenMHernandez/ESP32-CSI-Tool.git
```

### Dépendances Python

```bash
pip install pyserial matplotlib numpy
```

## Identification de l'ESP

```bash
lsusb
ls /dev/ttyACM* /dev/ttyUSB*
esptool.py --port /dev/ttyACM0 chip_id
```

Le port sera référencé comme `/dev/ttyACM0` dans la suite, adapter si besoin.

## Configuration du firmware

```bash
cd ~/Documents/wifidetect/ESP32-CSI-Tool/active_sta
. ~/esp/esp-idf/export.sh
idf.py set-target esp32s3
```

Deux patches pour compatibilité IDF v5+ :

```bash
# Header renommé en IDF v5
sed -i 's|#include "esp_spi_flash.h"|#include "spi_flash_mmap.h"|' main/main.cc

# Priorité de tâche FreeRTOS (100 > MAX 25)
sed -i 's/(void \*) &is_wifi_connected, 100,/(void *) \&is_wifi_connected, 5,/' main/main.cc
```

Puis configuration :

```bash
idf.py menuconfig
```

- `ESP32 CSI Tool Config` → renseigner SSID + password de la box, cocher "collect CSI"
- `Component config → Wi-Fi` → cocher `WiFi CSI(Channel State Information)`

## Flash

```bash
idf.py -p /dev/ttyACM0 flash monitor
```

Récupérer l'IP de l'ESP dans les logs (`sta ip: 192.168.1.XX`), quitter le
monitor avec `Ctrl+]`.

## Scripts Python

Placés dans `utils/` du repo. `csi_bridge.py` lit le port série en gardant DTR
bas (évite le reset auto). `csi_presence.py` calcule l'écart-type glissant des
amplitudes CSI par sous-porteuse et affiche une fenêtre matplotlib avec bande
rouge quand un mouvement est détecté.

## Utilisation

Deux terminaux.

Générateur de trafic (l'ESP ne produit du CSI que sur les paquets reçus) :

```bash
sudo ping -i 0.02 <IP_ESP>
sudo ping -i 0.02 192.168.1.91 -q

```

Lecture + visualisation :

```bash
python3 -u utils/csi_bridge.py | python3 -u utils/csi_presence.py
```

Le terminal affiche `rate=…Hz motion=…` deux fois par seconde. Rester immobile
5-10 s pour observer la baseline, puis bouger dans l'axe box↔ESP pour voir la
courbe décoller.

## Paramètres

En haut de `utils/csi_presence.py` :

- `FIXED_THRESHOLD` — seuil au-dessus duquel une présence est déclarée.
  Environnement calme : ~2.0. Openspace bruyant : ~4.5. À caler à mi-chemin
  entre motion au repos et motion en mouvement observés.
- `WINDOW_SEC` — fenêtre glissante en secondes. 1.0 pour de la réactivité,
  2.0 pour absorber les trous de rate CSI.

## Notes

- L'ESP a besoin de trafic **entrant** pour produire du CSI en continu. Le ping
  vers son IP est ce qui garantit un flux stable.
- L'IP de l'ESP peut changer au reboot ; la relever à chaque session via
  `idf.py monitor` ou le DHCP de la box.
- La box peut rate-limiter les réponses ICMP, plafonnant le rate autour de
  25-30 Hz même avec un ping à 50 pps.
- La qualité de la détection dépend fortement de l'environnement : très bonne
  dans une pièce calme, dégradée en openspace saturé de trafic WiFi.




