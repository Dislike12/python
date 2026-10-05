# Safe File Organizer

A small utility that groups the **direct child files** of a directory into folders named by extension. It never recurses and skips symlinks.

## Preview first

```bash
python -m projects.file_organizer.app ~/Downloads
```

The default is a dry run: it prints planned moves and changes nothing. To apply the displayed plan:

```bash
python -m projects.file_organizer.app ~/Downloads --apply
```

Files without a suffix go into `no_extension/`. Existing names are preserved; if a destination already exists, the organizer chooses a numbered name rather than overwriting it. Review the preview before using `--apply`. This is a local filesystem tool; test on a copy if the files are important.
