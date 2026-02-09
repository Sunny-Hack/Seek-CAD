import copy
import uuid
import numpy as np

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Pln, gp_Ax3
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire

from visualize.utils.occ_utils import get_bbox
from visualize.modules.Curves import CurveBase, Circle, Line, Arc, BSpline
from visualize.base.BaseVFeature import BaseVFeature
from visualize.macro import NORM_FACTOR
from visualize.utils.math_utils import denumericalize_unit_vector, numericalize_unit_vector


# --------------------------------------------------
# We would like to thank the authors (Rundi Wu, Chang Xiao and Changxi Zheng) of
# DeepCAD (https://arxiv.org/abs/2105.09492), as this code is partially adapted from their work.
# --------------------------------------------------

class Loop(BaseVFeature):
    """Sketch loop, a sequence of connected curves."""

    def __init__(self, all_curves):
        super().__init__("loop", None, "loop", None)
        self.curves = all_curves
        self.reorder()

    def reorder(self):
        """reorder by starting left most and counter-clockwise"""
        if len(self.curves) <= 1:
            return

        start_curve_idx = -1
        sx, sy = 10000, 10000
        # correct start-end point order
        if np.allclose(self.curves[0].start_point, self.curves[1].start_point) or \
                np.allclose(self.curves[0].start_point, self.curves[1].end_point):
            self.curves[0].reverse()

        # correct start-end point order and find left-most point
        for i, curve in enumerate(self.curves):
            if i < len(self.curves) - 1 and np.allclose(curve.end_point, self.curves[i + 1].end_point):
                self.curves[i + 1].reverse()
            if round(curve.start_point[0], 6) < round(sx, 6) or \
                    (round(curve.start_point[0], 6) == round(sx, 6) and round(curve.start_point[1], 6) < round(sy, 6)):
                start_curve_idx = i
                sx, sy, _ = curve.start_point

        self.curves = self.curves[start_curve_idx:] + self.curves[:start_curve_idx]

        # ensure mostly counter-clock wise
        if isinstance(self.curves[0], Circle) or isinstance(self.curves[-1], Circle):
            return
        start_vec = np.array(self.curves[0].direction())[:-1]
        end_vec = np.array(self.curves[-1].direction(from_start=False))[:-1]
        if np.cross(end_vec, start_vec) <= 0:
            for curve in self.curves:
                curve.reverse()
            self.curves.reverse()

    def to_deepcad_json(self):
        loop_json = {
            "is_outer": True,
            "profile_curves": [
            ]
        }

        for child in self.curves:
            loop_json['profile_curves'].append(child.to_deepcad_json())
        return loop_json

    def back2json(self):
        loop_dict = {
            "loop_curves": []
        }
        for curve in self.curves:
            loop_dict["loop_curves"].append(curve.back2json())
        return loop_dict

    @staticmethod
    def from_dict(loops):
        all_curves = [CurveBase.construct_curve_from_dict(item) for item in loops['loop_curves']]
        this_loop = Loop(all_curves)
        return this_loop

    @property
    def bbox(self):
        """compute bounding box (min/max points) of the sketch"""
        all_points = np.concatenate([child.bbox for child in self.curves], axis=0)
        return np.stack([np.min(all_points, axis=0), np.max(all_points, axis=0)], axis=0)

    def create_loop(self, plane):
        topo_wire = BRepBuilderAPI_MakeWire()
        occ_edges_list = TopTools_ListOfShape()
        # =====================================================================
        # from OCC.Display.SimpleGui import init_display
        # display, start_display, add_menu, add_function_to_menu = init_display()
        # topo_edge = self.curves[0].create_curve_3D()
        # display.DisplayShape(topo_edge, color="red", update=True)
        # if len(self.curves) > 1:
        #     topo_edge = self.curves[1].create_curve_3D()
        #     display.DisplayShape(topo_edge, color="green", update=True)
        # for curve in self.curves[2:]:
        #     topo_edge = curve.create_curve_3D()
        #     display.DisplayShape(topo_edge, color="blue", update=True)
        # start_display()
        # =====================================================================
        for curve in self.curves:
            topo_edge = curve.create_curve_3D(plane)
            occ_edges_list.Append(topo_edge)
        topo_wire.Add(occ_edges_list)
        return topo_wire.Wire()

    def get_code(self, param: dict):
        ref_ids = param.get("ref_ids", set())
        indent = 4
        _code = f"Loop()\n"
        if len(self.curves) == 1:
            assert isinstance(self.curves[0], Circle)
            center = self.curves[0].center
            radius = self.curves[0].radius
            # _code += f"{' ' * indent}.center({center[0]},{center[1]})\n"
            _code += f"{' ' * indent}.moveTo({center[0]},{center[1]})\n"
            _code += f"{' ' * indent}.circle({radius})"
            if self.curves[0].id in ref_ids:
                _code += f".curveTag(\"{self.curves[0].id}\")"
            _code += "\n"
        else:
            s_p = self.curves[0].start_point
            _code += f"{' ' * indent}.moveTo({s_p[0]},{s_p[1]})\n"
            for curve in self.curves:
                assert not isinstance(curve, Circle)
                if isinstance(curve, Line):
                    e_p = curve.end_point
                    _code += f"{' ' * indent}.lineTo({e_p[0]},{e_p[1]})"
                elif isinstance(curve, Arc):
                    m_p = curve.midpoint
                    e_p = curve.end_point
                    _code += f"{' ' * indent}.threePointArc(({m_p[0]},{m_p[1]}), ({e_p[0]},{e_p[1]}))"
                elif isinstance(curve, BSpline):
                    inter_ps = curve.interpolated_points[1:]
                    _code += f"{' ' * indent}.splineTo("
                    for p in inter_ps:
                        _code += f"({p[0]},{p[1]}), "
                    _code = _code[:-2] + ")"
                e_p_id = curve.end_point_id
                curve_id = curve.id
                if e_p_id in ref_ids:
                    _code += f".pointTag(\"{e_p_id}\")"
                if curve_id in ref_ids:
                    _code += f".curveTag(\"{curve_id}\")"
                _code += "\n"
        return _code.strip()


