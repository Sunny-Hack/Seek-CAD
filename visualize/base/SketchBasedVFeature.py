from abc import ABC, abstractmethod

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCC.Core.TopoDS import TopoDS_Shape
from visualize.macro import *
from visualize.base.BaseVFeature import BaseVFeature
from visualize.modules.Sketch import Sketch


class SketchBasedVFeature(BaseVFeature, ABC):
    def __init__(self, feat_name, feat_id, feat_type, parameters):
        super().__init__(feat_name, feat_id, feat_type, parameters)

    @abstractmethod
    def op(self, sketch: Sketch) -> TopoDS_Shape:
        pass

    @abstractmethod
    def transform(self, s: TopoDS_Shape, cap_type: CapType, param=None) -> TopoDS_Shape:
        pass

    @staticmethod
    def op_boolean(body1: TopoDS_Shape, body2: TopoDS_Shape, boolean_op: BooleanOp) -> TopoDS_Shape:
        if body1 is None or body1.IsNull():
            s = body2
        elif body2 is None or body2.IsNull():
            s = body1
        else:
            if boolean_op in [BooleanOp.NEW, BooleanOp.ADD]:
                s = BRepAlgoAPI_Fuse(body1, body2).Shape()
            elif boolean_op == BooleanOp.REMOVE:
                s = BRepAlgoAPI_Cut(body1, body2).Shape()
            elif boolean_op == BooleanOp.INTERSECT:
                s = BRepAlgoAPI_Common(body1, body2).Shape()
            else:
                raise NotImplemented(f"Boolean operation {boolean_op} is not implemented.")
        # # ======= Visualized DEBUG =======
        # from OCC.Display.SimpleGui import init_display
        # display, start_display, add_menu, add_function_to_menu = init_display()
        # from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
        # color = Quantity_Color(0, 1, 0, Quantity_TOC_RGB)
        # display.DisplayShape(body1, color=color, transparency=0.4, update=True)
        # if boolean_type == OPERATION_TYPE_REMOVE:
        #     display.DisplayShape(body2, color=Quantity_Color(1, 0, 0, Quantity_TOC_RGB), transparency=0.4, update=True)
        # else:
        #     display.DisplayShape(body2, color=Quantity_Color(0, 1, 0, Quantity_TOC_RGB), transparency=0.4, update=True)
        # start_display()
        return s
