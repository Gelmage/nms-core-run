# The Run To Core

A No Man's Sky teleporter planner. It reads your save and tells you, for every
teleporter destination you have banked, whether it is **closer to the galactic
core than where you are standing right now**.

The game does not show this. When you open a space station teleporter you get a
list of names with no indication of which way any of them takes you. If you are
running for the core, that matters: a jump can quietly put you further out than
you have already been, and you will not find out until you arrive.

![The verdict panel: where you are, the best teleport available, and the gain](screenshots/main.png)

Every destination ranked, with the ones that move you inward marked in green:

![The full destination table](screenshots/destinations.png)

## What it tells you

- How far you are from the core, in light years
- The best teleport available to you, and how much it gains or loses
- Every destination ranked, with the ones that move you inward marked
- A chart of your whole network against your current position
- Destinations stranded in galaxies you have left, greyed out, because the
  teleporter will not offer them

## Download and run

**[Get the latest release](../../releases/latest)** and pick the file for your
system. Each one is a single executable with Python built in, so there is
nothing to install.

| System | File |
| --- | --- |
| Windows | `run-to-core-windows.zip` |
| Steam Deck and Linux | `run-to-core-linux.zip` |
| Mac (Apple silicon) | `run-to-core-macos-arm64.zip` |

A small console window stays open the whole time the tool is running. That
window is the program: closing it stops the tool and shuts down the local page.

### Windows

1. Download `run-to-core-windows.zip` and extract it. Right-click the zip,
   choose **Extract All**, and pick any folder you like.