class Face(BaseVFeature):
    """Sketch profile，a closed region formed by one or more loops.
    The outermost loop is placed at first."""

    def __init__(self, profile_id, all_loops):
        super().__init__(profile_id, profile_id, "face", None)
        self.id = profile_id
        self.loops = all_loops
        self.__reorder()

    @staticmethod
    def from_dict(profile_id, loops):
        all_loops = [Loop.from_dict(item) for item in loops]
        return Face(profile_id, all_loops)

    def to_deepcad_json(self):
        face_json = {
            "loops": [],
            "properties": {}
        }
        for loop in self.loops:
            face_json['loops'].append(loop.to_deepcad_json())
        return face_json

    def back2json(self) -> dict:
        """Back to origin json representation"""
        profile_dict = {
            "loops": []
        }
        for loop in self.loops:
            loop_dict = {
                "loop_curves": []
            }
            for curve in loop.curves:
                loop_dict["loop_curves"].append(curve.back2json())
            profile_dict["loops"].append(loop_dict)
        return profile_dict

    def __reorder(self):
        if len(self.loops) <= 1:
            return
        all_loops_bbox_min = np.stack([loop.bbox[0] for loop in self.loops], axis=0).round(6)
        ind = np.lexsort(all_loops_bbox_min.transpose()[[1, 0]])
        self.loops = [self.loops[i] for i in ind]

    def create_profile(self, plane):
        origin = gp_Pnt(*plane["origin"])
        normal = gp_Dir(*plane["normal"])
        x_axis = gp_Dir(*plane["x"])
        gp_face = gp_Pln(gp_Ax3(origin, normal, x_axis))

        all_loops = [loop.create_loop(plane) for loop in self.loops]
        # =====================================================================
        # from OCC.Display.SimpleGui import init_display
        # display, start_display, add_menu, add_function_to_menu = init_display()
        # display.DisplayShape(all_loops[0], color="red", update=True)
        # for loop in all_loops[1:]:
        #     display.DisplayShape(loop, color="blue", update=True)
        # start_display()
        # =====================================================================
        topo_face = BRepBuilderAPI_MakeFace(gp_face, all_loops[0])
        for loop in all_loops[1:]:
            topo_face.Add(loop.Reversed())
        return topo_face.Face()

    def get_code(self, param: dict):
        ref_ids = param.get("ref_ids", set())
        profile_name = param.get("profile_name", f"p{self.id}")
        if self.id in ref_ids:
            _res = f"{profile_name} = Profile(tag=\"{self.id}\")\n"
        else:
            _res = f"{profile_name} = Profile()\n"
        for loop in self.loops:
            _res += f"{profile_name}.addLoop({loop.get_code(param)}\n)\n"
        return _res.strip()


