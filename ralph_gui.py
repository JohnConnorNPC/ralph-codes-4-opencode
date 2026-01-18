#!/usr/bin/env python3
"""
Ralph GUI - A cross-platform GUI for setting up and running Ralph projects.

This application allows users to:
1. Select a target folder
2. Enter text for RALPH-DESIGN.md
3. Clean up existing files (RALPH-DESIGN.md, RALPH-PROGRESS.md, RALPH-COMPLETE.md)
4. Copy opencode.json configuration file (optional)
5. Create RALPH-DESIGN.md with the entered text
6. Run ralph in the target folder
7. Dark mode interface with Ralph Wiggum branding
8. Backup files to backup/guid folder
9. Track multiple concurrent running tasks
"""

import json
import logging
import os
import platform
import random

import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import uuid
from datetime import datetime

from tkinter import filedialog, messagebox, ttk
from typing import Optional

# Configure logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ralph.log")

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# Ralph Wiggum content - loaded from ralph_content.json
def _load_ralph_content() -> dict:
    """Load Ralph Wiggum GIF URLs and quotes from config file.

    Returns:
        Dictionary with 'gif_urls' and 'quotes' keys.
    """
    content_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ralph_content.json")
    try:
        with open(content_file, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load ralph_content.json: {e}")
        return {"gif_urls": [], "quotes": []}


# Load content at module level
_ralph_content = _load_ralph_content()
RALPH_GIF_URLS = _ralph_content.get("gif_urls", [])
RALPH_QUOTES = [f'"{q}"' for q in _ralph_content.get("quotes", [])]


class DarkTheme:
    """Dark theme color scheme."""

    BG_PRIMARY = "#1e1e1e"
    BG_SECONDARY = "#252526"
    BG_TERTIARY = "#2d2d30"
    BG_INPUT = "#3c3c3c"
    FG_PRIMARY = "#cccccc"
    FG_SECONDARY = "#9cdcfe"
    FG_DIM = "#808080"
    ACCENT = "#007acc"
    ACCENT_HOVER = "#1c97ea"
    SUCCESS = "#4ec9b0"
    WARNING = "#dcdcaa"
    ERROR = "#f14c4c"
    BORDER = "#3c3c3c"


def center_window_on_parent(window: tk.Toplevel, parent: Optional[tk.Tk]):
    """Center a window on its parent or screen center."""
    window.update_idletasks()
    if parent:
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - window.winfo_width()) // 2
        y = parent_y + (parent_height - window.winfo_height()) // 2
    else:
        x = (window.winfo_screenwidth() - window.winfo_width()) // 2
        y = (window.winfo_screenheight() - window.winfo_height()) // 2
    window.geometry(f"+{x}+{y}")


class RalphViewer:
    """Integrated viewer window to display RALPH-COMPLETE.md and RALPH-PROGRESS.md files."""

    def __init__(self, target_dir: str, parent: Optional[tk.Tk] = None):
        """Initialize the viewer window.

        Args:
            target_dir: Directory containing the RALPH files.
            parent: Optional parent window to center on (for multi-monitor support).
        """
        self.target_dir = target_dir
        self._parent = parent
        self.root = tk.Toplevel()
        self.root.title("RALPH - Task Complete")
        self.root.geometry("900x700")
        self.root.configure(bg=DarkTheme.BG_PRIMARY)

        self._create_widgets()
        self._center_window()

    def _read_file(self, filepath: str) -> str:
        """Read a file and return its contents."""
        try:
            with open(filepath, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return f"File not found: {filepath}"
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return f"Error reading file: {e}"

    def _create_widgets(self):
        """Create all GUI widgets for the viewer."""
        # File paths
        complete_path = os.path.join(self.target_dir, "RALPH-COMPLETE.md")
        progress_path = os.path.join(self.target_dir, "RALPH-PROGRESS.md")

        # Configure style for notebook tabs
        style = ttk.Style(self.root)

        style.configure("Viewer.TNotebook", background=DarkTheme.BG_PRIMARY)
        style.configure(
            "Viewer.TNotebook.Tab",
            padding=[20, 10],
            font=("Consolas", 11),
            background=DarkTheme.BG_SECONDARY,
            foreground=DarkTheme.FG_PRIMARY,
        )
        style.map(
            "Viewer.TNotebook.Tab",
            background=[("selected", DarkTheme.BG_INPUT)],
            foreground=[("selected", DarkTheme.FG_SECONDARY)],
        )

        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(self.root, style="Viewer.TNotebook")
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame for RALPH-COMPLETE.md
        complete_frame = tk.Frame(notebook, bg=DarkTheme.BG_PRIMARY)
        notebook.add(complete_frame, text="RALPH-COMPLETE.md")

        complete_text = tk.Text(
            complete_frame,
            wrap="word",
            font=("Consolas", 11),
            bg=DarkTheme.BG_PRIMARY,
            fg=DarkTheme.FG_PRIMARY,
            insertbackground="white",
            padx=15,
            pady=15,
            relief="flat",
        )
        complete_text.pack(fill="both", expand=True, side="left")

        complete_scroll = tk.Scrollbar(complete_frame, command=complete_text.yview)
        complete_scroll.pack(fill="y", side="right")
        complete_text.config(yscrollcommand=complete_scroll.set)

        complete_content = self._read_file(complete_path)
        complete_text.insert("1.0", complete_content)
        complete_text.config(state="disabled")

        # Frame for RALPH-PROGRESS.md
        progress_frame = tk.Frame(notebook, bg=DarkTheme.BG_PRIMARY)
        notebook.add(progress_frame, text="RALPH-PROGRESS.md")

        progress_text = tk.Text(
            progress_frame,
            wrap="word",
            font=("Consolas", 11),
            bg=DarkTheme.BG_PRIMARY,
            fg=DarkTheme.FG_PRIMARY,
            insertbackground="white",
            padx=15,
            pady=15,
            relief="flat",
        )
        progress_text.pack(fill="both", expand=True, side="left")

        progress_scroll = tk.Scrollbar(progress_frame, command=progress_text.yview)
        progress_scroll.pack(fill="y", side="right")
        progress_text.config(yscrollcommand=progress_scroll.set)

        progress_content = self._read_file(progress_path)
        progress_text.insert("1.0", progress_content)
        progress_text.config(state="disabled")

        # Close button
        close_btn = tk.Button(
            self.root,
            text="Close",
            command=self.root.destroy,
            font=("Consolas", 11),
            bg=DarkTheme.ACCENT,
            fg="white",
            activebackground=DarkTheme.ACCENT_HOVER,
            activeforeground="white",
            padx=30,
            pady=8,
            relief="flat",
            cursor="hand2",
        )
        close_btn.pack(pady=10)

    def _center_window(self):
        """Center the window on the same monitor as the parent window."""
        center_window_on_parent(self.root, self._parent)


class OpencodeJsonEditor:
    """Simple editor popup for opencode.json file with permission snippet buttons."""

    _instance: Optional["OpencodeJsonEditor"] = None

    # Permission snippets - predefined configurations for common use cases
    PERMISSION_SNIPPETS = {
        "Ask All": {
            "description": "Safe default - ask for all operations",
            "snippet": {"permission": "ask"},
        },
        "Allow All": {
            "description": "Trust mode - allow all operations without prompting",
            "snippet": {"permission": "allow"},
        },
        "Read-Only": {
            "description": "Allow read/search operations, deny edits and bash",
            "snippet": {
                "permission": {
                    "read": "allow",
                    "list": "allow",
                    "glob": "allow",
                    "grep": "allow",
                    "edit": "deny",
                    "bash": "deny",
                }
            },
        },
        "Bash Allowlist": {
            "description": "Allow common dev commands (git, npm, etc), ask for others",
            "snippet": {
                "permission": {
                    "bash": {
                        "git *": "allow",
                        "npm *": "allow",
                        "pnpm *": "allow",
                        "yarn *": "allow",
                        "ls *": "allow",
                        "cat *": "allow",
                        "*": "ask",
                    }
                }
            },
        },
        "Standard Dev": {
            "description": "Read/search allowed, edit/bash require approval",
            "snippet": {
                "permission": {
                    "read": "allow",
                    "list": "allow",
                    "glob": "allow",
                    "grep": "allow",
                    "edit": "ask",
                    "bash": "ask",
                    "webfetch": "allow",
                    "websearch": "allow",
                }
            },
        },
        "Agent Override": {
            "description": "Add permission override for a specific agent",
            "snippet": None,  # Special handling - prompts for agent name
            "is_agent_scoped": True,
        },
    }

    def __init__(self, script_dir: str, parent: Optional[tk.Tk] = None):
        if OpencodeJsonEditor._instance is not None:
            OpencodeJsonEditor._instance._bring_to_front()
            return
        OpencodeJsonEditor._instance = self
        self.script_dir = script_dir
        self._parent = parent
        self.filepath = os.path.join(script_dir, "opencode.json")
        self.root = tk.Toplevel()
        self.root.title("Edit opencode.json")
        self.root.geometry("700x550")
        self.root.configure(bg=DarkTheme.BG_PRIMARY)
        self.root.minsize(500, 500)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._create_widgets()
        self._center_window()
        self._load_file()
        self.root.lift()
        self.root.focus_force()

    def _bring_to_front(self):
        """Bring existing window to front."""
        self.root.lift()
        self.root.focus_force()

    def _on_close(self):
        """Handle window close."""
        OpencodeJsonEditor._instance = None
        self.root.destroy()

    def _create_widgets(self):
        """Create editor widgets with permission snippet toolbar."""
        # Snippet toolbar frame
        toolbar_frame = tk.Frame(self.root, bg=DarkTheme.BG_SECONDARY)
        toolbar_frame.pack(fill="x", padx=10, pady=(10, 5))

        toolbar_label = tk.Label(
            toolbar_frame,
            text="Insert Permission Preset:",
            bg=DarkTheme.BG_SECONDARY,
            fg=DarkTheme.FG_DIM,
            font=("Segoe UI", 9),
        )
        toolbar_label.pack(side="left", padx=(5, 10))

        # Create snippet buttons
        for name, config in self.PERMISSION_SNIPPETS.items():
            btn = tk.Button(
                toolbar_frame,
                text=name,
                command=lambda n=name: self._insert_snippet(n),
                bg=DarkTheme.BG_TERTIARY,
                fg=DarkTheme.FG_PRIMARY,
                activebackground=DarkTheme.BG_INPUT,
                activeforeground=DarkTheme.FG_SECONDARY,
                relief="flat",
                font=("Segoe UI", 9),
                padx=8,
                pady=3,
                cursor="hand2",
            )
            btn.pack(side="left", padx=2)
            # Add tooltip
            self._create_tooltip(btn, config["description"])

        # Text editor with scrollbar
        text_frame = tk.Frame(self.root, bg=DarkTheme.BG_PRIMARY)
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 11),
            bg=DarkTheme.BG_INPUT,
            fg=DarkTheme.FG_PRIMARY,
            insertbackground=DarkTheme.FG_PRIMARY,
            padx=10,
            pady=10,
            relief="flat",
            undo=True,  # Enable undo support
        )
        self.text_widget.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(text_frame, command=self.text_widget.yview)
        scrollbar.pack(fill="y", side="right")
        self.text_widget.config(yscrollcommand=scrollbar.set)

        # Button frame
        btn_frame = tk.Frame(self.root, bg=DarkTheme.BG_PRIMARY)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        save_btn = tk.Button(
            btn_frame,
            text="Save",
            command=self._save_file,
            bg=DarkTheme.ACCENT,
            fg="#ffffff",
            activebackground=DarkTheme.ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10),
            padx=20,
            pady=5,
            cursor="hand2",
        )
        save_btn.pack(side="right", padx=(10, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self._on_close,
            bg=DarkTheme.BG_TERTIARY,
            fg=DarkTheme.FG_PRIMARY,
            activebackground=DarkTheme.BG_INPUT,
            activeforeground=DarkTheme.FG_PRIMARY,
            relief="flat",
            font=("Segoe UI", 10),
            padx=20,
            pady=5,
            cursor="hand2",
        )
        cancel_btn.pack(side="right")

    def _center_window(self):
        """Center the window on the same monitor as the parent window."""
        center_window_on_parent(self.root, self._parent)

    def _load_file(self):
        """Load opencode.json content into editor."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, encoding="utf-8") as f:
                    content = f.read()
                self.text_widget.insert("1.0", content)
            else:
                self.text_widget.insert("1.0", "{}")
        except Exception as e:
            logger.error(f"Error loading opencode.json: {e}")
            self.text_widget.insert("1.0", f"Error loading file: {e}")

    def _save_file(self):
        """Save editor content to opencode.json."""
        try:
            content = self.text_widget.get("1.0", tk.END).rstrip()
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved: {self.filepath}")
            self._on_close()
        except Exception as e:
            logger.error(f"Error saving opencode.json: {e}")
            messagebox.showerror("Error", f"Error saving file:\n{e}")

    def _prompt_agent_name(self) -> Optional[str]:
        """Prompt user for agent name via a simple dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Agent Name")
        dialog.geometry("300x120")
        dialog.configure(bg=DarkTheme.BG_PRIMARY)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 120) // 2
        dialog.geometry(f"+{x}+{y}")

        result: dict[str, Optional[str]] = {"value": None}

        tk.Label(
            dialog,
            text="Enter agent name (e.g., 'code-reviewer'):",
            bg=DarkTheme.BG_PRIMARY,
            fg=DarkTheme.FG_PRIMARY,
            font=("Segoe UI", 10),
        ).pack(pady=(15, 5))

        entry = tk.Entry(
            dialog,
            bg=DarkTheme.BG_INPUT,
            fg=DarkTheme.FG_PRIMARY,
            insertbackground=DarkTheme.FG_PRIMARY,
            font=("Consolas", 11),
            relief="flat",
        )
        entry.pack(padx=20, pady=5, fill="x")
        entry.focus_set()

        def on_ok():
            result["value"] = entry.get().strip()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=DarkTheme.BG_PRIMARY)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="OK",
            command=on_ok,
            bg=DarkTheme.ACCENT,
            fg="#ffffff",
            relief="flat",
            padx=15,
            cursor="hand2",
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Cancel",
            command=on_cancel,
            bg=DarkTheme.BG_TERTIARY,
            fg=DarkTheme.FG_PRIMARY,
            relief="flat",
            padx=15,
            cursor="hand2",
        ).pack(side="left", padx=5)

        entry.bind("<Return>", lambda e: on_ok())
        entry.bind("<Escape>", lambda e: on_cancel())

        dialog.wait_window()
        return result["value"] if result["value"] else None

    def _insert_snippet(self, snippet_name: str):
        """Insert a permission snippet into the JSON editor.

        Handles merging with existing JSON or replacing the permission key.
        Also handles agent-scoped permissions for nested agent.<name>.permission paths.
        """
        if snippet_name not in self.PERMISSION_SNIPPETS:
            return

        config = self.PERMISSION_SNIPPETS[snippet_name]

        # Handle agent-scoped permissions
        if config.get("is_agent_scoped"):
            agent_name = self._prompt_agent_name()
            if not agent_name:
                return
            # Create agent-scoped snippet
            snippet_data = {
                "agent": {
                    agent_name: {
                        "permission": {
                            "read": "allow",
                            "edit": "ask",
                            "bash": "ask",
                        }
                    }
                }
            }
        else:
            snippet_data = config["snippet"]

        try:
            # Get current content
            current_content = self.text_widget.get("1.0", tk.END).strip()

            # Parse current JSON
            if current_content:
                try:
                    current_json = json.loads(current_content)
                except json.JSONDecodeError:
                    # Invalid JSON - ask user if they want to replace
                    if not messagebox.askyesno(
                        "Invalid JSON",
                        "Current content is not valid JSON. Replace entirely with snippet?",
                    ):
                        return
                    current_json = {}
            else:
                current_json = {}

            # Handle agent-scoped snippets differently
            if "agent" in snippet_data:
                agent_name = list(snippet_data["agent"].keys())[0]
                agent_permission = snippet_data["agent"][agent_name]["permission"]

                # Initialize agent key if needed
                if "agent" not in current_json:
                    current_json["agent"] = {}

                # Check if this specific agent already has config
                if agent_name in current_json["agent"]:
                    response = messagebox.askyesnocancel(
                        "Agent Exists",
                        f'Agent "{agent_name}" already has configuration.\n\n'
                        f"Yes = Replace agent permission\n"
                        f"No = Merge with existing\n"
                        f"Cancel = Abort",
                    )
                    if response is None:  # Cancel
                        return
                    elif response:  # Yes - replace
                        if "permission" not in current_json["agent"][agent_name]:
                            current_json["agent"][agent_name] = {}
                        current_json["agent"][agent_name]["permission"] = agent_permission
                    else:  # No - merge
                        existing = current_json["agent"][agent_name].get("permission", {})
                        if isinstance(existing, dict):
                            existing.update(agent_permission)
                            current_json["agent"][agent_name]["permission"] = existing
                        else:
                            current_json["agent"][agent_name]["permission"] = agent_permission
                else:
                    # New agent, just add it
                    current_json["agent"][agent_name] = snippet_data["agent"][agent_name]

            # Check if permission key exists (for regular snippets)
            elif "permission" in snippet_data:
                if "permission" in current_json:
                    # Ask user: merge or replace?
                    response = messagebox.askyesnocancel(
                        "Permission Exists",
                        f'A "permission" key already exists.\n\n'
                        f"Yes = Replace existing permission\n"
                        f"No = Merge with existing\n"
                        f"Cancel = Abort",
                    )
                    if response is None:  # Cancel
                        return
                    elif response:  # Yes - replace
                        current_json["permission"] = snippet_data["permission"]
                    else:  # No - merge
                        if isinstance(current_json["permission"], dict) and isinstance(
                            snippet_data["permission"], dict
                        ):
                            # Deep merge dictionaries
                            current_json["permission"].update(snippet_data["permission"])
                        else:
                            # Can't merge non-dict, replace instead
                            current_json["permission"] = snippet_data["permission"]
                else:
                    # No existing permission, just add it
                    current_json.update(snippet_data)
            else:
                # Generic update
                current_json.update(snippet_data)

            # Format the JSON with indentation
            new_content = json.dumps(current_json, indent=2)

            # Replace content (with undo support)
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", new_content)

            logger.info(f"Inserted permission snippet: {snippet_name}")

        except Exception as e:
            logger.error(f"Error inserting snippet: {e}")
            messagebox.showerror("Error", f"Failed to insert snippet:\n{e}")

    def _create_tooltip(self, widget, text: str):
        """Create a simple tooltip for a widget."""

        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")

            label = tk.Label(
                tooltip,
                text=text,
                bg=DarkTheme.BG_INPUT,
                fg=DarkTheme.FG_PRIMARY,
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
                padx=5,
                pady=3,
            )
            label.pack()

            # Store tooltip reference to destroy later
            widget._tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, "_tooltip") and widget._tooltip:
                widget._tooltip.destroy()
                widget._tooltip = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)


