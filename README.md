# Pocket Receiver v0.1.9

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


## v0.1.6

The PocketTerm Start and Select buttons are now read directly from Linux evdev
rather than relying on terminal/Textual key translation.

- Start: Linux `KEY_PAUSE` (119) -> Listen / Stop
- Select: Linux `KEY_SYSRQ` (99) -> Quit / Back
- The keyboard event device is discovered dynamically by its device name:
  `My Company My Custom Pico Keyboard`
- No hard-coded `/dev/input/eventN` number is used.

## v0.1.7

PocketTerm navigation:
- Up / Down moves focus between Frequency, Mode, Gain and Volume.
- Frequency remains a normal editable text field, so frequencies can be typed directly.
- Left / Right retains the Select widget's normal behaviour for Mode, Gain and Volume.
- Start remains Listen / Stop via direct evdev.
- Select remains Quit / Back via direct evdev.
- Focused fields use an explicit Textual focus border for clearer selection.

## v0.1.8

- Left / Right now explicitly cycle Mode, Gain and Volume.
- Frequency remains directly editable with normal keyboard input.
- Gain labels are now shown as Auto / 10 dB / 20 dB / 30 dB / 40 dB.
- Volume values are now stored consistently as strings and displayed as percentages.
- Mode values are explicit and stable.


## v0.1.9

- Replaced Textual Select/dropdown widgets with simple PocketTerm-native choice fields.
- Mode, Gain and Volume now show one plain value rather than a dropdown/slider control.
- Up/Down moves between fields.
- Left/Right cycles the focused Mode, Gain or Volume value immediately.
- Frequency remains a normal editable text field.
