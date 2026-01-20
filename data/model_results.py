from cProfile import label


class ModelPredictResult:
    def __init__(self, label: str, confidence: float):
        self.label = label
        self.confidence = confidence

    def get_label(self): return self.label
    def get_confidence(self): return self.confidence