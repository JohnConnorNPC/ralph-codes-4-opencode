# RALPH-SPECS.md (Lookup Table)

> PIN file. Agent: study this FIRST to find existing patterns. Don't invent.
> Keywords improve search tool hit rate.

---

## GUI
- **src**: ralph_gui.py
- **keywords**: tkinter, dark theme, folder, model, combobox, viewer, tts, speech

## Loop
- **src**: ralph_loop.sh, ralph_loop.ps1, ralph.sh
- **keywords**: while, iteration, opencode, checkpoint, progress, done, blocked, stop

## Backup
- **src**: ralph_gui.py:1117-1142
- **keywords**: uuid, guid, backup, restore, copy

## Execution
- **src**: ralph_gui.py:1201-1243
- **keywords**: subprocess, popen, terminal, spawn, run

---

## Adding New Entries

```
## [Name]
- **src**: [file:lines]
- **keywords**: [word1], [word2], [synonyms]
```

Use words the search tool would match. More keywords = more hits = less inventing.
