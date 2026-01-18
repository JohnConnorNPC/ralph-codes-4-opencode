# Ralph Codes 4 OpenCode


<img width="802" height="984" alt="image" src="https://github.com/user-attachments/assets/b0e4b879-aec1-4c62-8578-216fdfb796ed" />



A cross-platform GUI application for setting up and running AI-assisted coding tasks using OpenCode CLI.

*"Me fail English? That's unpossible!"* - Ralph Wiggum

## Features

- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Dark Mode Interface**: Easy on the eyes with Ralph Wiggum branding
- **Model + Variant Selection**: Choose OpenCode models and variants
- **Task Management**: Track multiple concurrent running tasks
- **Loop Controls**: Pause, resume, or stop running tasks
- **Automatic Backup**: Backs up existing files before each run
- **Completion Viewer**: GUI viewer shows results when tasks complete
- **opencode.json Editor**: Edit permission presets inside the app
- **Voice Feedback**: Text-to-speech completion notifications (Windows, macOS, Linux)


## Prerequisites

- Python 3.9 or higher
- [OpenCode CLI](https://opencode.ai/) installed and configured
- tkinter (usually included with Python)

## Installation

### Option 1: Install from source

```bash
# Clone the repository
git clone https://github.com/JohnConnorNPC/ralph-codes-4-opencode.git
cd ralph-codes-4-opencode


# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

### Option 2: Install dependencies only

```bash
pip install Pillow
```

### Linux: Install tkinter if needed

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

## Usage

### Launch the GUI

```bash
# Run directly
python ralph_gui.py

# Or use the convenience launcher
run_ralph.cmd   # Windows
./run_ralph.sh  # Linux/macOS

# Or if installed as package
ralph

```

### Using Ralph

1. **Select Target Folder**: Choose a project folder where Ralph will work
2. **Choose Model + Variant**: Select an AI model and optional variant from the dropdown
3. **Configure opencode.json**: Optionally edit/copy the OpenCode config for the run
4. **Enter Design**: Write your task/design in the text area
5. **Run Ralph**: Click "Run Ralph" to start the AI coding task


### How It Works

1. Ralph writes `RALPH-DESIGN.md` and copies `RALPH-SPECS.md` (and optional `opencode.json`) to the target folder
2. Launches OpenCode CLI using the instructions in `RALPH-PROMPT.md`
3. OpenCode updates `RALPH-PLAN.md` and `RALPH-PROGRESS.md` each iteration
4. Each iteration ends with `RALPH-CHECKPOINT.md` until completion
5. Completion creates `RALPH-COMPLETE.md`; blocked runs create `RALPH-BLOCKED.md`
6. The viewer opens to show results and plays a Ralph quote


### Files

| File | Purpose |
|------|---------|
| `RALPH-DESIGN.md` | Your task/design instructions |
| `RALPH-PLAN.md` | Checklist for each iteration |
| `RALPH-PROGRESS.md` | Append-only progress log |
| `RALPH-CHECKPOINT.md` | Signals one iteration done |
| `RALPH-COMPLETE.md` | Signals all requirements done |
| `RALPH-BLOCKED.md` | Signals blocked state |
| `RALPH-PROMPT.md` | Prompt template for OpenCode |
| `RALPH-SPECS.md` | Lookup table of patterns |
| `run_ralph.cmd` / `run_ralph.sh` | Platform GUI launchers |
| `opencode.json` | Optional OpenCode config copied to target |


## Configuration

Recent folders and models are saved automatically to:
- `recent_folders.json`
- `recent_models.json`
- `recent_variant.json`

Ralph GIF URLs and quotes live in `ralph_content.json` and are cached in `gif_cache/`.
Logs are written to `ralph.log`.


## Project Structure

```
├── ralph_gui.py        # Main GUI application (includes integrated viewer and TTS)
├── run_ralph.cmd       # Windows GUI launcher
├── run_ralph.sh        # Linux/macOS GUI launcher
├── opencode.json       # Optional OpenCode config template
├── ralph_content.json  # Ralph GIF URLs and quotes
├── RALPH-*.md          # Prompt templates and scaffolds
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Package configuration
├── gif_cache/          # Cached GIFs (created at runtime)
└── backup/             # Automatic backups (created at runtime)

```

## Development

### Install development dependencies

```bash
pip install -e ".[dev]"
```

MIT License

## Acknowledgments

 
- Built for use with [OpenCode CLI](https://github.com/opencode-ai/opencode)
- Inspired by [The Ralph Wiggum Loop from 1st principles](https://www.youtube.com/watch?v=4Nna09dG_c0&start=2) — Geoffrey Huntley (creator of Ralph)

