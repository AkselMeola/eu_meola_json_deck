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
import tempfile
import subprocess

from loguru import logger as log

# Import gtk modules - used for the config rows
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


from dataclasses import dataclass
from typing import List
from typing import Optional


@dataclass
class Frame:
    top_label: Optional[str] = None
    center_label: Optional[str] = None
    bottom_label: Optional[str] = None
    media_path: Optional[str] = None

@dataclass
class ActionFrames:
    frames: List[Frame]
    frame_duration: Optional[int] = None

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
        self.start_timer()
        self.do_fetch()
        
    def on_key_down(self) -> None:
        self.do_fetch()

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


    def stop_timer(self):
        if self.auto_run_timer is not None:
            self.auto_run_timer.cancel()

    def start_timer(self):
        self.stop_timer()
        settings = self.get_settings()
        if settings.get("auto_run", 0) <= 0:
            return
        self.auto_run_timer = threading.Timer(settings.get("auto_run", 0), self.do_fetch)
        self.auto_run_timer.start()

    #def on_key_up(self) -> None:
    #    print("Key up")

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
        self.start_timer()

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

    # Fetch from a Web URL
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

    # Fetch contents of a file
    def fetch_from_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()  # Read the entire file content
            return content
        except FileNotFoundError:
            log.error("File not found:" + path)
            return None
        except IOError as e:
            log.error(e)
            return None

    # Run the command and capture the output
    def fetch_from_cmd(self, cmd):
        if self.is_in_flatpak():
            cmd = "flatpak-spawn --host " + cmd

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            log.error(e)
            return None

    def is_in_flatpak(self) -> bool:
        return os.path.isfile('/.flatpak-info')

    def do_fetch(self):
        self.start_timer()

        exec_path = self.get_exec_path()
        result = self.process_exec_path(exec_path)

        if result in ["", None]:
            self.show_error(duration=1)
            return

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

        self.frame_index = 0
        self.n_ticks = 0

        self.do_show()

    def do_show(self):
        if self.action_frames is None:
            return

        frame = self.action_frames.frames[self.frame_index] or None
        if frame is None:
            log.error("Frame not found")
            return

        # Set labels
        if frame.top_label is not None:
            self.set_top_label(frame.top_label)
        if frame.center_label is not None:
            self.set_center_label(frame.center_label)
        if frame.bottom_label is not None:
            self.set_bottom_label(frame.bottom_label)

        if frame.media_path is not None:
            self.process_image_path(frame.media_path)


    # TODO: Use Content-Disposition header to detect original file name
    def download_from_url(self, url, target_path):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Ensure we raise an error for invalid responses
            with open(target_path, 'wb') as f:
                f.write(response.content)
            return target_path
        except requests.exceptions.RequestException as e:
            return None

    def process_image_path(self, value):
        # Check if the value is a path to a file
        if os.path.isfile(value):
            self.set_media(media_path=value)
        # Check if the value is a URL
        elif value.startswith(('http://', 'https://')):
            # Create a temp directory to save the file
            filename = "jsondeck_" + os.path.basename(value)  # Extract the filename from the URL
            tmp_dir = tempfile.gettempdir()
            target_path = os.path.join(tmp_dir, filename)

            # Skip downloading if the file already exists in the temp directory
            if not os.path.exists(target_path):
                self.download_from_url(value, target_path)

            if os.path.isfile(target_path):
                self.set_media(media_path=target_path)