class RalphLoopRunner:
    """Runs the opencode loop logic directly in Python.

    Implements the iteration loop: invoke opencode, check for terminal states,
    and handle checkpoints until completion or blocking condition.
    """

    # File constants for checkpoint and progress tracking
    PIN_SPEC = "RALPH-DESIGN.md"
    PIN_LOOKUP = "RALPH-SPECS.md"
    PLAN_FILE = "RALPH-PLAN.md"
    PROGRESS_FILE = "RALPH-PROGRESS.md"
    DONE_FILE = "RALPH-COMPLETE.md"
    BLOCKED_FILE = "RALPH-BLOCKED.md"
    STOP_FILE = "RALPH-STOP"
    CHECKPOINT_FILE = "RALPH-CHECKPOINT.md"

    def __init__(
        self,
        folder: str,
        model: str,
        max_attempts: int = 40,
        sleep_seconds: int = 2,
        log_level: str = "INFO",
        variant: Optional[str] = None,
    ):
        """Initialize the loop runner.

        Args:
            folder: Target folder to run opencode in
            model: LLM model to use (e.g., "anthropic/claude-opus-4-5")
            max_attempts: Maximum number of loop iterations
            sleep_seconds: Delay between attempts
            log_level: Log level for opencode
            variant: Model variant (e.g., "high", "max", "minimal") or None to omit
        """
        self.folder = folder
        self.model = model
        self.max_attempts = max_attempts
        self.sleep_seconds = sleep_seconds
        self.log_level = log_level
        self.variant = variant

        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._current_attempt = 0
        self._status = "pending"  # pending, running, completed, blocked, stopped, failed, paused
        self._error_message: Optional[str] = None

        self._current_process: Optional[subprocess.Popen] = None

        # Waiting state support
        self._is_waiting = False
        self._waiting_since: Optional[datetime] = None
        self._waiting_duration: int = 0  # Total wait time in seconds
        self._waiting_reason: str = ""  # "checkpoint", "backoff", "cooldown"

        # Pause/resume support
        self._pause_requested = False  # Queue pause for next loop boundary
        self._is_paused = False  # Currently paused

        # Missing checkpoint pause support
        self._missing_checkpoint_pause = False  # Paused due to missing checkpoint
        self._user_continue_decision: Optional[bool] = None  # True=continue, False=stop

    @property
    def status(self) -> str:
        """Get current runner status."""
        return self._status

    @property
    def current_attempt(self) -> int:
        """Get current attempt number."""
        return self._current_attempt

    @property
    def is_running(self) -> bool:
        """Check if the runner is still active."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_waiting(self) -> bool:
        """Check if runner is currently in a waiting/sleep state."""
        return self._is_waiting

    @property
    def waiting_reason(self) -> str:
        """Get the reason for waiting."""
        return self._waiting_reason

    @property
    def waiting_seconds_remaining(self) -> int:
        """Get seconds remaining in current wait period."""
        if not self._is_waiting or self._waiting_since is None:
            return 0
        elapsed = (datetime.now() - self._waiting_since).total_seconds()
        remaining = max(0, self._waiting_duration - int(elapsed))
        return remaining

    @property
    def is_paused(self) -> bool:
        """Check if runner is currently paused."""
        return self._is_paused

    @property
    def pause_pending(self) -> bool:
        """Check if a pause is queued for next loop boundary."""
        return self._pause_requested

    @property
    def is_missing_checkpoint_pause(self) -> bool:
        """Check if paused due to missing checkpoint."""
        return self._missing_checkpoint_pause

    def continue_after_missing_checkpoint(self):
        """User chose to continue after missing checkpoint."""
        self._user_continue_decision = True
        self._missing_checkpoint_pause = False

    def stop_after_missing_checkpoint(self):
        """User chose to stop after missing checkpoint."""
        self._user_continue_decision = False
        self._missing_checkpoint_pause = False

    def pause(self):
        """Queue a pause for the next loop boundary."""
        if not self._is_paused:
            self._pause_requested = True

    def resume(self):
        """Resume from paused state."""
        self._is_paused = False
        self._pause_requested = False

    def force_kill(self):
        """Immediately terminate the running subprocess."""
        self._stop_requested = True
        if self._current_process:
            pid = self._current_process.pid
            try:
                # On Windows, use taskkill to terminate entire process tree
                if platform.system() == "Windows":
                    subprocess.run(
                        ["taskkill", "/T", "/F", "/PID", str(pid)],
                        capture_output=True,
                    )
                else:
                    self._current_process.terminate()
                self._current_process.wait(timeout=2)
            except Exception:
                try:
                    self._current_process.kill()
                except Exception:
                    pass
            self._current_process = None
        self._is_waiting = False
        self._is_paused = False
        self._status = "stopped"

    def _set_waiting(self, reason: str, duration: int):
        """Enter waiting state with reason and duration."""
        self._is_waiting = True
        self._waiting_since = datetime.now()
        self._waiting_duration = duration
        self._waiting_reason = reason

    def _clear_waiting(self):
        """Exit waiting state."""
        self._is_waiting = False
        self._waiting_since = None
        self._waiting_duration = 0
        self._waiting_reason = ""

    def _wait_with_state(self, reason: str, duration: int):
        """Sleep while tracking waiting state (can be interrupted by stop)."""
        self._set_waiting(reason, duration)
        try:
            # Sleep in small increments to allow stop/pause interruption
            elapsed = 0
            while elapsed < duration and not self._stop_requested:
                time.sleep(0.5)
                elapsed += 0.5
        finally:
            self._clear_waiting()

    def start(self):
        """Start the loop in a background thread."""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Runner is already running")

        self._stop_requested = False
        self._status = "running"
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Request the loop to stop gracefully."""
        self._stop_requested = True

    def _file_path(self, filename: str) -> str:
        """Get full path to a file in the target folder."""
        return os.path.join(self.folder, filename)

    def _file_exists(self, filename: str) -> bool:
        """Check if a file exists in the target folder."""
        return os.path.exists(self._file_path(filename))

    def _remove_file(self, filename: str):
        """Remove a file from the target folder if it exists."""
        path = self._file_path(filename)
        if os.path.exists(path):
            os.remove(path)

    def _read_template_file(self, filename: str) -> str:
        """Read a template file from the script directory.

        Args:
            filename: Name of the template file (e.g., 'RALPH-PLAN.md')

        Returns:
            File contents.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, filename)
        with open(template_path, encoding="utf-8") as f:
            return f.read()

    def _scaffold_plan_file(self):
        """Create default RALPH-PLAN.md if it doesn't exist."""
        if not self._file_exists(self.PLAN_FILE):
            content = self._read_template_file(self.PLAN_FILE)
            with open(self._file_path(self.PLAN_FILE), "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Created scaffold: {self.PLAN_FILE}")

    def _scaffold_progress_file(self):
        """Create default RALPH-PROGRESS.md if it doesn't exist."""
        if not self._file_exists(self.PROGRESS_FILE):
            content = self._read_template_file(self.PROGRESS_FILE)
            with open(self._file_path(self.PROGRESS_FILE), "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Created scaffold: {self.PROGRESS_FILE}")

    def _build_prompt(self) -> str:
        """Build the prompt for opencode by reading from RALPH-PROMPT.md."""
        return self._read_template_file("RALPH-PROMPT.md").strip()

    def _invoke_opencode(self) -> bool:
        """Invoke opencode run with the prompt.

        Returns:
            True if opencode completed successfully, False on error.
        """
        prompt = self._build_prompt()

        # Build command
        is_windows = platform.system() == "Windows"

        # Build variant flag if specified
        variant_flag = ""
        variant_args = []
        if self.variant and self.variant != "None":
            variant_flag = f" --variant {self.variant}"
            variant_args = ["--variant", self.variant]

        if is_windows:
            # Use CREATE_NEW_CONSOLE to get visible window that's killable
            # Escape newlines for Windows cmd - replace with space to keep as single line
            # This preserves the full prompt content for opencode
            escaped_prompt = prompt.replace("\r\n", " ").replace("\n", " ")
            cmd = [
                "cmd",
                "/c",
                f'opencode --log-level {self.log_level} --model {self.model}{variant_flag} run "{escaped_prompt}"',
            ]
            creationflags = subprocess.CREATE_NEW_CONSOLE
        else:
            cmd = (
                ["opencode", "--log-level", self.log_level, "--model", self.model]
                + variant_args
                + ["run", prompt]
            )
            creationflags = 0

        try:
            logger.info(f"[ralph] invoking opencode (attempt {self._current_attempt})")

            # Use Popen for interruptible execution
            self._current_process = subprocess.Popen(
                cmd,
                cwd=self.folder,
                creationflags=creationflags if is_windows else 0,
            )

            # Poll process while checking stop/pause flags
            while self._current_process.poll() is None:
                if self._stop_requested:
                    logger.info("[ralph] stop requested during opencode execution")
                    self._current_process.terminate()
                    try:
                        self._current_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._current_process.kill()
                    return False

                # Check for pause at process boundary (after process ends naturally)
                # Don't interrupt mid-execution for pause
                time.sleep(0.2)

            returncode = self._current_process.returncode
            self._current_process = None

            if returncode != 0:
                logger.warning(f"[ralph] opencode returned non-zero: {returncode}")
                return False

            return True

        except FileNotFoundError:
            logger.error("[ralph] opencode command not found")
            self._error_message = "opencode command not found"
            self._current_process = None
            return False
        except Exception as e:
            logger.error(f"[ralph] opencode failed: {e}")
            self._current_process = None
            return False

    def _run_loop(self):
        """Main loop logic (runs in background thread)."""
        try:
            # Validate required file exists
            if not self._file_exists(self.PIN_SPEC):
                self._status = "failed"
                self._error_message = f"Missing {self.PIN_SPEC}"
                logger.error(f"[ralph] missing {self.PIN_SPEC}")
                return

            # Scaffold plan and progress files if missing
            self._scaffold_plan_file()
            self._scaffold_progress_file()

            # Remove terminal state files from previous runs
            self._remove_file(self.DONE_FILE)
            self._remove_file(self.BLOCKED_FILE)

            logger.info(f"[ralph] start (model={self.model})")

            for attempt in range(1, self.max_attempts + 1):
                self._current_attempt = attempt
                logger.info(f"[ralph] attempt {attempt}/{self.max_attempts}")

                # Check for pause request at loop boundary
                if self._pause_requested:
                    self._is_paused = True
                    self._pause_requested = False
                    self._status = "paused"
                    logger.info("[ralph] paused at loop boundary")
                    while self._is_paused and not self._stop_requested:
                        time.sleep(0.5)
                    if self._stop_requested:
                        logger.info("[ralph] STOP requested while paused")
                        self._status = "stopped"
                        return
                    self._status = "running"
                    logger.info("[ralph] resumed")

                # Check stop conditions
                if self._stop_requested or self._file_exists(self.STOP_FILE):
                    logger.info("[ralph] STOP requested")
                    self._status = "stopped"
                    return

                if self._file_exists(self.DONE_FILE):
                    # If checkpoint was also created alongside done, remove it
                    if self._file_exists(self.CHECKPOINT_FILE):
                        logger.info("[ralph] removing checkpoint (done file takes precedence)")
                        self._remove_file(self.CHECKPOINT_FILE)
                    logger.info("[ralph] done")
                    self._status = "completed"
                    return

                if self._file_exists(self.BLOCKED_FILE):
                    # If checkpoint was also created alongside blocked, remove it
                    if self._file_exists(self.CHECKPOINT_FILE):
                        logger.info("[ralph] removing checkpoint (blocked file takes precedence)")
                        self._remove_file(self.CHECKPOINT_FILE)
                    logger.info(f"[ralph] blocked (see {self.BLOCKED_FILE})")
                    self._status = "blocked"
                    return

                # Checkpoint = one item done, consume and continue with fresh context
                if self._file_exists(self.CHECKPOINT_FILE):
                    logger.info("[ralph] checkpoint - one item done, restarting fresh")
                    self._remove_file(self.CHECKPOINT_FILE)
                    self._wait_with_state("checkpoint", self.sleep_seconds)
                    continue

                # Invoke opencode
                if not self._invoke_opencode():
                    logger.warning("[ralph] opencode failed; backing off")
                    self._wait_with_state("backoff", self.sleep_seconds)
                    continue

                # Check terminal states after opencode
                if self._file_exists(self.DONE_FILE):
                    # If checkpoint was also created alongside done, remove it
                    if self._file_exists(self.CHECKPOINT_FILE):
                        logger.info("[ralph] removing checkpoint (done file takes precedence)")
                        self._remove_file(self.CHECKPOINT_FILE)
                    logger.info("[ralph] done")
                    self._status = "completed"
                    return

                if self._file_exists(self.BLOCKED_FILE):
                    # If checkpoint was also created alongside blocked, remove it
                    if self._file_exists(self.CHECKPOINT_FILE):
                        logger.info("[ralph] removing checkpoint (blocked file takes precedence)")
                        self._remove_file(self.CHECKPOINT_FILE)
                    logger.info(f"[ralph] blocked (see {self.BLOCKED_FILE})")
                    self._status = "blocked"
                    return

                # Check for checkpoint - if missing, pause and ask user
                if self._file_exists(self.CHECKPOINT_FILE):
                    logger.info("[ralph] checkpoint found after opencode - continuing")
                    self._remove_file(self.CHECKPOINT_FILE)
                    self._wait_with_state("checkpoint", self.sleep_seconds)
                    continue
                else:
                    # No checkpoint created - pause and wait for user decision
                    logger.warning("[ralph] no checkpoint created - pausing for user decision")
                    self._missing_checkpoint_pause = True
                    self._status = "missing_checkpoint"
                    self._user_continue_decision = None

                    # Wait for user decision
                    while self._missing_checkpoint_pause and not self._stop_requested:
                        time.sleep(0.5)

                    if self._stop_requested:
                        logger.info("[ralph] STOP requested while waiting for checkpoint decision")
                        self._status = "stopped"
                        return

                    if self._user_continue_decision is False:
                        logger.info("[ralph] user chose to stop after missing checkpoint")
                        self._status = "stopped"
                        return

                    # User chose to continue
                    logger.info("[ralph] user chose to continue after missing checkpoint")
                    self._status = "running"
                    self._wait_with_state("cooldown", self.sleep_seconds)

            # Max attempts reached without completion
            logger.warning("[ralph] max attempts without completion")
            self._status = "failed"
            self._error_message = "Max attempts reached"

        except Exception as e:
            logger.error(f"[ralph] loop error: {e}")
            self._status = "failed"
            self._error_message = str(e)


