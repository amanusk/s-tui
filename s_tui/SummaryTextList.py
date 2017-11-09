import urwid
import itertools
from collections import OrderedDict

class SummaryTextList:
    def __init__(self, source, alert_color=None):
        self.summary_text_items = OrderedDict((key, urwid.Text(str(val), align='right')) for key, val in source.get_summary().items())
        self.source = source
        self.alert_color = alert_color

    def get_text_item_list(self):
        return itertools.chain.from_iterable([urwid.Text(str(key), align='left'), val]  for (key, val) in self.summary_text_items.items())

    def update(self):
        for key, val in self.source.get_summary().items():
            if key in self.summary_text_items:
                try:
                    # NOTE: Not the best way to keep the max values persistent colors
                    if 'Max' in key:
                        if self.source.get_max_triggered():
                            self.summary_text_items[key].set_text((self.alert_color, str(val)))
                        else:
                            self.summary_text_items[key].set_text(str(val))
                    else:
                        if self.source.get_edge_triggered():
                            self.summary_text_items[key].set_text((self.alert_color, str(val)))
                        else:
                            self.summary_text_items[key].set_text(str(val))

                except (NotImplementedError):
                    self.summary_text_items[key].set_text(str(val))

    def get_is_available(self):
        return self.source.get_is_available()
