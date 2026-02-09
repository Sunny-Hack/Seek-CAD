import uuid

import numpy as np
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Dir

from visualize.macro import CapType
from visualize.base.SketchBasedVFeature import SketchBasedVFeature
from visualize.modules.Sketch import Sketch


class Extrude(SketchBasedVFeature):
    def __init__(self, feat_name, feat_id, feat_type, parameters):
        super().__init__(feat_name, feat_id, feat_type, parameters)
        self.depth_one = self.parameters['depthOne']
        self.depth_two = self.parameters['depthTwo']
        assert self.depth_one != 0 or self.depth_two != 0, "Extrude depth_one and depth_two cannot both be zero."

    @staticmethod
    def from_dict(feature):
        return Extrude(feature["name"],
                       feature["id"],
                       feature["type"],
                       feature["parameters"])

    def __get_gp_dir_one(self, ext_normal):
        if self.depth_one != 0:
            return gp_Vec(gp_Dir(*ext_normal)).Multiplied(self.depth_one)
        return None

    def __get_gp_dir_two(self, ext_normal):
        if self.depth_two != 0:
            return gp_Vec(gp_Dir(*ext_normal).Reversed()).Multiplied(self.depth_two)
        return None

    def _op(self, s: TopoDS_Shape, normal: list[float]):
        ext_normal = np.array(normal)
        ext_normal = ext_normal / np.linalg.norm(ext_normal)

        if self.depth_one != 0 and self.depth_two != 0:
            trans = gp_Trsf()
            trans.SetTranslation(gp_Vec(*(ext_normal * -1 * self.depth_two)))
            translator = BRepBuilderAPI_Transform(s, trans)
            s = translator.Shape()
            ext_dir = gp_Vec(gp_Dir(*ext_normal)).Multiplied(abs(self.depth_two) + abs(self.depth_one))
            return BRepPrimAPI_MakePrism(s, ext_dir).Shape()
        ext_dir = self.__get_gp_dir_one(ext_normal) if self.depth_one != 0 else self.__get_gp_dir_two(ext_normal)
        return BRepPrimAPI_MakePrism(s, ext_dir).Shape()

    def op(self, sketch: Sketch) -> TopoDS_Shape:
        s = sketch.create_sketch(return_union=True)
        return self._op(s, sketch.plane["normal"])

    def transform(self, s: TopoDS_Shape, cap_type: CapType, param=None) -> TopoDS_Shape:
        ext_normal = np.array(param.get("normal", [0.0, 0.0, 1.0]))
        ext_normal = ext_normal / np.linalg.norm(ext_normal)
        trans = gp_Trsf()
        assert cap_type in [CapType.START, CapType.END]
        if cap_type == CapType.START:
            if self.depth_two == 0:
                return s
            trans.SetTranslation(gp_Vec(*(ext_normal * -1 * self.depth_two)))
        else:  # CapType.END
            if self.depth_one == 0:
                return s
            trans.SetTranslation(gp_Vec(*(ext_normal * self.depth_one)))
        translator = BRepBuilderAPI_Transform(s, trans)
        return translator.Shape()

    def transform_param(self, translation, scale):
        self.depth_one *= scale
        self.depth_two *= scale

    def numericalize(self, n=256):
        orig_d_one, orig_d_two = self.depth_one, self.depth_two
        self.depth_one = (self.depth_one * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.depth_one = float(self.depth_one)
        if self.depth_one == 0 and orig_d_one != 0:
            self.depth_one = 1.0 if orig_d_one > 0 else -1.0
        self.depth_two = (self.depth_two * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.depth_two = float(self.depth_two)
        if self.depth_two == 0 and orig_d_two != 0:
            self.depth_two = 1.0 if orig_d_two > 0 else -1.0

    def back2json(self):
        return {
            "name": self.feat_name,
            "id": self.feat_id,
            "type": self.feat_type,
            # "sketch_id": self.sketch_id,
            "parameters": {
                "bodyType": self.parameters["bodyType"],
                "operationType": self.parameters["operationType"],
                "endBound": self.parameters["endBound"],
                "depthOne": self.depth_one,
                "depthTwo": self.depth_two
            }
        }

    def to_deepcad_json(self):
        if self.parameters["operationType"] == "NEW":
            op = "NewBodyFeatureOperation"
        elif self.parameters["operationType"] == "ADD":
            op = "JoinFeatureOperation"
        elif self.parameters["operationType"] == "REMOVE":
            op = "CutFeatureOperation"
        else:
            op = "IntersectFeatureOperation"
        if self.depth_two != 0:
            if self.depth_one == 0:
                extent_type = "OneSideFeatureExtentType"
                self.depth_one = -self.depth_two
                self.depth_two = 0
            else:
                if self.depth_one == self.depth_two:
                    extent_type = "SymmetricFeatureExtentType"
                else:
                    extent_type = "TwoSidesFeatureExtentType"
        else:
            extent_type = "OneSideFeatureExtentType"
        ext_json = {
            "extent_two": {
                "distance": {
                    "role": "AgainstDistance",
                    "type": "ModelParameter",
                    "name": "none",
                    "value": self.depth_two
                },
                "type": "DistanceExtentDefinition",
                "taper_angle": {
                    "role": "Side2TaperAngle",
                    "type": "ModelParameter",
                    "name": "none",
                    "value": 0.0
                }
            },
            "name": str(uuid.uuid4()),
            "extent_one": {
                "distance": {
                    "role": "AlongDistance",
                    "type": "ModelParameter",
                    "name": "none",
                    "value": self.depth_one
                },
                "type": "DistanceExtentDefinition",
                "taper_angle": {
                    "role": "TaperAngle",
                    "type": "ModelParameter",
                    "name": "none",
                    "value": 0.0
                }
            },
            "extent_type": extent_type,
            "operation": op,
            "start_extent": {
                "type": "ProfilePlaneStartDefinition"
            },
            "type": "ExtrudeFeature",
            "profiles": []
        }
        return ext_json

    def get_code(self, param: dict):
        SERPair_idx = param.get("index", 0)
        shape_name = param.get("shape_name", f"shape{SERPair_idx}")
        sketch_name = param.get("sketch_name", f"sk{SERPair_idx}")
        _res = ""
        if "desc" in param:
            _res += f"# {param['desc'][self.feat_id]['desc']}\n"

        if self.depth_one != 0 and self.depth_two != 0:
            _res += f"{shape_name} = {self.feat_type.capitalize()}({sketch_name}, distance=({self.depth_one}, {self.depth_two}))"
        else:
            _depth = self.depth_one if self.depth_one != 0 else -1.0 * self.depth_two
            _res += f"{shape_name} = {self.feat_type.capitalize()}({sketch_name}, distance={_depth})"
        return _res