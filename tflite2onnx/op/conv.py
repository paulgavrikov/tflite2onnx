import tflite
from onnx import helper

from .. import tensor
from ..common import logger
from .op import Operator
from .transpose import TransposeHelper


OpTypeMapping = {
        tflite.BuiltinOperator.CONV_2D : 'Conv',     # noqa: E203
}


class Conv2D(Operator):
    def __init__(self, model, graph, op):
        Operator.__init__(self)

    def convert(self, model, graph, op):
        logger.debug("Converting...")
        self.tflite = op
        opcode = model.OperatorCodes(op.OpcodeIndex()).BuiltinCode()
        assert(opcode in OpTypeMapping)
        self.type = OpTypeMapping[opcode]

        assert(op.InputsLength() == 3)
        assert(op.OutputsLength() == 1)

        # input
        ii = op.Inputs(0)
        tensor.convert(model, graph, ii)
        inputTranspose = TransposeHelper(model, graph, op, 'NHWC', 'NCHW', iIndex=ii)
        self.inputs.append(inputTranspose.outputs[0])

        # weight
        wi = op.Inputs(1)
        wt = tensor.convert(model, graph, wi, False)
        weightTranspose = TransposeHelper(model, graph, op, 'OHWI', 'OIHW', iIndex=wi)
        self.inputs.append(weightTranspose.outputs[0])
        self.weights.append(weightTranspose.inputs[0])

        # bias
        bi = op.Inputs(2)
        bt = tensor.convert(model, graph, bi, False)
        self.inputs.append(bt)
        self.weights.append(bt)

        # options
        op_opt = op.BuiltinOptions()
        option = tflite.Conv2DOptions()
        option.Init(op_opt.Bytes, op_opt.Pos)

        kshape = wt.dims[1:3]
        dilations = [option.DilationHFactor(), option.DilationWFactor()]
        group = 1
        padding = option.Padding()
        strides = [option.StrideH(), option.StrideW()]
        # option.FusedActivationFunction()
        assert(padding == tflite.Padding.SAME)  # TODO: enable VALID padding
        auto_pad = 'SAME_UPPER'  # See ComputePaddingHeightWidth() of TFLite
        # pads #  This attribute cannot be used simultaneously with auto_pad attribute.

        # output
        oi = op.Outputs(0)
        tensor.convert(model, graph, oi)
        outputTranspose = TransposeHelper(model, graph, op, 'NCHW', 'NHWC', oIndex=oi)
        self.outputs.append(outputTranspose.inputs[0])

        inames = [t.name for t in self.inputs]
        onames = [t.name for t in self.outputs]
        logger.debug("Making ONNX...")
        self.onnx = helper.make_node(self.type, inames, onames, kernel_shape=kshape,
                                     strides=strides, auto_pad=auto_pad, dilations=dilations,
                                     group=group)

        return [inputTranspose, weightTranspose, self, outputTranspose]
