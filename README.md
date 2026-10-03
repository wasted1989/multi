# Wind Waker Mod Bundle Creator

Create an uncompressed, Zip64-compatible archive from a directory of Wind
Waker mod files. The archive keeps the source directory as its top-level
folder and can be built from either the command line or a Tkinter interface.

## Command line

```bash
python3 wind_waker_bundler.py --stage /path/to/mods --output bundle.zip
```

Existing archives are never overwritten. Pass `--replace-empty` to remove a
zero-byte archive left behind by an interrupted build. Run the script without
arguments (or with `--gui`) to launch the graphical interface when Tkinter is
available.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
