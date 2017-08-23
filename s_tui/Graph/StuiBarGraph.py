from ComplexBarGraphs import LabeledBarGraph
from ComplexBarGraphs import ScalableBarGraph

class StuiBarGraph(LabeledBarGraph):
    def __init__(self, source, title, measurement_unit, color_a, color_b, x_label, y_label):
        self.source = source
        self.title = title
        self.measurement_unit = measurement_unit


        w = ScalableBarGraph(['bg background', color_a, color_b])
        super(StuiBarGraph, self).__init__([w, x_label, y_label, title])

