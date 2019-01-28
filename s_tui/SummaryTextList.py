import urwid


class SummaryTextList:
    MAX_LABEL_L = 11

    def __init__(self, source, alert_color=None):
        self.source = source
        self.alert_color = alert_color
        self.summery_text_list = []

    def get_text_item_list(self):

        summery_text_list = []
        for key, val in self.source.get_summary().items():
            label_w = urwid.Text(str(key[0:self.MAX_LABEL_L-1]), align='left')
            value_w = urwid.Text(str(val), align='right')
            col_w = urwid.Columns([label_w, value_w])
            summery_text_list.append(col_w)

        self.summery_text_list = summery_text_list

        return self.summery_text_list

    def get_is_available(self):
        return self.source.get_is_available()