class RunningTask:
    """Represents a running Ralph task."""

    def __init__(
        self,
        folder: str,
        backup_guid: str,
        runner: Optional[RalphLoopRunner] = None,
    ):
        self.folder: str = folder
        self.backup_guid: str = backup_guid
        self.runner: Optional[RalphLoopRunner] = runner
        self.start_time: datetime = datetime.now()
        self.status: str = "running"
        self.opencode_json_copied: bool = False

    def get_elapsed_time(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = datetime.now() - self.start_time
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_current_attempt(self) -> int:
        """Get current attempt number from the runner."""
        if self.runner:
            return self.runner.current_attempt
        return 0

    def is_complete(self) -> bool:
        """Check if the task has completed by looking for RALPH-COMPLETE.md."""
        complete_file = os.path.join(self.folder, "RALPH-COMPLETE.md")
        return os.path.exists(complete_file)

    def is_runner_active(self) -> bool:
        """Check if the runner is still active."""
        if self.runner:
            return self.runner.is_running
        return False

    def get_runner_status(self) -> str:
        """Get the runner's status (pending, running, completed, blocked, stopped, failed)."""
        if self.runner:
            return self.runner.status
        return "unknown"

    def is_blocked(self) -> bool:
        """Check if the task is blocked by looking for RALPH-BLOCKED.md."""
        blocked_file = os.path.join(self.folder, "RALPH-BLOCKED.md")
        return os.path.exists(blocked_file)

    def get_runner_error(self) -> Optional[str]:
        """Get the runner's error message if any."""
        if self.runner and hasattr(self.runner, "_error_message"):
            return self.runner._error_message
        return None

    def is_waiting(self) -> bool:
        """Check if the runner is in a waiting/sleep state."""
        if self.runner:
            return self.runner.is_waiting
        return False

    def get_waiting_info(self) -> tuple:
        """Get waiting state info: (is_waiting, reason, seconds_remaining)."""
        if self.runner:
            return (
                self.runner.is_waiting,
                self.runner.waiting_reason,
                self.runner.waiting_seconds_remaining,
            )
        return (False, "", 0)

    def is_paused(self) -> bool:
        """Check if the runner is paused."""
        if self.runner:
            return self.runner.is_paused
        return False

    def is_pause_pending(self) -> bool:
        """Check if a pause is queued for next loop boundary."""
        if self.runner:
            return self.runner.pause_pending
        return False

    def pause(self):
        """Queue a pause for next loop boundary."""
        if self.runner:
            self.runner.pause()

    def resume(self):
        """Resume from paused state."""
        if self.runner:
            self.runner.resume()

    def force_kill(self):
        """Immediately terminate the runner's subprocess."""
        if self.runner:
            self.runner.force_kill()

    def is_missing_checkpoint_pause(self) -> bool:
        """Check if paused due to missing checkpoint."""
        if self.runner:
            return self.runner.is_missing_checkpoint_pause
        return False

    def continue_after_missing_checkpoint(self):
        """User chose to continue after missing checkpoint."""
        if self.runner:
            self.runner.continue_after_missing_checkpoint()

    def stop_after_missing_checkpoint(self):
        """User chose to stop after missing checkpoint."""
        if self.runner:
            self.runner.stop_after_missing_checkpoint()


class RalphGUI:
    """Main GUI application for Ralph project setup."""

    def __init__(self, root):
        """Initialize the GUI components."""
        self.root = root
        self.root.title("Ralph Codes 4 OpenCode")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)

        # Get the directory where this script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create backup directory
        self.backup_dir = os.path.join(self.script_dir, "backup")
        os.makedirs(self.backup_dir, exist_ok=True)

        # Create GIF cache directory
        self.gif_cache_dir = os.path.join(self.script_dir, "gif_cache")
        os.makedirs(self.gif_cache_dir, exist_ok=True)

        # GIF animation state
        self._animation_id = None
        self._current_frame = 0
        self._gif_frames = []
        self._frame_delays = []
        self.ralph_photo = None  # Holds reference to current image to prevent garbage collection

        # Selected folder path
        self.selected_folder = tk.StringVar()

        # Running tasks list
        self.running_tasks = []
        self.task_update_id = None

        # Track checkpoint dialogs to prevent duplicates (task_id -> dialog)
        self._checkpoint_dialogs: dict = {}

        # Context menu task reference (to survive listbox refresh race condition)
        self._context_menu_task: Optional[RunningTask] = None

        # Recent folders tracking
        self.recent_folders = []
        self.recent_folders_file = os.path.join(self.script_dir, "recent_folders.json")

        # Load recent folders from file
        self._load_recent_folders()

        # Model selection
        self.selected_model = tk.StringVar()
        self.available_models = []
        self.recently_used_models = []
        self.recent_models_file = os.path.join(self.script_dir, "recent_models.json")

        # Load recently used models from file
        self._load_recent_models()

        # Model variant selection
        self.selected_variant = tk.StringVar()
        self.variant_options = ["None", "minimal", "high", "max"]
        self.recent_variant_file = os.path.join(self.script_dir, "recent_variant.json")

        # Load recently used variant from file
        self._load_recent_variant()

        # opencode.json copy checkbox state
        self.copy_opencode_json = tk.BooleanVar(value=True)  # Default checked

        # Apply dark theme
        self._apply_dark_theme()

        self._create_widgets()
        self._configure_grid()

        # Load Ralph image
        self._load_ralph_image()

        # Load available models in background
        self._load_models_async()

        # Start task status update loop
        self._update_task_status()

        # Start periodic GIF/quote refresh (every 30 seconds)
        self._start_periodic_refresh()

        # Load template from file on startup
        self._load_template_from_file()

    def _apply_dark_theme(self):
        """Apply dark theme to the application."""
        self.root.configure(bg=DarkTheme.BG_PRIMARY)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Configure ttk styles for dark theme
        style.configure("Dark.TFrame", background=DarkTheme.BG_PRIMARY)
        style.configure("DarkSecondary.TFrame", background=DarkTheme.BG_SECONDARY)

        style.configure(
            "Dark.TLabel",
            background=DarkTheme.BG_PRIMARY,
            foreground=DarkTheme.FG_PRIMARY,
            font=("Segoe UI", 10),
        )

        style.configure(
            "DarkTitle.TLabel",
            background=DarkTheme.BG_PRIMARY,
            foreground=DarkTheme.FG_SECONDARY,
            font=("Segoe UI", 14, "bold"),
        )

        style.configure(
            "DarkStatus.TLabel",
            background=DarkTheme.BG_PRIMARY,
            foreground=DarkTheme.FG_DIM,
            font=("Segoe UI", 9),
        )

        style.configure(
            "Dark.TEntry",
            fieldbackground=DarkTheme.BG_INPUT,
            foreground=DarkTheme.FG_PRIMARY,
            insertcolor=DarkTheme.FG_PRIMARY,
        )

        style.configure(
            "Dark.TButton",
            background=DarkTheme.ACCENT,
            foreground="#ffffff",
            font=("Segoe UI", 10),
            padding=(10, 5),
        )

        style.map(
            "Dark.TButton",
            background=[("active", DarkTheme.ACCENT_HOVER)],
            foreground=[("active", "#ffffff")],
        )

        style.configure("DarkLabelframe.TLabelframe", background=DarkTheme.BG_SECONDARY)

        style.configure(
            "DarkLabelframe.TLabelframe.Label",
            background=DarkTheme.BG_SECONDARY,
            foreground=DarkTheme.FG_SECONDARY,
            font=("Segoe UI", 10, "bold"),
        )

        # Style for terminal notebook
        style.configure(
            "TNotebook",
            background=DarkTheme.BG_SECONDARY,
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=DarkTheme.BG_TERTIARY,
            foreground=DarkTheme.FG_PRIMARY,
            padding=[10, 5],
            font=("Consolas", 9),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", DarkTheme.BG_INPUT)],
            foreground=[("selected", DarkTheme.FG_SECONDARY)],
        )

        # Style for dark combobox
        style.configure(
            "Dark.TCombobox",
            fieldbackground=DarkTheme.BG_INPUT,
            background=DarkTheme.BG_INPUT,
            foreground=DarkTheme.FG_PRIMARY,
            arrowcolor=DarkTheme.FG_PRIMARY,
            selectbackground=DarkTheme.ACCENT,
            selectforeground="#ffffff",
            insertcolor=DarkTheme.FG_PRIMARY,
            bordercolor=DarkTheme.BORDER,
            lightcolor=DarkTheme.BG_INPUT,
            darkcolor=DarkTheme.BG_INPUT,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[
                ("readonly", DarkTheme.BG_INPUT),
                ("disabled", DarkTheme.BG_SECONDARY),
                ("!disabled", DarkTheme.BG_INPUT),
            ],
            background=[
                ("active", DarkTheme.ACCENT_HOVER),
                ("pressed", DarkTheme.ACCENT),
                ("!disabled", DarkTheme.BG_INPUT),
            ],
            foreground=[
                ("readonly", DarkTheme.FG_PRIMARY),
                ("disabled", DarkTheme.FG_DIM),
                ("!disabled", DarkTheme.FG_PRIMARY),
            ],
            selectbackground=[("readonly", DarkTheme.ACCENT)],
            selectforeground=[("readonly", "#ffffff")],
            arrowcolor=[
                ("disabled", DarkTheme.FG_DIM),
                ("!disabled", DarkTheme.FG_PRIMARY),
            ],
        )

        # Style for dark checkbutton
        style.configure(
            "Dark.TCheckbutton",
            background=DarkTheme.BG_PRIMARY,
            foreground=DarkTheme.FG_PRIMARY,
            font=("Segoe UI", 10),
        )
        style.map(
            "Dark.TCheckbutton",
            background=[("active", DarkTheme.BG_PRIMARY)],
            foreground=[("active", DarkTheme.FG_SECONDARY)],
        )

    def _load_recent_folders(self):
        """Load recent folders from file."""
        try:
            if os.path.exists(self.recent_folders_file):
                with open(self.recent_folders_file, encoding="utf-8") as f:
                    self.recent_folders = json.load(f)
                # Filter out folders that no longer exist
                self.recent_folders = [f for f in self.recent_folders if os.path.isdir(f)]
        except Exception:
            self.recent_folders = []

    def _save_recent_folders(self):
        """Save recent folders to file."""
        try:
            with open(self.recent_folders_file, "w", encoding="utf-8") as f:
                json.dump(self.recent_folders, f)
        except Exception:
            pass

    def _add_to_recent_folders(self, folder):
        """Add a folder to the recent folders list."""
        if folder in self.recent_folders:
            self.recent_folders.remove(folder)
        self.recent_folders.insert(0, folder)
        # Keep only the last 5 recent folders
        self.recent_folders = self.recent_folders[:5]
        self._save_recent_folders()
        # Update the dropdown
        self._update_folder_dropdown()

    def _update_folder_dropdown(self):
        """Update the folder dropdown with recent folders."""
        if hasattr(self, "folder_combo"):
            self.folder_combo["values"] = self.recent_folders

    def _load_recent_models(self):
        """Load recently used models from file."""
        try:
            if os.path.exists(self.recent_models_file):
                with open(self.recent_models_file, encoding="utf-8") as f:
                    self.recently_used_models = json.load(f)
        except Exception:
            self.recently_used_models = []

    def _save_recent_models(self):
        """Save recently used models to file."""
        try:
            with open(self.recent_models_file, "w", encoding="utf-8") as f:
                json.dump(self.recently_used_models, f)
        except Exception:
            pass

    def _add_to_recent_models(self, model):
        """Add a model to the recently used list."""
        if model in self.recently_used_models:
            self.recently_used_models.remove(model)
        self.recently_used_models.insert(0, model)
        # Keep only the last 10 recently used models
        self.recently_used_models = self.recently_used_models[:10]
        self._save_recent_models()
        # Update the dropdown order
        self._update_model_dropdown()

    def _get_sorted_models(self):
        """Get models sorted by: recently used first, then alphabetically."""
        if not self.available_models:
            return []

        # Separate recently used from others
        recent = [m for m in self.recently_used_models if m in self.available_models]
        others = [m for m in self.available_models if m not in self.recently_used_models]

        # Sort others alphabetically
        others.sort()

        return recent + others

    def _load_recent_variant(self):
        """Load recently used variant from file."""
        try:
            if os.path.exists(self.recent_variant_file):
                with open(self.recent_variant_file, encoding="utf-8") as f:
                    data = json.load(f)
                    variant = data.get("variant", "None")
                    if variant in self.variant_options:
                        self.selected_variant.set(variant)
                    else:
                        self.selected_variant.set("None")
            else:
                self.selected_variant.set("None")
        except Exception:
            self.selected_variant.set("None")

    def _save_recent_variant(self):
        """Save recently used variant to file."""
        try:
            with open(self.recent_variant_file, "w", encoding="utf-8") as f:
                json.dump({"variant": self.selected_variant.get()}, f)
        except Exception:
            pass

    def _on_variant_selected(self, event=None):
        """Handle variant selection change."""
        self._save_recent_variant()

    def _load_models_async(self):
        """Load available models from opencode models in a background thread."""

        def load_models():
            try:
                # On Windows, we need shell=True to find .cmd files in PATH
                # On other platforms, shell=False works fine
                is_windows = platform.system() == "Windows"
                result = subprocess.run(
                    "opencode models" if is_windows else ["opencode", "models"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=is_windows,
                )
                if result.returncode == 0:
                    # Parse the output - each line is a model name
                    models = [
                        line.strip() for line in result.stdout.strip().split("\n") if line.strip()
                    ]
                    self.available_models = models
                    # Update the dropdown in the main thread
                    self.root.after(0, self._update_model_dropdown)
            except subprocess.TimeoutExpired:
                pass
            except FileNotFoundError:
                # opencode command not found
                pass
            except Exception:
                pass

        thread = threading.Thread(target=load_models, daemon=True)
        thread.start()

    def _update_model_dropdown(self):
        """Update the model dropdown with sorted models."""
        sorted_models = self._get_sorted_models()
        if hasattr(self, "model_combo"):
            self.model_combo["values"] = sorted_models
            current_value = self.selected_model.get()
            # Select the first model if no valid model is selected
            # (i.e., if current value is empty, the placeholder, or not in the list)
            if sorted_models and (
                not current_value
                or current_value == "Loading models..."
                or current_value not in sorted_models
            ):
                # Select the first model (most recently used or first alphabetically)
                self.selected_model.set(sorted_models[0])

    def _download_gif(self, url: str, filepath: str) -> bool:
        """Download a GIF from URL and save to filepath.

        Args:
            url: The URL to download the GIF from.
            filepath: The local path to save the GIF to.

        Returns:
            True on success, False on failure.
        """
        try:
            logger.info(f"Downloading GIF from {url}")
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                with open(filepath, "wb") as f:
                    f.write(response.read())
            logger.info(f"Downloaded GIF to {filepath}")
            return True
        except Exception as e:
            logger.warning(f"Failed to download GIF from {url}: {e}")
            return False

    def _ensure_gif_cached(self, index: int) -> Optional[str]:
        """Ensure a GIF is cached locally, downloading if necessary.

        Args:
            index: Index into RALPH_GIF_URLS list.

        Returns:
            Filepath to the cached GIF, or None if unavailable.
        """
        if index < 0 or index >= len(RALPH_GIF_URLS):
            return None

        filename = f"ralph_{index}.gif"
        filepath = os.path.join(self.gif_cache_dir, filename)

        # Return existing cached file
        if os.path.exists(filepath):
            return filepath

        # Download and cache
        url = RALPH_GIF_URLS[index]
        if self._download_gif(url, filepath):
            return filepath

        return None

    def _stop_animation(self):
        """Stop any running GIF animation."""
        if self._animation_id is not None:
            self.root.after_cancel(self._animation_id)
            self._animation_id = None
        self._current_frame = 0
        self._gif_frames = []
        self._frame_delays = []

    def _animate_gif(self):
        """Cycle through GIF frames for animation."""
        if not self._gif_frames:
            return

        # Display current frame
        self.image_label.configure(image=self._gif_frames[self._current_frame])

        # Move to next frame
        self._current_frame = (self._current_frame + 1) % len(self._gif_frames)

        # Get delay for current frame (default 100ms if not specified)
        delay = self._frame_delays[self._current_frame] if self._frame_delays else 100
        delay = max(delay, 20)  # Minimum 20ms delay

        # Schedule next frame
        self._animation_id = self.root.after(delay, self._animate_gif)

    def _load_ralph_image(self):
        """Load and display a random animated Ralph Wiggum GIF."""
        # Stop any existing animation
        self._stop_animation()

        def resize_keep_aspect(img, max_height=200):
            """Resize image to fit max_height while preserving aspect ratio."""
            from PIL import Image

            original_width, original_height = img.size
            if original_height <= 0:
                return img

            aspect_ratio = original_width / original_height
            new_height = max_height
            new_width = int(new_height * aspect_ratio)

            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        def load_fallback_image():
            """Load the fallback static image (ralph.jpg) or text placeholder."""
            ralph_jpg_path = os.path.join(self.script_dir, "ralph.jpg")
            try:
                from PIL import Image, ImageTk

                if os.path.exists(ralph_jpg_path):
                    image = Image.open(ralph_jpg_path)
                    image = resize_keep_aspect(image, max_height=200)
                    self.ralph_photo = ImageTk.PhotoImage(image)
                    self.image_label.configure(image=self.ralph_photo)
                else:
                    # No ralph.jpg available, use text placeholder
                    self.image_label.configure(
                        text="Ralph\nWiggum",
                        font=("Segoe UI", 12, "bold"),
                        foreground=DarkTheme.FG_SECONDARY,
                    )
            except (ImportError, Exception):
                # PIL not available or error, use text placeholder
                self.image_label.configure(
                    text="Ralph\nWiggum",
                    font=("Segoe UI", 12, "bold"),
                    foreground=DarkTheme.FG_SECONDARY,
                )

        try:
            from PIL import Image, ImageSequence, ImageTk

            # Select a random GIF index
            gif_index = random.randint(0, len(RALPH_GIF_URLS) - 1)
            gif_path = self._ensure_gif_cached(gif_index)

            if not gif_path:
                logger.warning("No cached GIF available, falling back to static image")
                load_fallback_image()
                return

            # Load the GIF and extract frames
            gif_image = Image.open(gif_path)

            self._gif_frames = []
            self._frame_delays = []

            for frame in ImageSequence.Iterator(gif_image):
                # Resize frame while preserving aspect ratio
                resized_frame = resize_keep_aspect(frame.copy().convert("RGBA"), max_height=200)
                photo = ImageTk.PhotoImage(resized_frame)
                self._gif_frames.append(photo)

                # Get frame duration (in milliseconds)
                delay = frame.info.get("duration", 100)
                self._frame_delays.append(delay)

            if self._gif_frames:
                # Display first frame and start animation
                self.image_label.configure(image=self._gif_frames[0])
                self._current_frame = 0
                self._animation_id = self.root.after(self._frame_delays[0], self._animate_gif)
            else:
                load_fallback_image()

        except ImportError:
            logger.warning("PIL not available, using fallback image")
            load_fallback_image()
        except Exception as e:
            logger.warning(f"Failed to load GIF: {e}")
            load_fallback_image()

    def _refresh_ralph_image(self):
        """Refresh the Ralph image with a new random GIF and quote."""
        self._load_ralph_image()
        self._refresh_quote()

    def _refresh_quote(self):
        """Refresh the Ralph quote with a new random quote."""
        if hasattr(self, "subtitle_label"):
            random_quote = random.choice(RALPH_QUOTES)
            self.subtitle_label.configure(text=random_quote)

    def _start_periodic_refresh(self):
        """Start periodic refresh of GIF and quote every 30 seconds."""
        self._periodic_refresh_id = None
        self._schedule_periodic_refresh()

    def _schedule_periodic_refresh(self):
        """Schedule the next periodic refresh."""
        self._periodic_refresh_id = self.root.after(30000, self._do_periodic_refresh)

    def _do_periodic_refresh(self):
        """Perform periodic refresh of GIF and quote, then reschedule."""
        self._refresh_ralph_image()
        self._schedule_periodic_refresh()

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="15", style="Dark.TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configure main frame grid
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)  # Text area row (shifted by 1 for variant row)
        main_frame.rowconfigure(7, weight=0)  # Tasks row

        # Header section with image and title
        header_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        header_frame.columnconfigure(1, weight=1)

        # Ralph image placeholder
        self.image_label = ttk.Label(header_frame, style="Dark.TLabel")
        self.image_label.grid(row=0, column=0, padx=(0, 15))

        # Title
        title_label = ttk.Label(
            header_frame, text="Ralph Codes 4 OpenCode", style="DarkTitle.TLabel"
        )
        title_label.grid(row=0, column=1, sticky="w")

        # Select a random Ralph quote
        random_quote = random.choice(RALPH_QUOTES)
        self.subtitle_label = ttk.Label(
            header_frame,
            text=random_quote,
            style="DarkStatus.TLabel",
        )
        self.subtitle_label.grid(row=1, column=1, sticky="w")

        # Folder selection section
        folder_label = ttk.Label(main_frame, text="Target Folder:", style="Dark.TLabel")
        folder_label.grid(row=1, column=0, sticky="w", pady=(0, 5))

        folder_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        folder_frame.grid(row=1, column=1, sticky="ew", pady=(0, 5))
        folder_frame.columnconfigure(0, weight=1)

        # Use Combobox for folder selection with recent folders dropdown
        self.folder_combo = ttk.Combobox(
            folder_frame,
            textvariable=self.selected_folder,
            values=self.recent_folders,
            style="Dark.TCombobox",
            font=("Segoe UI", 10),
        )
        self.folder_combo.grid(row=0, column=0, sticky="ew", padx=(5, 5), ipady=3)

        # Browse button
        browse_btn = tk.Button(
            folder_frame,
            text="Browse...",
            command=self._browse_folder,
            bg=DarkTheme.ACCENT,
            fg="#ffffff",
            activebackground=DarkTheme.ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10),
            padx=10,
            pady=5,
            cursor="hand2",
        )
        browse_btn.grid(row=0, column=1)

        # Model selection section
        model_label = ttk.Label(main_frame, text="Model:", style="Dark.TLabel")
        model_label.grid(row=2, column=0, sticky="w", pady=(10, 5))

        model_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        model_frame.grid(row=2, column=1, sticky="ew", pady=(10, 5))
        model_frame.columnconfigure(0, weight=1)

        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.selected_model,
            state="readonly",
            style="Dark.TCombobox",
            font=("Segoe UI", 10),
        )
        self.model_combo.grid(row=0, column=0, sticky="ew", padx=(5, 0), ipady=3)
        self.model_combo.set("Loading models...")

        # Bind selection event to track recently used models
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        # Model variant selection section
        variant_label = ttk.Label(main_frame, text="Variant:", style="Dark.TLabel")
        variant_label.grid(row=3, column=0, sticky="w", pady=(10, 5))

        variant_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        variant_frame.grid(row=3, column=1, sticky="ew", pady=(10, 5))
        variant_frame.columnconfigure(0, weight=1)

        self.variant_combo = ttk.Combobox(
            variant_frame,
            textvariable=self.selected_variant,
            values=self.variant_options,
            state="readonly",
            style="Dark.TCombobox",
            font=("Segoe UI", 10),
        )
        self.variant_combo.grid(row=0, column=0, sticky="ew", padx=(5, 0), ipady=3)

        # Bind selection event to save variant
        self.variant_combo.bind("<<ComboboxSelected>>", self._on_variant_selected)

        # RALPH-DESIGN.md text section with template button
        design_header_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        design_header_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(15, 5))
        design_header_frame.columnconfigure(0, weight=1)

        design_label = ttk.Label(
            design_header_frame, text="RALPH-DESIGN.md Content:", style="Dark.TLabel"
        )
        design_label.grid(row=0, column=0, sticky="w")

        template_btn = tk.Button(
            design_header_frame,
            text="Load Template",
            command=self._load_design_template,
            bg=DarkTheme.BG_TERTIARY,
            fg=DarkTheme.FG_PRIMARY,
            activebackground=DarkTheme.BG_INPUT,
            activeforeground=DarkTheme.FG_PRIMARY,
            relief="flat",
            font=("Segoe UI", 9),
            padx=8,
            pady=2,
            cursor="hand2",
        )
        template_btn.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Custom text widget with dark theme
        text_frame = ttk.Frame(main_frame, style="DarkSecondary.TFrame")
        text_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.design_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            bg=DarkTheme.BG_INPUT,
            fg=DarkTheme.FG_PRIMARY,
            insertbackground=DarkTheme.FG_PRIMARY,
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.design_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for text
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.design_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.design_text.configure(yscrollcommand=scrollbar.set)

        # Status section
        status_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        status_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.status_label = ttk.Label(status_frame, text="Ready", style="DarkStatus.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")

        # Activity indicator
        self.activity_label = ttk.Label(status_frame, text="", style="DarkStatus.TLabel")
        self.activity_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Running tasks section
        tasks_frame = ttk.LabelFrame(
            main_frame,
            text="Running Tasks",
            style="DarkLabelframe.TLabelframe",
            padding="10",
        )
        tasks_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        tasks_frame.columnconfigure(0, weight=1)

        # Tasks listbox with dark theme
        self.tasks_listbox = tk.Listbox(
            tasks_frame,
            height=4,
            bg=DarkTheme.BG_INPUT,
            fg=DarkTheme.FG_PRIMARY,
            selectbackground=DarkTheme.ACCENT,
            selectforeground=DarkTheme.FG_PRIMARY,
            relief="flat",
            font=("Consolas", 9),
            activestyle="none",
        )
        self.tasks_listbox.grid(row=0, column=0, sticky="ew")

        # Progress bar for waiting state
        self.wait_progress = ttk.Progressbar(
            tasks_frame,
            mode="determinate",
            maximum=100,
            length=200,
        )
        # Progress bar is shown/hidden dynamically

        # Context menu for tasks
        self.task_context_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=DarkTheme.BG_SECONDARY,
            fg=DarkTheme.FG_PRIMARY,
            activebackground=DarkTheme.ACCENT,
            activeforeground=DarkTheme.FG_PRIMARY,
        )
        self.task_context_menu.add_command(label="Pause Task", command=self._pause_selected_task)
        self.task_context_menu.add_command(label="Resume Task", command=self._resume_selected_task)
        self.task_context_menu.add_separator()
        self.task_context_menu.add_command(label="Stop Task", command=self._stop_selected_task)
        self.task_context_menu.add_command(
            label="Force Kill", command=self._force_kill_selected_task
        )
        self.task_context_menu.add_separator()
        self.task_context_menu.add_command(label="Open Folder", command=self._open_task_folder)
        self.task_context_menu.add_command(label="View Details", command=self._view_task_details)

        # Bind right-click to show context menu
        self.tasks_listbox.bind("<Button-3>", self._show_task_context_menu)
        # Bind double-click to open folder
        self.tasks_listbox.bind("<Double-Button-1>", lambda e: self._open_task_folder())

        # Empty state message
        self.tasks_listbox.insert(tk.END, "  No tasks running")

        # Buttons section
        button_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        button_frame.grid(row=8, column=0, columnspan=2, sticky="e")

        # Checkbox for opencode.json copy
        self.opencode_checkbox = ttk.Checkbutton(
            button_frame,
            text="Copy opencode.json",
            variable=self.copy_opencode_json,
            style="Dark.TCheckbutton",
        )
        self.opencode_checkbox.grid(row=0, column=0, padx=(0, 10))

        # Edit button for opencode.json
        edit_opencode_btn = tk.Button(
            button_frame,
            text="Edit",
            command=self._open_opencode_editor,
            bg=DarkTheme.BG_TERTIARY,
            fg=DarkTheme.FG_PRIMARY,
            activebackground=DarkTheme.BG_INPUT,
            activeforeground=DarkTheme.FG_PRIMARY,
            relief="flat",
            font=("Segoe UI", 9),
            padx=8,
            pady=5,
            cursor="hand2",
        )
        edit_opencode_btn.grid(row=0, column=1, padx=(0, 15))

        run_btn = tk.Button(
            button_frame,
            text="Run Ralph",
            command=self._run_ralph,
            bg=DarkTheme.ACCENT,
            fg="#ffffff",
            activebackground=DarkTheme.ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 10),
            padx=10,
            pady=5,
            cursor="hand2",
        )
        run_btn.grid(row=0, column=2, padx=(0, 10))

        quit_btn = tk.Button(
            button_frame,
            text="Quit",
            command=self._quit_app,
            bg=DarkTheme.BG_TERTIARY,
            fg=DarkTheme.FG_PRIMARY,
            activebackground=DarkTheme.BG_INPUT,
            activeforeground=DarkTheme.FG_PRIMARY,
            relief="flat",
            font=("Segoe UI", 10),
            padx=10,
            pady=5,
            cursor="hand2",
        )
        quit_btn.grid(row=0, column=3)

    def _configure_grid(self):
        """Configure the root grid weights."""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _browse_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(title="Select Target Folder")
        if folder:
            self.selected_folder.set(folder)
            self._add_to_recent_folders(folder)
            self._update_status(f"Selected folder: {folder}")

    def _on_model_selected(self, event=None):
        """Handle model selection from dropdown."""
        model = self.selected_model.get()
        if model and model != "Loading models...":
            self._add_to_recent_models(model)

    def _open_opencode_editor(self):
        """Open the opencode.json editor popup."""
        OpencodeJsonEditor(self.script_dir, self.root)

    def _load_design_template(self):
        """Load the RALPH-DESIGN.md template from file into the text area."""
        template_path = os.path.join(self.script_dir, "RALPH-DESIGN.md")
        with open(template_path, encoding="utf-8") as f:
            template = f.read()
        self.design_text.delete("1.0", tk.END)
        self.design_text.insert("1.0", template.strip())
        self._update_status("Template loaded", DarkTheme.SUCCESS)

    def _load_template_from_file(self):
        """Load RALPH-DESIGN.md template from disk into the text area on startup."""
        template_path = os.path.join(self.script_dir, "RALPH-DESIGN.md")
        if os.path.exists(template_path):
            try:
                with open(template_path, encoding="utf-8") as f:
                    content = f.read()
                self.design_text.delete("1.0", tk.END)
                self.design_text.insert("1.0", content)
                logger.info(f"Loaded template from: {template_path}")
            except Exception as e:
                logger.error(f"Error loading template: {e}")
                # Fall back to default template
                self._load_design_template()
        else:
            # Fall back to default template if file doesn't exist
            self._load_design_template()

    def _get_selected_task(self) -> Optional[RunningTask]:
        """Get the currently selected task from the listbox."""
        selection = self.tasks_listbox.curselection()
        if not selection or not self.running_tasks:
            return None
        idx = selection[0]
        if idx < len(self.running_tasks):
            return self.running_tasks[idx]
        return None

    def _get_context_menu_task(self) -> Optional[RunningTask]:
        """Get the task that was selected when the context menu was opened.

        Returns None if the task is no longer in the running tasks list.
        This prevents errors when a task completes while the menu is open.
        """
        task = self._context_menu_task
        if task and task in self.running_tasks:
            return task
        return None

    def _show_task_context_menu(self, event):
        """Show context menu for the selected task."""
        # Select the item under cursor
        self.tasks_listbox.selection_clear(0, tk.END)
        idx = self.tasks_listbox.nearest(event.y)
        self.tasks_listbox.selection_set(idx)
        self.tasks_listbox.activate(idx)

        task = self._get_selected_task()
        if not task:
            self._context_menu_task = None
            return

        # Store the task reference for menu commands (prevents race condition
        # with listbox refresh clearing selection before command executes)
        self._context_menu_task = task

        # Enable/disable menu items based on task state
        runner_status = task.get_runner_status()
        is_paused = task.is_paused()
        is_running = runner_status in ("running", "paused") and task.is_runner_active()

        # Pause: enabled if running and not paused
        self.task_context_menu.entryconfig(
            "Pause Task", state="normal" if is_running and not is_paused else "disabled"
        )
        # Resume: enabled if paused
        self.task_context_menu.entryconfig(
            "Resume Task", state="normal" if is_paused else "disabled"
        )
        # Stop: enabled if running
        self.task_context_menu.entryconfig(
            "Stop Task", state="normal" if is_running else "disabled"
        )
        # Force Kill: enabled if running
        self.task_context_menu.entryconfig(
            "Force Kill", state="normal" if is_running else "disabled"
        )

        # Show context menu
        try:
            self.task_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.task_context_menu.grab_release()

    def _pause_selected_task(self):
        """Pause the selected task at next loop boundary."""
        task = self._get_context_menu_task()
        if task:
            task.pause()
            self._update_status(
                f"Pause queued for {os.path.basename(task.folder)}", DarkTheme.WARNING
            )
            self._update_tasks_list()

    def _resume_selected_task(self):
        """Resume the selected paused task."""
        task = self._get_context_menu_task()
        if task:
            task.resume()
            self._update_status(f"Resumed {os.path.basename(task.folder)}", DarkTheme.SUCCESS)
            self._update_tasks_list()

    def _stop_selected_task(self):
        """Stop the selected task gracefully."""
        task = self._get_context_menu_task()
        if not task:
            return
        if messagebox.askyesno(
            "Stop Task",
            f"Stop task for {os.path.basename(task.folder)}?\n\nThis will stop at the next loop boundary.",
        ):
            if task.runner:
                task.runner.stop()
            self._update_status(f"Stopping {os.path.basename(task.folder)}...", DarkTheme.WARNING)

    def _force_kill_selected_task(self):
        """Force kill the selected task immediately."""
        task = self._get_context_menu_task()
        if not task:
            return
        if messagebox.askyesno(
            "Force Kill",
            f"Force kill task for {os.path.basename(task.folder)}?\n\n"
            "WARNING: This will immediately terminate the process.\n"
            "The task may be left in an incomplete state.",
            icon="warning",
        ):
            task.force_kill()
            self._update_status(f"Force killed {os.path.basename(task.folder)}", DarkTheme.ERROR)

    def _open_task_folder(self):
        """Open the selected task's folder in file explorer."""
        try:
            # Use context menu task if available (prevents race condition with listbox refresh),
            # fall back to selection for double-click handler
            task = self._get_context_menu_task() or self._get_selected_task()
            if not task:
                return
            folder = task.folder
            if not os.path.isdir(folder):
                messagebox.showerror("Error", f"Folder not found:\n{folder}")
                return
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder:\n{e}")

    def _view_task_details(self):
        """Show details about the selected task."""
        try:
            task = self._get_context_menu_task()
            if not task:
                return

            runner_status = task.get_runner_status()
            waiting_info = task.get_waiting_info()
            details = [
                f"Folder: {task.folder}",
                f"Elapsed: {task.get_elapsed_time()}",
                f"Attempt: {task.get_current_attempt()}",
                f"Status: {runner_status}",
                f"Paused: {task.is_paused()}",
                f"Pause Pending: {task.is_pause_pending()}",
            ]
            if waiting_info[0]:
                details.append(f"Waiting: {waiting_info[1]} ({waiting_info[2]}s remaining)")

            messagebox.showinfo("Task Details", "\n".join(details))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get task details:\n{e}")

    def _update_status(self, message, color=None):
        """Update the status label."""
        if color is None:
            color = DarkTheme.FG_DIM
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()

    def _update_activity(self, message):
        """Update the activity indicator."""
        self.activity_label.config(text=message)
        self.root.update_idletasks()

    def _update_tasks_list(self):
        """Update the running tasks listbox."""
        self.tasks_listbox.delete(0, tk.END)

        waiting_task = None

        if not self.running_tasks:
            self.tasks_listbox.insert(tk.END, "  No tasks running")
        else:
            for task in self.running_tasks:
                elapsed = task.get_elapsed_time()
                folder_name = os.path.basename(task.folder)
                attempt = task.get_current_attempt()
                runner_status = task.get_runner_status()

                # Build status display based on runner state
                if task.is_paused():
                    status_icon = "[PAUSED]"
                elif task.is_pause_pending():
                    status_icon = "[STOPPING]"
                elif task.is_waiting():
                    is_waiting, reason, remaining = task.get_waiting_info()
                    status_icon = f"[wait:{reason}]"
                    waiting_task = task
                elif runner_status == "running":
                    if attempt > 0:
                        status_icon = f"[#{attempt}]"
                    else:
                        status_icon = "[...]"
                elif runner_status == "stopped":
                    status_icon = "[STOPPED]"
                else:
                    status_icon = "[OK]"

                # Include attempt and wait info in display
                if task.is_waiting():
                    _, reason, remaining = task.get_waiting_info()
                    self.tasks_listbox.insert(
                        tk.END, f"  {status_icon} {folder_name} - {remaining}s"
                    )
                elif attempt > 0:
                    self.tasks_listbox.insert(
                        tk.END, f"  {status_icon} {folder_name} - {elapsed} (attempt {attempt})"
                    )
                else:
                    self.tasks_listbox.insert(tk.END, f"  {status_icon} {folder_name} - {elapsed}")

        # Update progress bar visibility
        if waiting_task:
            is_waiting, reason, remaining = waiting_task.get_waiting_info()
            if waiting_task.runner:
                total_duration = waiting_task.runner.sleep_seconds
                if total_duration > 0:
                    progress = 100 - (remaining / total_duration * 100)
                    self.wait_progress["value"] = max(0, min(100, progress))
            self.wait_progress.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        else:
            self.wait_progress.grid_remove()

    def _update_task_status(self):
        """Periodically update task status and display."""
        # Check task states: completed, blocked, failed, or stopped
        # Uses both file-based detection and runner state for reliability
        finished_tasks = []
        for task in self.running_tasks:
            # Check for completion (RALPH-COMPLETE.md exists)
            # Wait for the process to exit before marking as completed
            if task.is_complete() and not task.is_runner_active():
                task.status = "completed"
                finished_tasks.append(task)
                continue

            # Check for blocked state (RALPH-BLOCKED.md exists)
            if task.is_blocked():
                task.status = "blocked"
                finished_tasks.append(task)
                continue

            # Check runner state if runner is no longer active
            if task.runner and not task.is_runner_active():
                runner_status = task.get_runner_status()
                if runner_status in ("completed", "blocked", "stopped", "failed"):
                    task.status = runner_status
                    finished_tasks.append(task)
                    continue

        # Handle finished tasks
        for task in finished_tasks:
            self._move_files_to_backup(task)
            backup_path = os.path.join(self.backup_dir, task.backup_guid)

            if task.status == "completed":
                # Launch viewer for completed tasks
                self._launch_viewer(backup_path)
            elif task.status == "blocked":
                # Show blocked notification
                logger.warning(f"Task blocked: {task.folder}")
                self._update_status(
                    f"Task blocked: {os.path.basename(task.folder)}", DarkTheme.WARNING
                )
            elif task.status == "failed":
                # Show failure notification
                error_msg = task.get_runner_error() or "Unknown error"
                logger.error(f"Task failed: {task.folder} - {error_msg}")
                self._update_status(
                    f"Task failed: {os.path.basename(task.folder)}", DarkTheme.ERROR
                )
            elif task.status == "stopped":
                # Show stopped notification
                logger.info(f"Task stopped: {task.folder}")
                self._update_status(
                    f"Task stopped: {os.path.basename(task.folder)}", DarkTheme.FG_DIM
                )

        # Remove finished tasks from running list
        self.running_tasks = [t for t in self.running_tasks if t.status == "running"]

        # Check for tasks paused due to missing checkpoint
        for task in self.running_tasks:
            if task.is_missing_checkpoint_pause():
                task_id = id(task)
                if task_id not in self._checkpoint_dialogs:
                    self._show_missing_checkpoint_dialog(task)

        # Update display
        self._update_tasks_list()

        # Update activity indicator with animation
        if self.running_tasks:
            dots = "." * ((int(datetime.now().timestamp()) % 3) + 1)
            self._update_activity(f"Working{dots}")
        else:
            self._update_activity("")

        # Schedule next update (faster when any task is waiting for progress bar smoothness)
        has_waiting = any(t.is_waiting() for t in self.running_tasks)
        update_interval = 500 if has_waiting else 1000
        self.task_update_id = self.root.after(update_interval, self._update_task_status)

    def _run_ralph(self):
        """Execute the Ralph setup and run process."""
        # Validate inputs
        target_folder = self.selected_folder.get().strip()
        design_content = self.design_text.get("1.0", tk.END).strip()

        if not target_folder:
            messagebox.showerror("Error", "Please select a target folder.")
            return

        if not os.path.isdir(target_folder):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return

        if not design_content:
            messagebox.showerror("Error", "Please enter content for RALPH-DESIGN.md.")
            return

        # Validate model selection
        selected_model = self.selected_model.get()
        if not selected_model or selected_model == "Loading models...":
            messagebox.showerror("Error", "Please select a model.")
            return

        if selected_model not in self.available_models:
            messagebox.showerror("Error", "Please select a valid model from the list.")
            return

        try:
            # Add folder to recent folders list
            self._add_to_recent_folders(target_folder)

            # Generate unique backup GUID
            backup_guid = str(uuid.uuid4())

            # Step 1: Create backup
            self._update_status("Creating backup...", DarkTheme.FG_SECONDARY)
            self._create_backup(target_folder, backup_guid, design_content)

            # Step 2: Remove existing files
            self._update_status("Removing existing files...", DarkTheme.FG_SECONDARY)
            self._remove_existing_files(target_folder)

            # Step 3: Create RALPH-DESIGN.md
            self._update_status("Creating RALPH-DESIGN.md...", DarkTheme.FG_SECONDARY)
            self._create_design_file(target_folder, design_content)

            # Step 4: Copy RALPH-SPECS.md (lookup table)
            self._copy_specs_file(target_folder)

            # Step 4.5: Copy opencode.json if checkbox is checked
            opencode_json_copied = self._copy_opencode_json(target_folder)

            # Step 5: Start RalphLoopRunner (replaces script copying and terminal execution)
            self._update_status("Starting Ralph loop...", DarkTheme.FG_SECONDARY)

            # Get variant (None if "None" selected)
            selected_variant = self.selected_variant.get()
            variant = selected_variant if selected_variant and selected_variant != "None" else None

            runner = RalphLoopRunner(
                folder=target_folder,
                model=selected_model,
                max_attempts=40,
                sleep_seconds=2,
                variant=variant,
            )
            runner.start()

            # Add to running tasks
            task = RunningTask(target_folder, backup_guid, runner=runner)
            task.opencode_json_copied = opencode_json_copied
            self.running_tasks.append(task)
            self._update_tasks_list()

            self._update_status("Ralph started successfully!", DarkTheme.SUCCESS)

        except Exception as e:
            self._update_status(f"Error: {str(e)}", DarkTheme.ERROR)
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")

    def _create_backup(self, target_folder, backup_guid, design_content):
        """Create backup of files being sent to the project."""
        backup_path = os.path.join(self.backup_dir, backup_guid)
        os.makedirs(backup_path, exist_ok=True)

        # Save backup info
        info_path = os.path.join(backup_path, "backup_info.txt")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"Backup Created: {datetime.now().isoformat()}\n")
            f.write(f"Target Folder: {target_folder}\n")
            f.write(f"Backup GUID: {backup_guid}\n")

        # Save RALPH-DESIGN.md content
        design_backup_path = os.path.join(backup_path, "RALPH-DESIGN.md")
        with open(design_backup_path, "w", encoding="utf-8") as f:
            f.write(design_content)

        # Copy existing RALPH-*.md files if they exist
        files_to_backup = [
            "RALPH-DESIGN.md",
            "RALPH-PROGRESS.md",
            "RALPH-COMPLETE.md",
            "RALPH-PLAN.md",
            "RALPH-CHECKPOINT.md",
            "RALPH-BLOCKED.md",
        ]
        for filename in files_to_backup:
            source_path = os.path.join(target_folder, filename)
            if os.path.exists(source_path):
                dest_path = os.path.join(backup_path, f"existing_{filename}")
                shutil.copy2(source_path, dest_path)

        logger.info(f"Backup created: {backup_path}")

    def _remove_existing_files(self, folder):
        """Remove existing RALPH-*.md files from the target folder."""
        files_to_remove = [
            "RALPH-DESIGN.md",
            "RALPH-PROGRESS.md",
            "RALPH-COMPLETE.md",
            "RALPH-PLAN.md",
            "RALPH-CHECKPOINT.md",
            "RALPH-BLOCKED.md",
        ]

        for filename in files_to_remove:
            filepath = os.path.join(folder, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Removed: {filepath}")

    def _create_design_file(self, folder, content):
        """Create RALPH-DESIGN.md file with the given content."""
        filepath = os.path.join(folder, "RALPH-DESIGN.md")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Created: {filepath}")

    def _copy_specs_file(self, target_folder):
        """Copy RALPH-SPECS.md to target folder if it exists in script dir."""
        source_path = os.path.join(self.script_dir, "RALPH-SPECS.md")
        dest_path = os.path.join(target_folder, "RALPH-SPECS.md")
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied: {source_path} -> {dest_path}")

    def _copy_opencode_json(self, target_folder: str) -> bool:
        """Copy opencode.json to target folder if checkbox checked and not already present."""
        if not self.copy_opencode_json.get():
            return False
        source_path = os.path.join(self.script_dir, "opencode.json")
        dest_path = os.path.join(target_folder, "opencode.json")
        if os.path.exists(source_path) and not os.path.exists(dest_path):
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied: {source_path} -> {dest_path}")
            return True
        return False

    def _move_files_to_backup(self, task):
        """Move ralph files from target folder to backup folder before viewing."""
        backup_path = os.path.join(self.backup_dir, task.backup_guid)
        os.makedirs(backup_path, exist_ok=True)

        # Move RALPH-*.* files to backup
        files_to_move = [
            "RALPH-DESIGN.md",
            "RALPH-PROGRESS.md",
            "RALPH-COMPLETE.md",
            "RALPH-PLAN.md",
        ]

        # Also move opencode.json if we copied it
        if task.opencode_json_copied:
            files_to_move.append("opencode.json")

        for filename in files_to_move:
            source_path = os.path.join(task.folder, filename)
            if os.path.exists(source_path):
                dest_path = os.path.join(backup_path, filename)
                shutil.move(source_path, dest_path)
                logger.info(f"Moved to backup: {source_path} -> {dest_path}")

    def _show_missing_checkpoint_dialog(self, task: RunningTask):
        """Show dialog when RALPH-CHECKPOINT.md is not created after an iteration.

        Allows user to view RALPH-PROGRESS.md and RALPH-PLAN.md and decide
        whether to continue the loop or stop.
        """
        task_id = id(task)

        dialog = tk.Toplevel(self.root)
        dialog.title("Missing Checkpoint")

        # Track this dialog
        self._checkpoint_dialogs[task_id] = dialog
        dialog.geometry("650x550")
        dialog.minsize(550, 450)  # Ensure buttons are always visible
        dialog.configure(bg=DarkTheme.BG_PRIMARY)
        dialog.transient(self.root)
        dialog.grab_set()

        # Header
        header = tk.Label(
            dialog,
            text="RALPH-CHECKPOINT.md was not created",
            font=("Segoe UI", 14, "bold"),
            bg=DarkTheme.BG_PRIMARY,
            fg=DarkTheme.WARNING,
        )
        header.pack(pady=(20, 10))

        info_label = tk.Label(
            dialog,
            text="The agent did not create a checkpoint file. Review progress and decide to continue or stop.",
            font=("Segoe UI", 10),
            bg=DarkTheme.BG_PRIMARY,
            fg=DarkTheme.FG_PRIMARY,
            wraplength=550,
        )
        info_label.pack(pady=(0, 15))

        # Notebook for viewing files
        style = ttk.Style(dialog)
        style.configure("Missing.TNotebook", background=DarkTheme.BG_PRIMARY)
        style.configure(
            "Missing.TNotebook.Tab",
            padding=[15, 8],
            font=("Consolas", 10),
            background=DarkTheme.BG_SECONDARY,
            foreground=DarkTheme.FG_PRIMARY,
        )
        style.map(
            "Missing.TNotebook.Tab",
            background=[("selected", DarkTheme.BG_INPUT)],
            foreground=[("selected", DarkTheme.FG_SECONDARY)],
        )

        # Button frame - pack FIRST with side="bottom" so it always has space
        btn_frame = tk.Frame(dialog, bg=DarkTheme.BG_PRIMARY)
        btn_frame.pack(side="bottom", fill="x", padx=15, pady=15)

        notebook = ttk.Notebook(dialog, style="Missing.TNotebook")
        notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # RALPH-PROGRESS.md tab
        progress_frame = tk.Frame(notebook, bg=DarkTheme.BG_PRIMARY)
        notebook.add(progress_frame, text="RALPH-PROGRESS.md")

        progress_text = tk.Text(
            progress_frame,
            wrap="word",
            font=("Consolas", 10),
            bg=DarkTheme.BG_INPUT,
            fg=DarkTheme.FG_PRIMARY,
            padx=10,
            pady=10,
            relief="flat",
        )
        progress_scroll = tk.Scrollbar(progress_frame, command=progress_text.yview)
        progress_text.config(yscrollcommand=progress_scroll.set)
        progress_scroll.pack(side="right", fill="y")
        progress_text.pack(side="left", fill="both", expand=True)

        progress_path = os.path.join(task.folder, "RALPH-PROGRESS.md")
        try:
            with open(progress_path, encoding="utf-8") as f:
                progress_text.insert("1.0", f.read())
        except FileNotFoundError:
            progress_text.insert("1.0", "File not found")
        progress_text.config(state="disabled")

        # RALPH-PLAN.md tab
        plan_frame = tk.Frame(notebook, bg=DarkTheme.BG_PRIMARY)
        notebook.add(plan_frame, text="RALPH-PLAN.md")

        plan_text = tk.Text(
            plan_frame,
            wrap="word",
            font=("Consolas", 10),
            bg=DarkTheme.BG_INPUT,
            fg=DarkTheme.FG_PRIMARY,
            padx=10,
            pady=10,
            relief="flat",
        )
        plan_scroll = tk.Scrollbar(plan_frame, command=plan_text.yview)
        plan_text.config(yscrollcommand=plan_scroll.set)
        plan_scroll.pack(side="right", fill="y")
        plan_text.pack(side="left", fill="both", expand=True)

        plan_path = os.path.join(task.folder, "RALPH-PLAN.md")
        try:
            with open(plan_path, encoding="utf-8") as f:
                plan_text.insert("1.0", f.read())
        except FileNotFoundError:
            plan_text.insert("1.0", "File not found")
        plan_text.config(state="disabled")

        def cleanup_dialog():
            """Remove dialog from tracking when closed."""
            if task_id in self._checkpoint_dialogs:
                del self._checkpoint_dialogs[task_id]

        def on_continue():
            task.continue_after_missing_checkpoint()
            cleanup_dialog()
            dialog.destroy()

        def on_stop():
            task.stop_after_missing_checkpoint()
            cleanup_dialog()
            dialog.destroy()

        def on_window_close():
            """Handle window close button (X)."""
            cleanup_dialog()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_window_close)

        continue_btn = tk.Button(
            btn_frame,
            text="Continue Loop",
            command=on_continue,
            bg=DarkTheme.ACCENT,
            fg="#ffffff",
            activebackground=DarkTheme.ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 11),
            padx=25,
            pady=8,
            cursor="hand2",
        )
        continue_btn.pack(side="right", padx=(10, 0))

        stop_btn = tk.Button(
            btn_frame,
            text="Stop Loop",
            command=on_stop,
            bg=DarkTheme.ERROR,
            fg="#ffffff",
            activebackground="#ff6666",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 11),
            padx=25,
            pady=8,
            cursor="hand2",
        )
        stop_btn.pack(side="right")

        # Center dialog on main window (same monitor)
        dialog.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - dialog.winfo_width()) // 2
        y = parent_y + (parent_height - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _launch_viewer(self, folder):
        """Launch integrated viewer window to display completion results."""
        try:
            # Create and show the integrated viewer window (centered on main window)
            RalphViewer(folder, self.root)
            logger.info(f"Launched integrated viewer for: {folder}")

            # Run text-to-speech on all platforms when task completes
            self._speak_ralph_quote()

        except Exception as e:
            logger.error(f"Error launching viewer: {e}")
            # Fallback: Try launching external viewer script if integrated fails
            viewer_path = os.path.join(self.script_dir, "ralph_viewer.py")
            if os.path.exists(viewer_path):
                try:
                    is_windows = platform.system() == "Windows"
                    python_cmd = "pythonw" if is_windows else "python3"
                    subprocess.Popen(
                        [python_cmd, viewer_path, folder],
                        cwd=folder,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    # Still try to speak even in fallback case
                    self._speak_ralph_quote()
                except Exception as e2:
                    logger.error(f"Fallback viewer also failed: {e2}")

    def _speak_ralph_quote(self):
        """Speak a random Ralph Wiggum quote using cross-platform text-to-speech.

        Supports:
        - Windows: PowerShell System.Speech.Synthesis.SpeechSynthesizer
        - macOS: 'say' command
        - Linux: espeak or festival
        """
        # Select a random quote (use simpler quotes for TTS)
        tts_quotes = [
            "I bent my Wookie",
            "Me fail English? That's unpossible!",
            "Hi Super Nintendo Chalmers!",
            "I choo-choo-choose you!",
            "My cat's breath smells like cat food",
            "I'm learnding!",
            "Go banana!",
            "I found a moonrock in my nose!",
            "I sleep in a drawer!",
            "The doctor said I wouldn't have so many nosebleeds if I kept my finger outta there",
        ]
        quote = random.choice(tts_quotes)
        logger.info(f"Ralph says: {quote}")

        current_platform = platform.system()

        try:
            if current_platform == "Windows":
                # Windows: Use PowerShell with System.Speech
                # Escape single quotes in the quote for PowerShell
                escaped_quote = quote.replace("'", "''")
                powershell_cmd = (
                    f"Add-Type -AssemblyName System.Speech; "
                    f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped_quote}')"
                )
                subprocess.Popen(
                    ["powershell", "-Command", powershell_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )

            elif current_platform == "Darwin":  # macOS
                # macOS: Use the 'say' command (built-in)
                # start_new_session=True ensures the process runs independently
                subprocess.Popen(
                    ["say", quote],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            elif current_platform == "Linux":
                # Linux: Try espeak first, then spd-say, then festival
                # start_new_session=True ensures the process runs independently
                tts_started = False

                # Try espeak (most common)
                try:
                    subprocess.Popen(
                        ["espeak", quote],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    tts_started = True
                except FileNotFoundError:
                    pass

                # Try spd-say (speech-dispatcher) - non-blocking
                if not tts_started:
                    try:
                        subprocess.Popen(
                            ["spd-say", quote],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True,
                        )
                        tts_started = True
                    except FileNotFoundError:
                        pass

                # Try festival as last resort (uses pipe, run in thread to avoid blocking)
                if not tts_started:
                    try:

                        def run_festival():
                            try:
                                process = subprocess.Popen(
                                    ["festival", "--tts"],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    start_new_session=True,
                                )
                                process.communicate(input=quote.encode("utf-8"))
                            except Exception:
                                pass

                        threading.Thread(target=run_festival, daemon=True).start()
                        tts_started = True
                    except FileNotFoundError:
                        pass

                if not tts_started:
                    logger.warning(
                        "No TTS engine found on Linux. "
                        "Install espeak, festival, or speech-dispatcher."
                    )
            else:
                logger.warning(f"Text-to-speech not supported on {current_platform}")

        except Exception as e:
            logger.error(f"Error running text-to-speech: {e}")

    def _quit_app(self):
        """Quit the application."""
        if self.task_update_id:
            self.root.after_cancel(self.task_update_id)
        self.root.quit()


def main():
    """Main entry point."""
    root = tk.Tk()

    # Set dark theme background before creating window
    root.configure(bg=DarkTheme.BG_PRIMARY)

    # CRITICAL: Set global listbox colors BEFORE any widgets are created
    # This affects combobox popdown listboxes which are created on-demand
    # Priority 100 is highest, ensuring these override all other settings
    root.option_add("*Listbox.background", DarkTheme.BG_INPUT, 100)
    root.option_add("*Listbox.foreground", DarkTheme.FG_PRIMARY, 100)
    root.option_add("*Listbox.selectBackground", DarkTheme.ACCENT, 100)
    root.option_add("*Listbox.selectForeground", "#ffffff", 100)
    root.option_add("*Listbox.font", ("Segoe UI", 10), 100)

    # Also set using the TCombobox pattern
    root.option_add("*TCombobox*Listbox.background", DarkTheme.BG_INPUT, 100)
    root.option_add("*TCombobox*Listbox.foreground", DarkTheme.FG_PRIMARY, 100)
    root.option_add("*TCombobox*Listbox.selectBackground", DarkTheme.ACCENT, 100)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff", 100)

    RalphGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