2. Run `run-to-core.exe`.
3. Windows will show a blue **"Windows protected your PC"** box. See
   [About the warnings](#about-the-warnings) below for what this is and how to
   decide. To continue, click **More info**, then **Run anyway**.
4. A console window opens and your browser shows the page. Leave the console
   window open while you play.

If you would rather not click past a security warning, the
[Running from source](#running-from-source) section needs no executable at all.

### Steam Deck

The Deck can run this, but only from Desktop Mode, since Gaming Mode has no file
manager.

1. Hold the power button and choose **Switch to Desktop**.
2. Download `run-to-core-linux.zip` and extract it.
3. Right-click `run-to-core`, choose **Properties**, open the **Permissions**
   tab, and tick **Is executable**.
4. Double-click it. SteamOS already has a browser for the page to open in.

To reach it from Gaming Mode later, right-click `run-to-core` while still in
Desktop Mode and choose **Add to Steam**. It will then appear in your library
under Non-Steam games.

### macOS

No Man's Sky on Mac requires Apple silicon, so only that build is provided.

1. Download `run-to-core-macos-arm64.zip` and open it.
2. **Right-click** `run-to-core` and choose **Open**, then confirm **Open** in
   the dialog. Do not double-click it: macOS refuses unsigned applications
   opened that way, and gives you no option to continue.
3. Your browser opens the page. Leave the Terminal window open while you play.

You only need the right-click step the first time.

### Linux

1. Download `run-to-core-linux.zip` and extract it.
2. Make it executable and run it:

```
chmod +x run-to-core
./run-to-core
```

## About the warnings

Windows and macOS both warn about this download. The warning is accurate, and it
is worth understanding rather than clicking past on someone's say-so.

**What the warning actually means.** Both systems check whether software carries
a code-signing certificate identifying its publisher. This project has no such
certificate, so your computer correctly reports that it cannot tell you who
wrote it. The message means "unidentified", not "inspected and found harmful" --
but it equally does not mean "inspected and found safe". Your computer is
telling you it does not know, which is true.

**Why there is no certificate.** Windows code-signing certificates cost roughly
200 to 400 US dollars a year and, since 2023, require dedicated hardware to hold
the key. Apple charges 99 dollars a year. This is a free tool with no income, so
that expense is not justified. Nothing more interesting than that is going on.

**What you can check instead.** Rather than asking you to take anyone's word for
it, this project gives you three ways to verify it yourself:

- **Read the source.** The entire tool is in this repository: about a thousand
  lines of Python and one HTML page. There is no build step and nothing
  obfuscated. The part that touches your save is `nms_save.py`, and it is worth
  a look if you are curious -- every file operation on a save is a read.
- **Check the download matches.** Every release includes a `.sha256` file so you
  can confirm your download is byte-for-byte what was published.
- **Check where the binary came from.** Each release is built by a public GitHub
  Actions workflow and carries signed provenance tying it to a specific commit
  in this repository. With the [GitHub CLI](https://cli.github.com/) installed
  (version 2.49 or newer -- the version packaged by some Linux distributions is
  older than that and has no `attestation` command):

```
gh attestation verify run-to-core-windows.zip --repo Gelmage/nms-core-run
```

  That confirms the file you downloaded was produced by this repository's
  workflow from the source you can read, and not modified afterwards.

**Or skip the executable entirely.** Running from source needs no downloaded
binary and triggers no warnings, because you are running code you can read with
a Python interpreter you installed yourself. That is the most cautious option,
and it is a perfectly reasonable one.

Being wary of unsigned executables is good judgement, and none of the above is
meant to talk you out of it. Use whichever of these options you are comfortable
with.

## Running from source

Python 3.8 or newer. Nothing else -- no pip install, no dependencies. The LZ4
decompression the save format needs is included in this repository.

```
python3 core_run.py
```

That is the whole thing. It finds your save, opens a page in your browser, and
keeps it up to date while you play.

On Windows, `Run To Core (Windows).bat` does the same thing with a double-click,
and tells you where to get Python if it is missing. `Run To Core (Mac).command`
and `run-to-core.sh` are the equivalents for macOS and Linux.

| Option | What it does |
| --- | --- |
| `--app` | Open as a plain window with no tabs or address bar |
| `--save PATH` | Read a specific save file or folder instead of searching |
| `--list` | List every save found on this machine, then exit |
| `--interval N` | Seconds between checks for a newer save (default 120) |
| `--port N` | Serve on a specific port (default 8787) |
| `--no-browser` | Do not open a browser window |

## How current the numbers are

The game writes your save when it saves -- when you dock, exit your ship, land,
or hit an autosave point. This reads that file, so the page follows a few seconds
behind those moments. It cannot track you continuously as you fly, because
nothing has been written to disk yet for it to read.

In practice this is exactly what you want: **when you dock at a new station, the
page has your new position by the time you have walked to the teleporter.**

The page re-checks on a timer and there is a **Check for a new save** button for
when you do not want to wait for it.

## Window mode

```
python3 core_run.py --app
```

opens the page as a plain window with no tabs and no address bar, using a
Chromium-family browser if one is installed -- your default browser is preferred,
so the window inherits the profile and theme you already use. Without one it
falls back to an ordinary tab. This adds no dependencies: it is the browser you
already have, without the browser furniture.

Launching a second time does not start a second copy. It notices the one already
running and opens that window instead.

## Finding your save

Detection is automatic and covers Steam on Windows, macOS, Linux and Steam Deck,
including games installed on secondary drives and SD cards. If it cannot find
yours, pass it directly:

```
python3 core_run.py --save "/path/to/save.hg"
```

Saves live in a folder named `st_<your steam id>` (or `DefaultUser` for GOG),
which holds `save.hg`, `save2.hg` and so on. Use `save.hg`, not
`accountdata.hg`. The usual locations:

**Windows**

```
%APPDATA%\HelloGames\NMS\st_<id>\
```

**macOS**

```
~/Library/Application Support/HelloGames/NMS/st_<id>/
```

**Linux and Steam Deck** (the game runs under Proton, so its saves sit inside a
Windows-style prefix)

```
~/.steam/steam/steamapps/compatdata/275850/pfx/drive_c/users/steamuser/AppData/Roaming/HelloGames/NMS/st_<id>/
```

On a Steam Deck, or with the game on another drive, replace `~/.steam/steam`
with that library's path -- for example `~/.local/share/Steam` or
`/run/media/mmcblk0p1`. Running `python3 core_run.py --list` will show you every
save it can see, which is usually faster than hunting for it.

The Microsoft Store and Game Pass versions store saves in a different format and
are not supported.

## What it does to your save

Nothing. It only reads. Each of these is checkable in the source rather than
something you have to take on trust:

- Every file operation on a save is a read, all of them in `nms_save.py`. No function anywhere in this project
  opens a save for writing, and there is no code path that could modify, move or
  delete one.
- Nothing is uploaded. The server it starts is bound to `127.0.0.1` and is only
  there so the page can ask for updated numbers; it is not reachable from your
  network.
- Reading a save while the game is running is fine. Worst case you catch a
  half-written file, the read fails, and the page keeps the last good numbers.

Backing up your saves before running any unfamiliar tool is a good habit
regardless, and No Man's Sky keeps several rotating save slots of its own.

## How it works

A `.hg` save is a chain of LZ4-compressed blocks holding one JSON document whose
keys are obfuscated -- `VoxelX` is stored as `dZj`, and so on. Those names change
between game versions, so instead of shipping a key mapping that would go stale,
this identifies the pieces it needs by shape: a galactic address is the object
containing exactly five numbers, and a teleporter endpoint is one holding an
address plus a known type string.

Distance to the core is then

```
sqrt(x^2 + y^2 + z^2) * 400
```

where `x, y, z` are voxel coordinates and a voxel is 400 light years across.
Coordinates are relative to the centre of the galaxy you are in, so the figure is
correct in any galaxy.

Two details worth knowing:

- **Distance is a property of the voxel**, not the system, so every system in the
  same voxel shows the same distance. That is the game's own resolution, not a
  rounding error here.
- **Only teleporter endpoints carry names.** Ordinary discovered systems do not;
  their names are generated at runtime or live on Hello Games' servers. Where the
  page can name the system you are in, it is borrowing the name of a station or
  base of yours sitting in it. Freighters are excluded, since yours follows you
  around and its name says nothing about where you are.

Galaxies are named for the first ten indices, which covers a long run of core
jumps. Past that they display as `Galaxy 10`, `Galaxy 11` and so on, with
distances still correct. Guessed names would be worse than none.

## Licence

MIT. See [LICENSE](LICENSE).
