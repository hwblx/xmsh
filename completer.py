# Copyright (C) 2025 hwblx

import readline
from difflib import get_close_matches

class Completer:
    def __init__(self, cutoff=0.6):
        self.keywords = []
        self.cutoff = cutoff
    
    def set_keywords(self, keywords):
        self.keywords = sorted(keywords)

    def set_cutoff(self, cutoff):
        self.cutoff = cutoff

    def completer(self, text, state):
        matches = get_close_matches(text, self.keywords, n=10, cutoff=self.cutoff)
        try:
            return matches[state]
        except IndexError:
            return None

    def init_readline(self, delims=' ";:=', parse=('tab: menu-complete',)):
        readline.set_completer(self.completer)
        readline.set_completer_delims(delims)

        if isinstance(parse, str):
            readline.parse_and_bind(parse)
        else:
            for binding in parse:
                readline.parse_and_bind(binding)

    @staticmethod
    def set_readline_hook(text):
        readline.set_startup_hook(lambda: readline.insert_text(text))

