# Pocket Receiver v0.1.5

Compact RTL-SDR audio receiver for the Waveshare PocketTerm35.

## Features
- Frequency entry in MHz
- AM / NFM / WFM / USB / LSB
- RTL gain: Auto / 10 / 20 / 30 / 40 dB
- Volume: 25 / 50 / 75 / 100%
- PocketTerm Start button: start/stop listening
- Q: exit
- Hardened readsb SDR lease matching Pocket Spectrum v0.3.5
- CLI launch support for future Spectrum integration

## Pi prerequisites

```bash
sudo apt install rtl-sdr alsa-utils
```

The existing sudoers rule is required:

```text
bdm198 ALL=(root) NOPASSWD: /usr/bin/systemctl stop readsb, /usr/bin/systemctl start readsb
```

## Install

```bash
cd ~/pocketterm/apps/pocket-receiver
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
pocket-receiver
```

Or pre-tune:

```bash
pocket-receiver --frequency 100.0 --mode WFM
```

## v0.1.3

- Changed Listen/Stop from Space to `L` so the frequency input can retain normal text-entry behaviour.

## v0.1.4

- Made `L` and `Q` priority Textual bindings so they work even while the frequency Input or a Select widget has focus.

## v0.1.5

PocketTerm hardware controls:
- Start (`KEY_PAUSE`) = Listen / Stop
- Select (`KEY_SYSRQ`) = Quit / Back

The previous L/Q receiver hotkeys have been removed so normal keyboard input remains available to focused fields.
