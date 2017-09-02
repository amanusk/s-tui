

class Source:

    def get_reading(self):
        raise NotImplementedError("Get reading is not implemented")

    def update(self):
        raise NotImplementedError("Get reading is not implemented")

    def get_maximum(self):
        raise NotImplementedError("Get maximum is not implemented")

    def get_is_available(self):
        raise NotImplementedError("Get is available is not implemented")

    def reset(self):
        raise NotImplementedError("Reset max information")

    def get_summary(self):
        raise NotImplementedError("Get summary is not implemented")

    def get_source_name(self):
        raise NotImplementedError("Get source name is not implemented")

    def get_edge_triggered(self):
        raise NotImplementedError("Get Edge triggered not implemented")

    def get_max_triggered(self):
        raise NotImplementedError("Get Edge triggered not implemented")

    def get_measurement_unit(self):
        raise NotImplementedError("Get measurement unit is not implemented")


class MockSource(Source):
    def get_reading(self):
        return 5

    def get_maximum(self):
        return 20

    def get_is_available(self):
        return True

    def get_summary(self):
        return {'MockValue': 5, 'Tahat': 34}

    def get_source_name(self):
        return 'Mock Source'

    def get_measurement_unit(self):
        return 'K'
