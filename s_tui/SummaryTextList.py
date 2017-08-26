import urwid
import itertools
from Sources.Source import Source

class SummaryTextList:
    def __init__(self, source):
        self.summary_text_items = dict((key, urwid.Text(str(val), align='right')) for key, val in source.get_summary().iteritems())
        self.source = source

    def get_text_item_list(self):
        return itertools.chain.from_iterable([urwid.Text(str(key), align='left'), val]  for (key, val) in self.summary_text_items.iteritems())

    def update(self):
        for key, val in self.source.get_summary().iteritems():
            if key in self.summary_text_items:
                self.summary_text_items[key].set_text(str(val))

    def get_is_available(self):
        return self.source.get_is_available()
