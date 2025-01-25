# Import StreamController modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

# Import python modules
import os
import threading
import requests
import json

from loguru import logger as log

# Import gtk modules - used for the config rows
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


from dataclasses import dataclass
from typing import List

@dataclass
class Frame:
    top_label: str
    center_label: str
    bottom_label: str
    media_path: str

@dataclass
class ActionFrames:
    frame_duration: int
    frames: List[Frame]

class FetchAction(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.path_entry = None
        self.auto_run_spinner = None
        self.auto_run_timer: threading.Timer = None

        self.action_frames: ActionFrames = None
        self.frame_index = 0
        self.n_ticks = 0

    def on_ready(self) -> None:
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "logo.png")
        self.set_media(media_path=icon_path, size=0.75)
        
    def on_key_down(self) -> None:
        self.do_fetch()
        print("Key down")
    
    def on_key_up(self) -> None:
        print("Key up")

    def get_config_rows(self) -> list:
        self.path_entry = Adw.EntryRow(title="URL, Path to file or command")
        self.auto_run_spinner = Adw.SpinRow.new_with_range(step=1, min=0, max=3600)
        self.auto_run_spinner.set_title("Auto run (s)")
        self.auto_run_spinner.set_subtitle("Set 0 to disable")

        self.load_config_defaults()

        # Connect signals
        self.path_entry.connect("notify::text", self.on_path_changed)
        self.auto_run_spinner.connect("notify::value", self.on_auto_run_changed)

        return [self.path_entry, self.auto_run_spinner]

    def load_config_defaults(self):
        settings = self.get_settings()
        self.path_entry.set_text(settings.get("path", "")) # Does not accept None
        self.auto_run_spinner.set_value(settings.get("auto_run", 0))

    def on_path_changed(self, entry, *args):
        settings = self.get_settings()
        settings["path"] = entry.get_text()
        self.set_settings(settings)

    def on_auto_run_changed(self, spinner, *args):
        settings = self.get_settings()
        settings["auto_run"] = spinner.get_value()
        self.set_settings(settings)


    def get_exec_path(self):
        settings = self.get_settings()
        return settings.get("path", "")

    def process_exec_path(self, execPath):
        # Check if execPath is a web URL
        if execPath.startswith(("http://", "https://")):
            return self.fetch_from_url(execPath)
        # Check if execPath is a non-executable file
        elif os.path.isfile(execPath) and not os.access(execPath, os.X_OK):
            return self.fetch_from_file(execPath)
        # Otherwise, treat it as a command
        else:
            return self.fetch_from_cmd(execPath)

    def fetch_from_url(self, url):
        if url in ["", None]:
            self.show_error(duration=1)

        try:
            response = requests.get(url=url, timeout=3)
            return response.text
        except Exception as e:
            log.error(e)
            self.show_error(duration=1)

        return None

    def fetch_from_file(self, path):
        pass

    def fetch_from_cmd(self, cmd):
        pass

    def do_fetch(self):
        exec_path = self.get_exec_path()
        result = self.process_exec_path(exec_path)

        if result in ["", None]:
            self.show_error(duration=1)
            return

        data = None

        try:
            data = json.loads(result)
        except json.decoder.JSONDecodeError as e:
            log.error(e)
            self.show_error(duration=1)
            return

        # Convert to dataclass
        self.action_frames = ActionFrames(
            frame_duration=data['frame_duration'],
            frames=[Frame(**frame) for frame in data['frames']]
        )

        self.do_show()

    def do_show(self):
        if self.action_frames is None:
            return

        frame = self.action_frames.frames[self.frame_index] or None
        if frame is None:
            return

        # Set labels
        if frame.top_label is not None:
            self.set_top_label(frame.top_label)
        if frame.center_label is not None:
            self.set_center_label(frame.center_label)
        if frame.bottom_label is not None:
            self.set_bottom_label(frame.bottom_label)


    def on_tick(self):
        if self.action_frames is None:
            return

        duration = self.action_frames.frame_duration
        if duration in [0, None]:
            duration = 30 # Set default duration of 30 tics

        # Cycle frame after N tics
        if self.n_ticks % duration == 0:
            self.n_ticks = 0
            self.frame_index += 1
            if self.frame_index >= len(self.action_frames.frames):
                self.frame_index = 0

            self.do_show()

        self.n_ticks += 1

