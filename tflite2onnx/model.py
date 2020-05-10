import tflite
import onnx
from onnx import helper

from .common import T2OBase, logger, Status
from .graph import Graph


class Model(T2OBase):
    """Everything helps to convert TFLite model to ONNX model"""
    def __init__(self, model: tflite.Model):
        super().__init__(model)
        self.tflite = model
        self.graphes = []
        self.setInited()

    def parse(self):
        logger.debug("Parsing the Model...")
        graph_count = self.model.SubgraphsLength()
        if (graph_count != 1):
            raise NotImplementedError("ONNX supports one graph per model only, while TFLite has ",
                                      graph_count)
        tflg = self.model.Subgraphs(0)
        graph = Graph(self.model, tflg)
        self.graphes.append(graph)

        for g in self.graphes:
            g.parse()

        self.setParsed()

    def propagate(self):
        self.parse()
        logger.debug("Propagating...")
        for g in self.graphes:
            g.propagate()
        self.setPropagated()

    def convert(self):
        self.propagate()
        logger.debug("Converting...")
        for g in self.graphes:
            g.convert()

        # ONNX restrictions
        opset = helper.make_operatorsetid(onnx.defs.ONNX_DOMAIN, 11)
        attrs = {
                'producer_name': 'tflite2onnx',
                'ir_version': 6,
                'opset_imports': [opset],
                }

        self.onnx = helper.make_model(self.graphes[0].onnx, **attrs)
        self.setConverted()

    def save(self, path: str):
        logger.debug("saving model as %s", path)
        assert(self.status is Status.CONVERTED)
        onnx.checker.check_model(self.onnx)
        onnx.save(self.onnx, path)
