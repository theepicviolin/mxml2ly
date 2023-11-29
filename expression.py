class Expression:
    dynamics = {'\\pp', '\\p', '\\mp', '\\mf', '\\f', '\\ff', '\\fp', '\\sf', '\\sfz', '\\<', '\\>', '\\cresc'}

    def __init__(self, text):
        if text is None:
            text = ''
        self.text = {text}

    def add(self, new):
        if new == '' or new is None:
            return
        self.text.add(new)
        if self.text.intersection(self.dynamics):
            self.text.discard("\\!")

    def __str__(self):
        return ''.join(self.text)
