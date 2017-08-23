

class Source:

    def get_reading(self):
        raise NotImplementedError("Get reading is not implemented")

    def get_maximum(self):
        raise NotImplementedError("Get maximum is not implemented")

    def get_is_available(self):
        raise NotImplementedError("Get is available is not implemented")


class MockSource(Source):
    def get_reading(self):
        return 5

    def get_maximum(self):
        return 20

    def get_is_available(self):
        return True