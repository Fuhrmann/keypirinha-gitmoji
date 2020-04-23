# Keypirinha launcher (keypirinha.com)

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet
from .pyperclip import copy as pcopy
import json
from datetime import datetime
import os.path

class gitmoji(kp.Plugin):
    """
    Search for gitmoji and copy then to your clipboard
    This plugin was based on: http://www.packal.org/workflow/gitmoji-0 and http://www.packal.org/workflow/gitmoji
    """

    GITMOJI_URL = "https://raw.githubusercontent.com/carloscuesta/gitmoji/master/src/data/gitmojis.json"
    DAYS_KEEP_CACHE = 7
    ITEMCAT = kp.ItemCategory.USER_BASE + 1
    ACTION_ITEMCAT = kp.ItemCategory.USER_BASE + 2

    def __init__(self):
        super().__init__()
        self.emojis = []
        self.default_copy_action = 'code'

    def on_start(self):
        self.read_config()
        self.generate_cache()
        self.create_actions()
        self.get_gitmoji()
        pass

    def on_catalog(self):
        self.set_catalog([
            self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label="gitmoji",
                short_desc="Search gitmoji and copy them to your clipboard",
                target="gitmoji",
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.KEEPALL
            )
        ])

    def on_suggest(self, user_input, items_chain):
        if not items_chain or items_chain[0].category() != kp.ItemCategory.KEYWORD:
            return

        suggestions = self.filter_emojis(user_input)
        self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.LABEL_ASC)

    def filter_emojis(self, user_input):
        return list(filter(lambda item: self.has_title_description(item, user_input), self.emojis))

    def has_title_description(self, item, user_input):
        if user_input.lower() in item.label().lower() or user_input.lower() in item.short_desc().lower():
            return item

        return False

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.read_config()
            self.on_catalog()

    def on_execute(self, item, action):
        emojis_file = self.read_emojis_file()

        # Find the emoji
        emoji = next(e for e in emojis_file['gitmojis'] if item.target() == e['code'])

        # Copy emoji itself
        if ((action and action.name() == 'copy_emoji') or (not action and self.default_copy_action == 'copy_emoji')):
            pcopy(emoji['emoji'])
            return
        
        # Copy its code
        if (action and action.name() in ['copy_code'] or (not action and self.default_copy_action == 'copy_code')):
            pcopy(emoji['code'])
            return
        
        # Fallback
        pcopy(emoji['code'])

    def generate_cache(self):
        cache_path = self.get_cache_path()
        should_generate = False
        try:
            last_modified = datetime.fromtimestamp(os.path.getmtime(cache_path)).date()
            if ((last_modified - datetime.today().date()).days > self.DAYS_KEEP_CACHE):
                should_generate = True
        except Exception as exc:
            should_generate = True

        if not should_generate:
            return False

        try:
            opener = kpnet.build_urllib_opener()
            with opener.open(self.GITMOJI_URL) as request:
                response = request.read()
        except Exception as exc:
            self.err("Could not reach the gitmoji repository file to generate the cache: ", exc)

        data = json.loads(response)
        with open(cache_path, "w") as index_file:
            json.dump(data, index_file, indent=2)

    # Create all the emojis suggestions
    def get_gitmoji(self):
        if not self.emojis:
            emojis_file = self.read_emojis_file()
            for item in emojis_file['gitmojis']:
                if 'entity' in item:
                    suggestion = self.create_item(
                        category=self.ITEMCAT,
                        label=item['code'],
                        short_desc=item['description'],
                        target=item['code'],
                        args_hint=kp.ItemArgsHint.FORBIDDEN,
                        hit_hint=kp.ItemHitHint.IGNORE,
                        icon_handle=self.load_icon('res://{}/icons/{}.png'.format(self.package_full_name(), item['name']))
                    )

                    self.emojis.append(suggestion)

        return self.emojis

    # Create the default actions to the suggestions
    def create_actions(self):
        self.set_actions(self.ITEMCAT, [
            self.create_action(name="copy_code", label="Copy emoji code", short_desc="Copy the emoji :code: to clipboard"),
            self.create_action(name="copy_emoji", label="Copy emoji", short_desc="Copy emoji to clipboard"),
        ])

    # Returns the path to the cache
    def get_cache_path(self):
        cache_path = self.get_package_cache_path(True)
        return os.path.join(cache_path, 'gitmoji.json')
    
    # Read all emojis from cache file
    def read_emojis_file(self):
        with open(self.get_cache_path(), "r") as emojis_file:
            data = json.loads(emojis_file.read())
        
        return data
    
    # Reads the plugin's configuration
    def read_config(self):
        settings = self.load_settings()
        self.default_copy_action = settings.get('default_copy_action', section='main', fallback='copy_code')