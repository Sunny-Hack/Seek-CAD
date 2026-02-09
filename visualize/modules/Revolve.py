import math
from visualize.modules import Sketch
import numpy as np
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Ax1, gp_Trsf, gp_Pnt, gp_Dir

from visualize.utils.math_utils import numericalize_unit_vector, denumericalize_unit_vector, fmt_list, format_offset
from visualize.base.SketchBasedVFeature import SketchBasedVFeature
from visualize.macro import CapType


class Revolve(SketchBasedVFeature):
    def __init__(self, feat_name, feat_id, feat_type, parameters):
        super().__init__(feat_name, feat_id, feat_type, parameters)
        self.axis = self.parameters['axis']
        self.angle_one = self.parameters['angleOne']
        self.angle_two = self.parameters['angleTwo']

    @staticmethod
    def from_dict(feature):
        return Revolve(feature["name"],
                       feature["id"],
                       feature["type"],
                       feature["parameters"])

    def _op(self, s: TopoDS_Shape) -> TopoDS_Shape:
        # ======= denormalize direction ========
        direction = denumericalize_unit_vector(self.axis["direction"])
        # ==================================
        axis = gp_Ax1(gp_Pnt(*self.axis["point"]), gp_Dir(*direction))
        if self.angle_one != 0 and self.angle_two != 0:
            trans = gp_Trsf()
            trans.SetRotation(axis, -1 * math.radians(self.angle_two))
            transform = BRepBuilderAPI_Transform(s, trans)
            s = transform.Shape()
            return BRepPrimAPI_MakeRevol(s,
                                         axis,
                                         math.radians(abs(self.angle_one) + abs(self.angle_two))
                                         ).Shape()
        angle = self.angle_one if self.angle_one != 0 else (-1 * self.angle_two)
        return BRepPrimAPI_MakeRevol(s, axis, math.radians(angle)).Shape()

    def op(self, sketch: Sketch) -> TopoDS_Shape:
        s = sketch.create_sketch(return_union=True)
        return self._op(s)

    def transform(self, s: TopoDS_Shape, cap_type: CapType, param=None) -> TopoDS_Shape:
        # ======= denormalize direction ========
        direction = denumericalize_unit_vector(self.axis["direction"])
        # ==================================
        axis = gp_Ax1(gp_Pnt(*self.axis["point"]), gp_Dir(*direction))
        trans = gp_Trsf()
        assert cap_type in [CapType.START, CapType.END]
        if cap_type == CapType.START:
            if self.angle_two == 0:
                return s
            trans.SetRotation(axis, -1 * math.radians(self.angle_two))
        else:  # CapType.END
            if self.angle_one == 0:
                return s
            trans.SetRotation(axis, math.radians(self.angle_one))
        translator = BRepBuilderAPI_Transform(s, trans)
        return translator.Shape()

    def transform_param(self, translation, scale):
        self.axis["point"] = (np.array(self.axis["point"]) + translation) * scale
        self.axis["point"] = self.axis["point"].tolist()

    def numericalize(self, n=256):
        self.angle_one = int(self.angle_one)
        self.angle_two = int(self.angle_two)
        self.axis["point"] = np.array(self.axis["point"])
        self.axis["point"] = (self.axis["point"] * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.axis["point"] = self.axis["point"].tolist()
        self.axis["direction"] = numericalize_unit_vector(self.axis["direction"])

    def back2json(self):
        return {
            "name": self.feat_name,
            "id": self.feat_id,
            "type": self.feat_type,
            # "sketch_id": self.sketch_id,
            "parameters": {
                "bodyType": self.parameters["bodyType"],
                "operationType": self.parameters["operationType"],
                "revolveType": self.parameters["revolveType"],
                "axis": {
                    "point": self.axis["point"],
                    "direction": self.axis["direction"]
                },
                "angleOne": self.angle_one,
                "angleTwo": self.angle_two
            }
        }

    def to_deepcad_json(self):
        pass

    def get_code(self, param: dict):
        SERPair_idx = param.get("index", 0)
        shape_name = param.get("shape_name", f"shape{SERPair_idx}")
        sketch_name = param.get("sketch_name", f"sk{SERPair_idx}")
        # if SERPair_idx == 0:
        _res = ""
        if "desc" in param:
            _res += f"# {param['desc'][self.feat_id]['desc']}\n"
        if self.angle_one != 0 and self.angle_two != 0:
            _res += f"{shape_name} = {self.feat_type.capitalize()}({sketch_name}, axis={self.axis}, angle=({self.angle_one}, {self.angle_two}))"
        else:
            angle = self.angle_one if self.angle_one != 0 else (-1.0 * self.angle_two)
            _res += f"{shape_name} = {self.feat_type.capitalize()}({sketch_name}, axis={self.axis}, angle={angle})"
        return _res
