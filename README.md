# g2flash

`g2flash` is a utility for installing firmware on Even Realities G2 smart
glasses, as well as a collection of firmware modifications that add features and
fix limitations of the glasses. The modifications themselves are made with
[Faceclaw](https://github.com/jimrandomh/faceclaw) in mind, but can be used by
any software that communicates with the G2 glasses using their BLE protocol. If
you are using this with Faceclaw, you can either use this tool to apply the
firmware mods, or use the flashing tool built in to Faceclaw's onboarding
process (both versions install the same firmware image). Installing using
Faceclaw is a bit more user friendly than installing using g2flash.

## Flash the glasses

> **Flashing custom firmware voids your warranty and can brick the glasses.**
> Proceed only if you understand and accept the risk.

### 1. Build the firmware image

On the computer that will run the flasher, you need Python 3 with `venv`,
internet access, `curl` or `wget`, and `shasum` or `sha256sum`. Run this from
the g2flash checkout.

```bash
./build_cfw.sh
```

The script sets up `./venv` with the flasher's dependencies, downloads stock
G2 2.3.0.24 from Even's CDN, and applies the committed patches. It verifies
both images against pinned SHA-256 hashes and leaves the result in
`g2_2.3.0.24_cfw.bin`. Applying the committed patch set requires no compiler.

On Debian or Ubuntu, install `python3-venv` if Python reports that
`ensurepip` is unavailable. If the failed build already created `venv/`,
run `python3 -m venv venv` to complete its setup before retrying the build.

### 2. Choose and set up a connection

Power on both arms and keep the glasses close to the computer or Android phone
that will connect to them.

#### Direct Bluetooth on Linux or macOS

1. Turn off Bluetooth on the phone that normally connects to the glasses so
   both arms advertise. If another app on the computer is connected to the
   glasses, disconnect it too.
2. On Linux, make sure BlueZ has a pairing agent and accept any prompts when
   the flasher requests pairing. If you have no desktop pairing agent, open
   `bluetoothctl`, run `agent on` and `default-agent`, and keep it open while
   running the flasher in another terminal. On macOS, allow Bluetooth access
   for your terminal if prompted. CoreBluetooth manages pairing and may prompt
   for each arm.
3. Scan with the same Python environment the flasher will use.

```bash
./venv/bin/python - <<'PY'
import asyncio

from bleak import BleakScanner
from g2flash import G2_NAME_RE


async def scan() -> None:
    devices = await BleakScanner.discover(timeout=15, return_adv=True)
    for device, advertisement in devices.values():
        name = advertisement.local_name or device.name or ""
        if G2_NAME_RE.search(name):
            print(f"{name}  {device.address}")


asyncio.run(scan())
PY
```

Pick the `_L_` and `_R_` names with the same pair number. Use the addresses
printed by the scan. Linux prints MAC addresses and macOS prints CoreBluetooth
UUIDs. Replace the placeholders in this command.

```bash
connection='g2://local?left=<left-address>&right=<right-address>'
```

#### Through an Android phone running DroidBridge

Use a phone already bonded to both arms. Leave its Bluetooth on, start
DroidBridge, and make sure the computer can reach the bridge. Fill in the
phone's host and port, the bridge token if configured, and both arms' MAC
addresses. Omit the `token` parameter if the bridge has no token.
[DroidBridge setup](https://github.com/jimrandomh/droidbridge#readme)

```bash
connection='g2://droidbridge?phone=<host>&port=<port>&token=<token>&left=<left-mac>&right=<right-mac>'
```

### 3. Check the connection before starting OTA

Use the connection string you just set. This checks discovery and application
authentication on both arms. Direct Linux connections can create a Bluetooth
bond during this check. The command stops before OTA BEGIN and FILE_CHECK.
`--my-warranty-is-void` skips the warranty prompt for this connection check.

```bash
./venv/bin/python g2flash.py -c "$connection" -f g2_2.3.0.24_cfw.bin \
  --stop-before file_check --my-warranty-is-void
```

Look for `authentication: ok` on both arms and `all selected lenses completed.`.
If an arm is missing from the scan, check that it is powered on and that the
phone is disconnected when using direct Bluetooth.

### 4. Flash and verify both arms

```bash
./venv/bin/python g2flash.py -c "$connection" -f g2_2.3.0.24_cfw.bin
```

Type `my warranty is void` at the prompt. The flasher processes the arms one at
a time. Wait for `all 6 components verified` on each arm, then for
`all selected lenses completed.`. Let the glasses reboot before reconnecting
them to your phone.

## Usage

```text
./venv/bin/python g2flash.py -c <connection-string> -f <firmware.bin> [options]
```

- `--lens left|right|both` selects which arm to flash. The default is `both`.
- `--stop-before discover|heartbeat|file_check|flash|done` stops at a stage.
  Use `heartbeat` to stop after discovery, `file_check` to authenticate and stop
  before OTA, or `flash` to send BEGIN and the first FILE_CHECK and stop before
  sending firmware data. `done` runs the full flash.
- `--my-warranty-is-void` skips interactive warranty confirmation for
  automation.
- `--component-retries N` and `--block-nak-retries N` tune transfer retries.
- `--reconnect-attempts N` and `--reconnect-delay SECONDS` tune recovery after
  the flasher loses an ACK.
- `--debug` prints received BLE frames.

Run `./venv/bin/python g2flash.py --help` for the full CLI reference and
`./build_cfw.sh --help` for build options. A local connection string also
accepts the optional `addressType` label (`public` for a MAC address or
`random` for a CoreBluetooth UUID).

After a length-preserving binary patch, run
`./venv/bin/python g2flash.py --recompute-checksums g2_2.3.0.24_cfw.bin`
to update the component CRC32C and main application preamble CRC32 in place.
This command exits without connecting to the glasses.

### Manage the Python environment manually

```bash
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
./build_cfw.sh --skip-venv
```

The local transport uses `bleak>=1.0` and DroidBridge uses
`websocket-client`. You only need the package for the transport you use.
Firmware parsing, validation, and checksum updates use the Python standard
library.

## Modifications

Some features this has (used by Faceclaw, but the exact API may not be fully documented):

 * Use the full 640x480 resolution of the screens, not just the 576x288 exposed
   by the EvenHub API
 * Upload display lists, which define instructions for redrawing the screen to
   make animations without needing to send messages for each frame
 * Compressed message transport, including cross-message compression
 * Modified bluetooth radio settings, greatly increasing transfer speed
 * Receive ring and temple-touchpad long-press and long-press-release as regular
   source-qualified gestures, rather than opening a modal offering to quit
 * Receive 2.2.9's tap-then-long gesture as distinct private event type 11 and,
   while the framebuffer lease is held, suppress its incompatible stock Menu path
 * Play sound effects with the piezo buzzer
 * Receive on-head detection wear/unwear events, to trigger a lock-screen
 * Use the magnetometer as a compass. Faceclaw/14 preserves the current magnetic
   calibration accuracy across IMU reconfiguration while the Faceclaw framebuffer
   lease is valid, including compass stop/start cycles. See
   [calibration preservation](docs/compass-calibration.md).
 * Read the ambient light sensor (a TI OPT3001 on the master temple) and,
   optionally, run it in a "passive" mode where the firmware polls the sensor
   for the phone but the stock auto-brightness adjuster never steps the panel,
   so the phone can implement its own brightness policy (image-handler mode 16;
   readings arrive as settings-channel field 105). See the contract comment in
   `patches/als_sensor.c`.
 * Take over the wakeword ("hey Even") and replace what it opens with a
   different phone-side transcription and AI agent pipeline
 * Take over the screen-wake even on the dashboard, so that you can end the
   EvenHub session (putting the glasses in a low-power mode) and return to
   Faceclaw with a double-tap
 * While the glasses are in that low-power mode (no app on screen), also
   report the single tap, long press and long-press release that the stock
   display thread drops, so the phone can show a lightweight sleep-time
   display (Faceclaw's Glanceboard) without a full wake

Glasses with a custom firmware identify themselves with the version number of
the stock firmware that the modded version is based on, with an extra field in
the settings-response message (protobuf field 100) carrying a firmware revision
string of the form `Faceclaw/<n>`. See `settings_send_wrapper` in
`patches/settings_ext.c`. `<n>` goes up each time the firmware contract changes
and is not kept in sync with Faceclaw phone-app versions; the phone app requires
a specific revision and offers to reflash when the installed one is older. Older
builds advertised `EVENCFW/<ver>` followed by feature tokens instead. If writing
your own firmware and your own phone software to go with it, use a different
prefix, and assume that firmware is only compatible if you recognize the exact
string.

Custom firmwares in this repository are intended to be backwards-compatible
with the official Even Realities app; ie, if the phone doesn't send any
bluetooth messages that make use of the added features, it will behave the same
way. In practice, this isn't tested, and using a custom firmware with the
official Even app may introduce bugs. EvenHub apps are especially likely to be
broken by custom firmware, since most of the modifications are to
EvenHub-related functionality.

Custom firmwares are currently _not_ expected to be compatible with each other.
When you update Faceclaw, you should update the firmware at the same time. If
you are writing your own software that relies on custom firmware, you probably
want to specify a particular CFW version. (This will probably change in the
future, when there is less new stuff still to be added.)

What _is_ tested for compatibility is the OTA updater. This firmware does not
make any changes to how OTA updates are installed. If you connect the official
Even app to your glasses, and it has a firmware that's newer than the one your
CFW is based on, it will offer to install an update. Installing an OTA update
using the official Even app will fully remove the custom firmware and restore
it to stock behavior. You can also go back to stock firmware by installing an
unmodified firmware image using g2flash, or the "Uninstall firmware" menu item
in Faceclaw.

## Developing firmware patches

DEVELOPING YOUR OWN FIRMWARE MODS IS MUCH RISKIER THAN INSTALLING FIRMWARE THAT
HAS ALREADY BEEN TESTED. If you are considering writing firmware mods and you
can complete a project using only phone-side changes, you are almost certainly
better off doing it that way. It is a bad idea to work in this codebase using a
non-frontier language model, or without a proper coding harness, or a
nontechnical user steering.

Changes that involve overwriting parts of the existing firmware are more risky
than changes to the existing C extension files. Changes that run or affect
behavior prior to receiving any custom messages are especially risky, because
if you make the glasses crash on boot, they won't be able to accept an OTA
update. Rebasing the mods onto a new base firmware is an especially hazardous
operation, since it requires updating every firmware offset correctly and not
missing any.

### What's in this directory

- `g2flash.py` — the flasher.
- `build_cfw.sh` — one-shot venv setup + download + patch + verify (see above).
- `patches/` — the patch sources and tools:
  - `cfw_patches.json` — the **committed patch set**: a list of
    offset/expected-old/new byte patches (plus base + output SHA-256s) that turns
    the stock image into the CFW image. This is the source of truth for the build.
  - `apply_patches.py` — replays `cfw_patches.json` onto the stock image. **No
    compiler** — pure Python stdlib, so it runs anywhere (a phone, a fresh box).
    This is what `build_cfw.sh` uses to produce the image.
  - `gen_patches.py` — compiles the injected code with **clang** and (re)generates
    `cfw_patches.json`. Run it after editing the patch sources:
    `python3 patches/gen_patches.py g2_2.3.0.24.bin patches/cfw_patches.json`
    (or `./build_cfw.sh --update-patches`), then commit the JSON.
  - `patch_compress.py` — the all-in-one patcher (576 carrier lift + image
    compression + direct framebuffer presentation + capability field);
    `gen_patches.py` calls it to build the ops.
    Defines live patch sites; stock function and RAM references also live in
    the C sources. `audit_stock.py` checks their reviewed inventory and stock
    byte guards in `stock_abi_230.json` before generation. See the
    [2.3.0.24 rebase review](docs/firmware-rebase-2.3.0.md) for every migrated
    site, nearby behavior changes, and validation of Faceclaw/17.
  - `build.py`, `*.c` — the C→position-independent-Thumb pipeline and sources
    for the injected firmware code (compiled by `gen_patches.py`; the resulting
    machine code lands in `cfw_patches.json`).
- `requirements.txt` — the flasher's Python dependencies.

Firmware images (`g2_2.3.0.24*.bin`) are **not** checked in — they are Even's
firmware, so you build them locally with `build_cfw.sh`.

## How it works (brief)

The flasher speaks the same `aa21`-framed envelope protocol as the official
app, validated byte-for-byte against a real flash capture. The firmware image
is an EVENOTA container of five or six components; each is streamed over the firmware
data service (`...e1001`) as a FILE_CHECK subheader followed by 4 KB blocks,
then an END check the glasses verify against a per-component CRC32C. Before
BEGIN, it performs the stock control-channel authentication handshake. On Linux,
it also requests BlueZ pairing to enable Bluetooth link encryption.
OTA data fragments refresh the transfer watchdog. The
official OTA capture sends no EvenHub-control heartbeats between BEGIN and the
final END, so neither does this flasher. DroidBridge flashes also reuse one HTTP connection
instead of opening one per BLE fragment. If an ACK is lost, the flasher never
risks replaying that ambiguous block in place: it reconnects, restores
notifications, sends a fresh BEGIN, and restarts the entire component from
FILE_CHECK. Arms are flashed one at a time. See the module docstring and comments
in `g2flash.py` for the wire-level details and the retry/recovery rationale.


## Contributing

PRs welcome, especially of firmware mods that unlock functionality that isn't
usable in the stock firmware. Please only submit changes that you've tested on
a real device.


# Acknowledgements

Thanks to kalanihelekunihi for [evenRealities-openCFW](https://github.com/kalanihelekunihi/evenRealities-openCFW/) and Commute773 for [g2-kit-unofficial](https://github.com/Commute773/g2-kit-unofficial/), which were immensely helpful while creating this.

### Experimental BLE keyboard bridge

`Faceclaw/39` adds an explicitly enabled right-lens BLE keyboard connection,
with HID reports relayed to the phone alongside ring input. It comes from
[tetramo-labs/g2flash](https://github.com/tetramo-labs/g2flash), where it has
been installed and used with physical keyboards; this repository's build of it
has only been through the offline checks and the emulator scenarios. Faceclaw
drives it from `app/g2/keyboard/`; a reference client and CLI are in
`demos/keyboard*.ts`. See
[setup, protocol and validation limits](docs/keyboard.md) and the
[donor ABI review](docs/keyboard-abi.md).
