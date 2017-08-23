from ComplexBarGraphs import LabeledBarGraph
from ComplexBarGraphs import ScalableBarGraph

class StuiBarGraph(LabeledBarGraph):

    MAX_SAMPLES = 1000

    def __init__(self, source, title, measurement_unit, color_a, color_b, bar_width = 1):
        self.source = source
        self.title = title
        self.measurement_unit = measurement_unit

        self.num_samples = self.MAX_SAMPLES
        self.graph_data = [0] * self.num_samples


        x_label = []
        y_label = [0, self.source.get_maximum()/2, self.source.get_maximum()]

        w = ScalableBarGraph(['bg background', color_a, color_b])
        super(StuiBarGraph, self).__init__([w, x_label, y_label, title])
        self.bar_graph.set_bar_width(bar_width)


    def get_current_summary(self):
        pass

    def get_title(self):
        return self.title

    def get_measurement_unit(self):
        return self.measurement_unit

    def get_is_available(self):
        return self.source.get_is_available()

    def update_displayed_graph_data(self):
        if not self.get_is_available():
            return

        l = []

        current_reading = self.source.get_reading()
        append_latest_value(self.graph_data, current_reading)

        # Get the graph width (dimension 1)
        num_displayed_bars = self.bar_graph.get_size()[1]
        # Iterage over all the information in the graph
        for n in range(self.MAX_SAMPLES-num_displayed_bars,self.data.MAX_SAMPLES):
            value = graph_data[n]
            # toggle between two bar types
            if n & 1:
                l.append([0, value])
            else:
                l.append([value, 0])
        self.bar_graph.set_data(l, data_max)
        y_label_size = graph.bar_graph.get_size()[0]
        self.set_y_label(self.get_label_scale(0, data_max, y_label_size))

    @staticmethod
    def append_latest_value(values, new_val):

        values.append(new_val)
        return values[1:]
