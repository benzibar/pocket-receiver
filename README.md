# Pocket Receiver

Pocket Receiver is a standalone, keyboard-first RTL-SDR radio for a Raspberry Pi
with a PocketTerm35 (640×480), or any Linux terminal of at least 64×22 characters.
It uses only the Python standard library for the interface.

Observe UK law and licence conditions. Band labels are a compact operating aid,
not permission to receive or disclose traffic.

The layout follows the supplied mock-up: Frequency, Mode, Bandwidth and Gain are
on the left; antenna length, UK allocation, signal-metric availability and volume
are on the right; the essential keys are always shown at the bottom.

Version 1.1.0 improves footer contrast, automatically opens selection menus upward
when necessary, and replaces unavailable RF metrics with live audio level and SDR
state indicators.

## What it does

- Displays frequency as exactly seven digits: `0,104.000 MHz`.
- Opens focused fields with Enter and commits them with Enter.
- Edits frequency one digit at a time; numbers replace and advance, arrows select
  or increment a digit, and only digits are accepted.
- Retunes 500 ms after the last frequency edit while playing, or immediately on
  Enter.
- Provides mode-aware menus for AM, NFM, WFM, USB and LSB bandwidths.
- Supports tuner gain Auto/20/40/60/80 dB.
- Changes PCM volume from 0–100% without retuning.
- Cooperatively stops `readsb` on first play and restores it at final exit, but
  only when Pocket Receiver was the process that stopped it.
- Captures useful RTL-SDR/ALSA errors and monitors and reaps both child processes.

## Install on Raspberry Pi

On the Pi, clone the GitHub repository and run:

```bash
cd pocket-receiver
bash scripts/install.sh
```

The script installs `rtl-sdr`, ALSA tools and Python venv support, then creates a
local `.venv` and installs the `pocket-receiver` command.

If an RTL2832 DVB kernel driver claims the dongle, follow the Raspberry Pi OS
`rtl-sdr` package guidance for blacklisting `dvb_usb_rtl28xxu`, then reboot. Check
the device independently with:

```bash
rtl_test -t
```

Pocket Receiver expects the existing passwordless rules to permit exactly:

```text
systemctl stop readsb
systemctl start readsb
```

It uses `sudo -n`, so a missing rule becomes a visible error instead of opening a
password prompt underneath the full-screen UI.

## Run

```bash
source .venv/bin/activate
pocket-receiver
```

Start immediately on FM broadcast:

```bash
pocket-receiver --frequency 104.0 --mode WFM --bandwidth 200 --gain Auto --volume 30 --play
```

An airband example:

```bash
pocket-receiver -f 121.500 -m AM -b 12 -g 40 -v 50 --play
```

This is also the launch interface for Spectrum or another app. Execute the
command as an argument array (not a shell string), for example:

```python
subprocess.Popen([
    "/home/bdm198/pocket-receiver/.venv/bin/pocket-receiver",
    "--frequency", "145.500",
    "--mode", "NFM",
    "--bandwidth", "12.5",
    "--gain", "Auto",
    "--volume", "40",
    "--play",
])
```

Additional options:

```text
--device 0              RTL-SDR device index
--audio-device default  ALSA PCM device
--no-readsb             Never manage the readsb service
--version               Print the installed version
```

Use `pocket-receiver --help` for the authoritative option list.

## Keys

When browsing fields:

| Key | Action |
|---|---|
| Up / Down | Move focus |
| Enter | Edit the focused field |
| `p` | Play/pause |
| `m` / `n` | Volume up/down by 10% |
| `q` | Quit (only when not editing) |

While editing Frequency:

| Key | Action |
|---|---|
| `0`–`9` | Replace selected digit and advance |
| Left / Right | Select a digit |
| Up / Down | Increment/decrement selected digit |
| Enter | Commit and retune immediately |
| Esc | Cancel |

While editing Mode, Bandwidth or Gain, Up/Down changes the highlighted menu item,
Enter commits it, and Esc cancels it. `p`, `m` and `n` remain global controls.

## Signal information

The information panel shows a live RMS audio level in dBFS. It is measured from
the demodulated signed-16-bit PCM before the user's volume adjustment, so changing
volume does not falsify the meter. This is an audio activity indication, not RF
signal strength.

The SDR status reads `receiving` while the pipeline owns the dongle, `reserved`
when this app has paused playback but continues holding the readsb reservation,
and `standby` before a lease is needed. `rtl_fm` does not publish calibrated RSSI
or SNR telemetry, and the RTL2832U cannot be shared with `rtl_power`. A future
single-process IQ/DSP backend could calculate relative channel power and SNR from
the audio IQ samples, but should label power as dBFS/relative unless the particular
receiver has been calibrated against a known RF source.

## Audio and mode notes

The pipeline is:

```text
rtl_fm → in-process signed-16-bit volume scaler → aplay
```

`rtl_fm` itself provides AM/NFM/WFM/USB/LSB demodulation. The bandwidth selection
sets its demodulator sample rate before resampling audio to 48 kHz. Actual usable
filter shape and SSB quality are constrained by `rtl_fm`; this app does not claim
communications-receiver-grade DSP.

## Windows → GitHub → Raspberry Pi workflow

1. Unzip/download this project on Windows and create a new GitHub repository.
2. In PowerShell, from the project directory:

   ```powershell
   git init
   git add .
   git commit -m "Initial Pocket Receiver rebuild"
   git branch -M main
   git remote add origin https://github.com/YOUR-NAME/pocket-receiver.git
   git push -u origin main
   ```

3. On the Raspberry Pi:

   ```bash
   git clone https://github.com/YOUR-NAME/pocket-receiver.git
   cd pocket-receiver
   bash scripts/install.sh
   source .venv/bin/activate
   pocket-receiver
   ```

For later updates, commit/push on Windows, then run `git pull` on the Pi. If
packaging files changed, rerun `bash scripts/install.sh`.

## Development checks

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m compileall -q src
```

The hardware audio path can only be fully verified on Linux with the actual
RTL-SDR and ALSA device attached.