class Sketch(BaseVFeature):
    def __init__(self, feat_name, feat_id, feat_type, faces: list[Face], plane: dict):
        super().__init__(feat_name, feat_id, feat_type, parameters=None)
        self.faces = faces
        self.plane = plane

    def to_deepcad_json(self):
        def array_to_xyz_dict(np_arr):
            return {
                "x": np_arr[0],
                "y": np_arr[1],
                "z": np_arr[2],
            }

        normal = denumericalize_unit_vector(copy.deepcopy(self.plane["normal"]))
        x_axis = denumericalize_unit_vector(copy.deepcopy(self.plane["x"]))
        y_axis = np.cross(normal, x_axis)
        transform = {
            "origin": array_to_xyz_dict(self.plane["origin"]),
            "y_axis": array_to_xyz_dict(y_axis),
            "x_axis": array_to_xyz_dict(x_axis),
            "z_axis": array_to_xyz_dict(normal)
        }

        sketch_json = {
            "transform": transform,
            "type": "Sketch",
            "name": str(uuid.uuid4()),
            "profiles": {},
            "reference_plane": {}
        }

        for p in self.faces:
            sketch_json['profiles'][str(uuid.uuid4())] = p.to_deepcad_json()
        return sketch_json

    @staticmethod
    def from_dict(feature):
        all_faces = []
        for p_id, v in feature["profiles"].items():
            all_faces.append(Face.from_dict(p_id, v["loops"]))
        return Sketch(feature["name"],
                      feature["id"],
                      feature["type"],
                      all_faces,
                      copy.deepcopy(feature["plane"]))

    def create_sketch(self, return_union=False, plane=None):
        if plane is None:
            plane = self.plane
        plane = copy.deepcopy(plane)

        plane["normal"] = denumericalize_unit_vector(plane["normal"])
        plane["x"] = denumericalize_unit_vector(plane["x"])

        all_faces = []
        for profile in self.faces:
            all_faces.append(profile.create_profile(plane))

        if return_union:
            union_face = all_faces[0]
            for face in all_faces[1:]:
                union_face = BRepAlgoAPI_Fuse(union_face, face).Shape()
            return union_face

        return all_faces

    def find_id(self, the_id):
        plane = copy.deepcopy(self.plane)
        # ======= denormalize plane ========
        plane["normal"] = denumericalize_unit_vector(plane["normal"])
        plane["x"] = denumericalize_unit_vector(plane["x"])
        # ==================================
        for profile in self.faces:
            if profile.id == the_id:
                return profile.create_profile(plane)
            for loop in profile.loops:
                for curve in loop.curves:
                    topo_ds = curve.find_topo_ds_by_id(the_id, plane)
                    if topo_ds is not None:
                        return topo_ds
        return None

    @property
    def bbox(self):
        skt = self.create_sketch(return_union=True)
        return get_bbox(skt)

    def normalize(self, size=1.0):
        """(1)normalize the shape into unit cube (-1~1). """
        # scale = size / np.max(np.abs(self.bbox))
        scale = size * NORM_FACTOR / np.max(np.abs(self.bbox))
        self.transform_param(np.array([0, 0, 0]), scale)

    def transform_param(self, translation, scale):
        # 1. transform plane
        self.plane["origin"] = (np.array(self.plane["origin"]) + translation) * scale
        self.plane["origin"] = self.plane["origin"].tolist()

        # 2. transform all curves in this sketch
        for face in self.faces:
            for loop in face.loops:
                for curve in loop.curves:
                    curve.transform_param(translation, scale)

    def numericalize(self, n=256):
        # 1. transform plane
        self.plane["origin"] = ((np.array(self.plane["origin"]) * (n / 2))
                                .round()
                                .clip(min=-n / 2, max=n / 2)
                                .astype(int)
                                .tolist())
        self.plane["normal"] = numericalize_unit_vector(self.plane["normal"])
        self.plane["x"] = numericalize_unit_vector(self.plane["x"])

        # 2. transform all curves in this sketch
        for profile in self.faces:
            for loop in profile.loops:
                for curve in loop.curves:
                    curve.numericalize(n)

    def back2json(self) -> dict:
        """Back to origin json representation"""
        orig_json = {
            "name": self.feat_name,
            "id": self.feat_id,
            "type": "sketch",
            "profiles": {},
            "plane": self.plane
        }
        for face in self.faces:
            profile_dict = face.back2json()
            orig_json["profiles"][face.id] = profile_dict
        return orig_json

    def get_code(self, param: dict):
        SERPair_idx = param.get("index", 0)
        sketch_name = param.get("sketch_name", f"sk{SERPair_idx}")
        _res = ""
        if "desc" in param:
            _res += f"# {param['desc'][self.feat_id]['sketch_summary']}\n"
            if "sketch_code" in param["desc"][self.feat_id]:
                _res += f"{param['desc'][self.feat_id]['sketch_code'].strip()}\n"
                return _res
        profile_names = [f"p{SERPair_idx}_{i}" for i in range(len(self.faces))]
        _res += f"{sketch_name} = Sketch(plane={self.plane})\n"
        for idx, profile in enumerate(self.faces):
            param["profile_name"] = profile_names[idx]
            _res += f"{profile.get_code(param)}\n"

        _res += f"{sketch_name}.addProfile({','.join(profile_names)})"
        return _res
