# Import StreamController modules
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder

# Import actions
from .actions.FetchAction.FetchAction import FetchAction

class JSONDeckPlugin(PluginBase):
    def __init__(self):
        super().__init__()

        ## Register actions
        self.fetch_action_holder = ActionHolder(
            plugin_base = self,
            action_base = FetchAction,
            action_id = "eu_meola_json_deck::FetchAction",
            action_name = "Fetch JSON",
        )
        self.add_action_holder(self.fetch_action_holder)

        # Register plugin
        self.register(
            plugin_name = "JSON-deck",
            github_repo = "https://github.com/AkselMeola/eu_meola_json_deck",
            plugin_version = "1.0.0",
            app_version = "1.1.1-alpha"
        )