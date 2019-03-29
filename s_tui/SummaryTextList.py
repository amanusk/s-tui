import urwid
from collections import OrderedDict


class SummaryTextList:
    MAX_LABEL_L = 12

    def __init__(self, source, alert_color=None):
        self.source = source
        self.alert_color = alert_color
        self.summery_text_list = []

        # We keep a dict of all the items in the summary list
        self.summary_text_items = OrderedDict()

    def get_text_item_list(self):

        summery_text_list = []
        for key, val in self.source.get_summary().items():
            label_w = urwid.Text(str(key[0:self.MAX_LABEL_L]))
            value_w = urwid.Text(str(val), align='right')
            # This can be accessed by the update method
            self.summary_text_items[key] = value_w
            col_w = urwid.Columns([('weight', 1.5, label_w), value_w])
            summery_text_list.append(col_w)

        self.summery_text_list = summery_text_list

        return self.summery_text_list

    def update(self):
        for key, val in self.source.get_summary().items():
            if key in self.summary_text_items:
                self.summary_text_items[key].set_text(str(val))

    def get_is_available(self):
        return self.source.get_is_available()
