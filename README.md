# Ralph Codes 4 OpenCode

<img width="802" height="732" alt="image" src="https://github.com/user-attachments/assets/daacf6b9-1d58-4536-8c01-3f2d36016749" />



A cross-platform GUI application for setting up and running AI-assisted coding tasks using OpenCode CLI.

*"Me fail English? That's unpossible!"* - Ralph Wiggum

## Features

- **Cross-Platform Support**: Works on Windows and Linux
- **Dark Mode Interface**: Easy on the eyes with Ralph Wiggum branding
- **Model Selection**: Choose from available OpenCode models
- **Task Management**: Track multiple concurrent running tasks
- **Automatic Backup**: Backs up existing files before each run
- **Completion Viewer**: GUI viewer shows results when tasks complete
- **Voice Feedback**: Text-to-speech completion notifications (Windows, macOS, Linux)

## Prerequisites

- Python 3.9 or higher
- [OpenCode CLI](https://opencode.ai/) installed and configured
- tkinter (usually included with Python)

## Installation

### Option 1: Install from source

```bash
# Clone the repository
git clone https://github.com/ralph-codes/ralph.git
cd ralph

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

# Or if installed as package
ralph
```

### Using Ralph

1. **Select Target Folder**: Choose a project folder where Ralph will work
2. **Choose Model**: Select an AI model from the dropdown (recently used models appear first)
3. **Enter Design**: Write your task/design in the text area
4. **Run Ralph**: Click "Run Ralph" to start the AI coding task

### How It Works

1. Ralph creates a `RALPH-DESIGN.md` file with your instructions
2. Launches OpenCode CLI in a new terminal window
3. OpenCode reads the design and begins working
4. Progress is tracked in `RALPH-PROGRESS.md`
5. When complete, `RALPH-COMPLETE.md` is created
6. The viewer automatically opens to show results

### Files

| File | Purpose |
|------|---------|
| `RALPH-DESIGN.md` | Your task/design instructions |
| `RALPH-PROGRESS.md` | AI's work-in-progress notes |
| `RALPH-COMPLETE.md` | Final completion summary |
| `ralph.cmd` / `ralph.sh` | Platform launcher scripts |

## Configuration

Recent folders and models are saved automatically to:
- `recent_folders.json`
- `recent_models.json`

Logs are written to `ralph.log`.

## Project Structure

```
├── ralph_gui.py        # Main GUI application (includes integrated viewer and TTS)
├── ralph.cmd           # Windows script for OpenCode CLI
├── ralph.sh            # Linux script for OpenCode CLI
├── run_ralph.cmd       # Windows GUI launcher
├── run_ralph.sh        # Linux GUI launcher
├── ralph.jpg           # Application branding
├── config.ini          # Configuration settings
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Package configuration
└── backup/             # Automatic backups (created at runtime)
```

## Development

### Install development dependencies

```bash
pip install -e ".[dev]"
```

### Run linting

```bash
ruff check .
```

### Type checking

```bash
mypy ralph_gui.py
```

## License

MIT License

## Acknowledgments

- Inspired by Ralph Wiggum from The Simpsons
- Built for use with [OpenCode CLI](https://github.com/opencode-ai/opencode)
