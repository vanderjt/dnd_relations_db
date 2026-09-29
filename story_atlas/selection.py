"""Ordered graph selection; identity never depends on display names."""
class OrderedSelection:
    def __init__(self):
        self.ids = []

    def select(self, ident, extend=False):
        if not extend:
            self.ids = [ident]
        elif ident in self.ids:
            self.ids.remove(ident)
        else:
            self.ids.append(ident)

    def source(self, ident):
        if ident in self.ids:
            self.ids.remove(ident)
            self.ids.insert(0, ident)

    def clear(self):
        self.ids.clear()

    def pairs(self):
        return [(self.ids[0], target) for target in self.ids[1:]] if self.ids else []
