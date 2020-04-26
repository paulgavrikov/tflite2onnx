import tflite
from onnx import helper

from ..common import logger
from .. import tensor
from .op import Operator


OpTypeMapping = {
        tflite.BuiltinOperator.ABS : 'Abs',     # noqa: E203
}


class Unary(Operator):
    def __init__(self, model, graph, index):
        super().__init__(model, graph, index)
        self.setInited()

    def parse(self):
        op = self.tflite
        opcode = self.model.OperatorCodes(op.OpcodeIndex()).BuiltinCode()
        assert(opcode in OpTypeMapping)
        self.type = OpTypeMapping[opcode]
        logger.debug("Parsing %s...", self.type)

        assert(op.InputsLength() == 1)
        assert(op.OutputsLength() == 1)

        ti = op.Inputs(0)
        to = tensor.get(self.model, self.graph, ti)
        to.parse()
        self.inputs.append(to)

        ti = op.Outputs(0)
        to = tensor.get(self.model, self.graph, ti)
        to.parse()
        self.outputs.append(to)

        self.setParsed()

    def buildGraph(self):
        logger.debug("Building graph in %s...", self.type)
        self.setGraphBuilt()

    def propagate(self):
        logger.debug("Propagating %s...", self.type)
        self.setPropagated()

    def convert(self):
        logger.debug("Converting %s...", self.type)
        self.buildGraph()
        self.propagate()

        self.inputs[0].convert()
        self.outputs[0].convert()

        inames = [t.name for t in self.inputs]
        onames = [t.name for t in self.outputs]
        self.onnx = helper.make_node(self.type, inames, onames)
        self.setConverted()
