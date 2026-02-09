import copy
import uuid
from abc import ABC, abstractmethod

import numpy as np
from OCC.Core.BRep import BRep_Tool
from OCC.Core.Geom import Geom_BSplineCurve
from OCC.Core.GeomAPI import GeomAPI_Interpolate
from OCC.Core.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
from OCC.Core.TopoDS import TopoDS_Edge
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Circ, gp_Ax2
from OCC.Core.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                     BRepBuilderAPI_MakeVertex)
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.GC import GC_MakeArcOfCircle
from OCC.Core.TColgp import TColgp_Array1OfPnt, TColgp_HArray1OfPnt
from visualize.utils.occ_utils import get_bbox
from visualize.macro import DUMMY_PLANE


# --------------------------------------------------
# We would like to thank the authors (Rundi Wu, Chang Xiao and Changxi Zheng) of
# DeepCAD (https://arxiv.org/abs/2105.09492), as this code is partially adapted from their work.
# --------------------------------------------------

class CurveBase(ABC):
    """Base class for curve. All types of curves shall inherit from this."""

    def __init__(self, topo_ds_edge, curve_id, start_point_id=None, end_point_id=None,
                 start_point=None, end_point=None):
        self.topo_ds_edge_from_2d_coord = topo_ds_edge
        self.id = curve_id
        self.start_point_id = start_point_id
        self.end_point_id = end_point_id
        self.start_point = start_point
        self.end_point = end_point

    @abstractmethod
    def create_curve_3D(self, plane):
        pass

    @abstractmethod
    def transform_param(self, translate, scale, numericalize=False):
        """linear transformation"""
        pass

    @abstractmethod
    def numericalize(self, n=256):
        """quantize curve parameters into integers"""
        pass

    @abstractmethod
    def back2json(self):
        """get minimal json representation of the curve"""
        pass

    @abstractmethod
    def to_deepcad_json(self):
        pass

    @staticmethod
    def from_dict(stat):
        """construct curve from json data"""
        raise NotImplementedError

    @property
    def bbox(self):
        """compute bounding box of the curve"""
        return get_bbox(self.topo_ds_edge_from_2d_coord)

    def reverse(self):
        """reverse the curve direction"""
        raise NotImplementedError

    def direction(self, from_start=True):
        """return a vector indicating the curve direction"""
        raise NotImplementedError

    @staticmethod
    def local2global(point: list, plane):
        origin = np.array(plane["origin"])
        x_axis = np.array(plane["x"])
        y_axis = np.cross(plane["normal"], plane["x"])
        g_point = point[0] * x_axis + point[1] * y_axis + origin
        g_point = g_point.tolist()
        return g_point

    @staticmethod
    def construct_curve_from_dict(curve):
        if curve["type"] == "Line2D":
            return Line.from_dict(curve)
        elif curve["type"] == "Circle2D":
            return Circle.from_dict(curve)
        elif curve["type"] == "Arc2D":
            return Arc.from_dict(curve)
        elif curve["type"] == "BSplineCurve2D":
            return BSpline.from_dict(curve)
        else:
            raise NotImplementedError("Curve type not supported yet: {}".format(curve["type"]))

    @staticmethod
    def create_line(start_point, end_point):
        start_point = gp_Pnt(*start_point)
        end_point = gp_Pnt(*end_point)
        topo_edge = BRepBuilderAPI_MakeEdge(start_point, end_point)
        return topo_edge.Edge()

    @staticmethod
    def create_arc(start_point, end_point, midpoint):
        start_point = gp_Pnt(*start_point)
        end_point = gp_Pnt(*end_point)
        mid_point = gp_Pnt(*midpoint)

        arc = GC_MakeArcOfCircle(start_point, mid_point, end_point).Value()
        topo_edge = BRepBuilderAPI_MakeEdge(arc)
        return topo_edge.Edge()

    @staticmethod
    def create_circle(center, plane, radius):
        center = gp_Pnt(*center)
        axis = gp_Dir(*plane["normal"])
        gp_circle = gp_Circ(gp_Ax2(center, axis), abs(float(radius)))
        topo_edge = BRepBuilderAPI_MakeEdge(gp_circle)
        return topo_edge.Edge()

    @staticmethod
    def create_bspline(control_points, knots, degree, is_periodic):
        global_control_points = [gp_Pnt(*p) for p in control_points]
        oc_control_points = TColgp_Array1OfPnt(1, len(global_control_points))
        for i, p in enumerate(global_control_points):
            oc_control_points.SetValue(i + 1, p)
        unique_knots = []
        multiplicities = []
        for knot in knots:
            if knot not in unique_knots:
                unique_knots.append(knot)
                multiplicities.append(knots.count(knot))
        oc_knots = TColStd_Array1OfReal(1, len(unique_knots))
        for i, knot in enumerate(unique_knots):
            oc_knots.SetValue(i + 1, knot)
        oc_multiplicities = TColStd_Array1OfInteger(1, len(multiplicities))
        for i, mult in enumerate(multiplicities):
            oc_multiplicities.SetValue(i + 1, mult)
        bspline_curve = Geom_BSplineCurve(oc_control_points, oc_knots, oc_multiplicities,
                                          int(degree), is_periodic)
        topo_edge = BRepBuilderAPI_MakeEdge(bspline_curve)
        edge = topo_edge.Edge()
        return edge

    @staticmethod
    def get_bspline_interpolated_points(bspline_edge: TopoDS_Edge, knots: list[float]):
        curve_handle, first_param, last_param = BRep_Tool.Curve(bspline_edge)
        _interpolated_points = []
        for knot in knots:
            p = gp_Pnt()
            curve_handle.D0(knot, p)
            _interpolated_points.append(p)
        interpolated_points = []
        pre_p = _interpolated_points[0]
        interpolated_points.append([pre_p.X(), pre_p.Y(), pre_p.Z()])

        for p in _interpolated_points[1:]:
            if p.IsEqual(pre_p, 1e-5):
                pre_p = p
                continue
            interpolated_points.append([p.X(), p.Y(), p.Z()])
            pre_p = p
        return interpolated_points

    @staticmethod
    def create_interpolate_spline(points):
        array = TColgp_HArray1OfPnt(1, len(points))
        for i, p in enumerate(points):
            array.SetValue(i + 1, gp_Pnt(*p))
        interpolator = GeomAPI_Interpolate(array, False, 1e-6)
        interpolator.Perform()
        curve = interpolator.Curve()
        return BRepBuilderAPI_MakeEdge(curve).Edge()

    def find_topo_ds_by_id(self, the_id, plane):
        if self.id == the_id:
            return self.create_curve_3D(plane)
        if self.start_point is not None:
            if the_id == self.start_point_id:
                p = self.start_point
            elif the_id == self.end_point_id:
                p = self.end_point
            else:
                return None
            g_p = CurveBase.local2global(p, plane)
            return BRepBuilderAPI_MakeVertex(gp_Pnt(*g_p)).Vertex()
        return None


class Line(CurveBase):
    def __init__(self, start_point, end_point, start_point_id, end_point_id, curve_id):
        curve_topo_ds = CurveBase.create_line(start_point, end_point)
        super(Line, self).__init__(curve_topo_ds, curve_id, start_point_id, end_point_id, start_point, end_point)

    def __str__(self):
        return f"Line({self.start_point}, {self.end_point})"

    def back2json(self):
        return {
            "type": "Line2D",
            "id": self.id,
            "start_point": self.start_point.tolist()[:2],
            "end_point": self.end_point.tolist()[:2],
            "start_point_id": self.start_point_id,
            "end_point_id": self.end_point_id,
        }

    def to_deepcad_json(self):
        return {
            "type": "Line3D",
            "start_point": {
                "x": float(self.start_point[0]),
                "y": float(self.start_point[1]),
                "z": 0
            },
            "curve": str(uuid.uuid4()),
            "end_point": {
                "x": float(self.end_point[0]),
                "y": float(self.end_point[1]),
                "z": 0
            }
        }

    @staticmethod
    def from_dict(curve):
        start_point = np.array(curve["start_point"] + [0.0])
        end_point = np.array(curve["end_point"] + [0.0])
        start_point_id = curve["start_point_id"]
        end_point_id = curve["end_point_id"]
        curve_id = curve["id"]
        return Line(start_point, end_point, start_point_id, end_point_id, curve_id)

    def create_curve_3D(self, plane):
        return CurveBase.create_line(CurveBase.local2global(self.start_point, plane),
                                     CurveBase.local2global(self.end_point, plane))

    def transform_param(self, translate, scale, numericalize=False):
        self.start_point = (self.start_point + translate) * scale
        self.end_point = (self.end_point + translate) * scale
        if numericalize:
            self.start_point = self.start_point.round()
            self.end_point = self.end_point.round()

    def numericalize(self, n=256):
        self.start_point = (self.start_point * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.end_point = (self.end_point * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)

    def reverse(self):
        self.start_point, self.end_point = self.end_point, self.start_point
        self.start_point_id, self.end_point_id = self.end_point_id, self.start_point_id

    def direction(self, from_start=True):
        return self.end_point - self.start_point


class Arc(CurveBase):
    def __init__(self, start_point, end_point, start_point_id, end_point_id, curve_id, center, radius,
                 mid_point, start_angle=None, end_angle=None, ref_vec=None):
        self.center = center
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.midpoint = mid_point
        self.ref_vec = ref_vec
        curve_topo_ds = CurveBase.create_arc(start_point, end_point, mid_point)
        super(Arc, self).__init__(curve_topo_ds, curve_id, start_point_id, end_point_id, start_point, end_point)
        self.degrees = self.get_degrees()

    # @property
    # def degrees(self):
    #     sweep_angle = max(abs(self.start_angle - self.end_angle), 1)
    #     return np.rad2deg(sweep_angle)

    def get_degrees(self):
        the_edge = self.topo_ds_edge_from_2d_coord
        curve = BRepAdaptor_Curve(the_edge)
        sweep_angle = max(abs(curve.LastParameter() - curve.FirstParameter()), 1)
        return np.rad2deg(sweep_angle)

    @property
    def clockwise(self):
        end_point = copy.deepcopy(self.end_point[:2])
        start_point = copy.deepcopy(self.start_point[:2])
        midpoint = copy.deepcopy(self.midpoint[:2])
        s2e = end_point - start_point
        s2m = midpoint - start_point
        sign = np.cross(s2m, s2e) < 0  # clockwise
        return sign

    def get_ref_vec(self):
        sweep_angle = self.degrees
        clock_sign = 0 if self.clockwise else 1
        s2e_vec = self.end_point - self.start_point
        if np.linalg.norm(s2e_vec) == 0:
            return ValueError("Start and end points are the same, cannot create an arc.")
        radius = (np.linalg.norm(s2e_vec) / 2) / np.sin(sweep_angle / 2)
        s2e_mid = (self.start_point + self.end_point) / 2
        vertical = np.cross(s2e_vec, [0, 0, 1])
        vertical = vertical / np.linalg.norm(vertical)
        if clock_sign == 0:
            vertical = -vertical
        center_point = s2e_mid - vertical * (radius * np.cos(sweep_angle / 2))

        if clock_sign == 0:
            ref_vec = self.end_point - center_point
        else:
            ref_vec = self.start_point - center_point
        ref_vec = ref_vec / np.linalg.norm(ref_vec)
        return ref_vec

    def create_curve_3D(self, plane):
        return CurveBase.create_arc(CurveBase.local2global(self.start_point, plane),
                                    CurveBase.local2global(self.end_point, plane),
                                    CurveBase.local2global(self.midpoint, plane))

    def transform_param(self, translate, scale, numericalize=False):
        self.start_point = (self.start_point + translate) * scale
        self.midpoint = (self.midpoint + translate) * scale
        self.end_point = (self.end_point + translate) * scale
        if self.center is not None:
            self.center = (self.center + translate) * scale
        self.radius = abs(self.radius * scale)
        if numericalize:
            self.start_point = self.start_point.round()
            self.midpoint = self.midpoint.round()
            self.end_point = self.end_point.round()
            self.center = self.center.round()
            self.radius = round(self.radius)

    def numericalize(self, n=256):
        # print(f"before: start_point: {self.start_point}, midpoint:{self.midpoint}, end_point: {self.end_point}")
        self.start_point = (self.start_point * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.midpoint = (self.midpoint * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.end_point = (self.end_point * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        # print(f"after: start_point: {self.start_point}, midpoint:{self.midpoint}, end_point: {self.end_point}")
        if self.center is not None:
            self.center = (self.center * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.radius = (self.radius * (n / 2)).round().clip(min=0, max=n).astype(int)
        self.degrees = max(int(self.degrees), 1)

    def back2json(self):
        return {
            "type": "Arc2D",
            "id": self.id,
            "start_point": self.start_point.tolist()[:2],
            "midpoint": self.midpoint.tolist()[:2],
            "end_point": self.end_point.tolist()[:2],
            "start_point_id": self.start_point_id,
            "end_point_id": self.end_point_id,
        }

    def to_deepcad_json(self):
        if self.ref_vec is None:
            self.ref_vec = self.get_ref_vec()
        return {
            "center_point": {
                "x": float(self.center[0]),
                "y": float(self.center[1]),
                "z": 0.0
            },
            "normal": {
                "y": 0.0,
                "x": 0.0,
                "z": 1.0
            },
            "end_point": {
                "x": float(self.end_point[0]),
                "y": float(self.end_point[1]),
                "z": 0.0
            },
            "start_angle": self.start_angle,
            "curve": str(uuid.uuid4()),
            "end_angle": self.end_angle,
            "radius": float(self.radius),
            "type": "Arc3D",
            "start_point": {
                "x": float(self.start_point[0]),
                "y": float(self.start_point[1]),
                "z": 0.0
            },
            "reference_vector": {
                "x": float(self.ref_vec[0]),
                "y": float(self.ref_vec[1]),
                "z": 0.0
            }
        }

    def reverse(self):
        self.start_point, self.end_point = self.end_point, self.start_point
        self.start_point_id, self.end_point_id = self.end_point_id, self.start_point_id

    def __str__(self):
        return "Arc: start({}), end({})".format(self.start_point.round(4), self.end_point.round(4))

    def direction(self, from_start=True):
        if from_start:
            return self.midpoint - self.start_point
        else:
            return self.end_point - self.midpoint

    @staticmethod
    def from_dict(curve):
        start_point = np.array(curve["start_point"] + [0.0])
        end_point = np.array(curve["end_point"] + [0.0])
        start_point_id = curve["start_point_id"]
        end_point_id = curve["end_point_id"]
        curve_id = curve["id"]
        center = np.array(curve["center_point"] + [0.0]) if "center_point" in curve else None
        radius = curve["radius"] if "radius" in curve else None
        start_angle = curve["start_angle"] if "start_angle" in curve else None
        end_angle = curve["end_angle"] if "end_angle" in curve else None
        mid_point = np.array(curve["midpoint"] + [0.0])
        ref_vec = np.array(curve["ref_vec"] + [0.0]) if "ref_vec" in curve else None
        return Arc(start_point, end_point, start_point_id, end_point_id, curve_id, center, radius,
                   mid_point, start_angle, end_angle, ref_vec)


class Circle(CurveBase):
    def __init__(self, center, radius, curve_id):
        self.center = center
        self.radius = radius
        curve_topo_ds = CurveBase.create_circle(center, DUMMY_PLANE, radius)
        super(Circle, self).__init__(curve_topo_ds, curve_id)

    def create_curve_3D(self, plane):
        return CurveBase.create_circle(CurveBase.local2global(self.center, plane), plane, self.radius)

    def transform_param(self, translate, scale, numericalize=False):
        self.center = (self.center + translate) * scale
        self.radius = abs(self.radius * scale)
        if numericalize:
            self.center = self.center.round()
            self.radius = round(self.radius)

    def numericalize(self, n=256):
        self.center = (self.center * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.radius = int((self.radius * (n / 2)).round().clip(min=0, max=n))

    def back2json(self):
        return {
            "type": "Circle2D",
            "id": self.id,
            "center_point": self.center.tolist()[:2],
            "radius": self.radius,
        }

    def to_deepcad_json(self):
        return {
            "center_point": {
                "x": float(self.center[0]),
                "y": float(self.center[1]),
                "z": 0.0
            },
            "type": "Circle3D",
            "radius": self.radius,
            "curve": str(uuid.uuid4()),
            "normal": {
                "y": 0.0,
                "x": 0.0,
                "z": 1.0
            }
        }

    def __str__(self):
        return "Circle: center({}), radius({})".format(self.center.round(4), round(self.radius, 4))

    def reverse(self):
        pass

    def direction(self, from_start=True):
        return self.center - np.array([self.center[0] - self.radius, self.center[1], self.center[2]])

    @staticmethod
    def from_dict(curve):
        center = np.array(curve["center_point"] + [0.0])
        radius = curve["radius"]
        curve_id = curve["id"]
        return Circle(center, radius, curve_id)


class BSpline(CurveBase):
    def __init__(self, start_point, end_point, start_point_id, end_point_id, curve_id, is_periodic,
                 interpolated_points):
        self.is_periodic = is_periodic
        self.interpolated_points = interpolated_points
        curve_topo_ds = CurveBase.create_interpolate_spline(interpolated_points)
        super(BSpline, self).__init__(curve_topo_ds, curve_id, start_point_id, end_point_id, start_point,
                                      end_point)

    def create_curve_3D(self, plane):
        global_interpolated_points = []
        for p in self.interpolated_points:
            g_p = CurveBase.local2global(p, plane)
            global_interpolated_points.append(g_p)
        return CurveBase.create_interpolate_spline(global_interpolated_points)

    def transform_param(self, translate, scale, numericalize=False):
        self.start_point = (self.start_point + translate) * scale
        self.end_point = (self.end_point + translate) * scale
        new_interpolated_points = []
        for p in self.interpolated_points:
            new_p = (np.array(p) + translate) * scale
            new_interpolated_points.append(new_p.tolist())
        self.interpolated_points = new_interpolated_points
        if numericalize:
            self.start_point = self.start_point.round()
            self.end_point = self.end_point.round()
            new_interpolated_points = []
            for p in self.interpolated_points:
                new_p = np.array(p).round()
                new_interpolated_points.append(new_p.tolist())
            self.interpolated_points = new_interpolated_points

    def numericalize(self, n=256):
        self.start_point = (self.start_point * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        self.end_point = (self.end_point * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
        numericalized_interpolated_points = []
        for p in self.interpolated_points:
            p = (np.array(p) * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
            numericalized_interpolated_points.append(p.tolist())
        self.interpolated_points = numericalized_interpolated_points

    def back2json(self):
        return {
            "type": "BSplineCurve2D",
            "id": self.id,
            "start_point": self.start_point.tolist()[:2],
            "end_point": self.end_point.tolist()[:2],
            "start_point_id": self.start_point_id,
            "end_point_id": self.end_point_id,
            "interpolated_points": [p[:2] for p in self.interpolated_points],
        }

    def to_deepcad_json(self):
        # DeepCAD does not support spline curve
        pass

    def reverse(self):
        self.start_point, self.end_point = self.end_point, self.start_point
        self.start_point_id, self.end_point_id = self.end_point_id, self.start_point_id
        self.interpolated_points = self.interpolated_points[::-1]

    @staticmethod
    def from_dict(curve):
        start_point = np.array(curve["start_point"] + [0.0])
        end_point = np.array(curve["end_point"] + [0.0])
        start_point_id = curve["start_point_id"]
        end_point_id = curve["end_point_id"]
        curve_id = curve["id"]
        is_periodic = curve["is_periodic"] if "is_periodic" in curve else None
        interpolated_points = curve["interpolated_points"]
        if interpolated_points[0] != start_point[:2].tolist():
            interpolated_points = interpolated_points[::-1]
        return BSpline(start_point, end_point, start_point_id, end_point_id, curve_id, is_periodic,
                       interpolated_points=[arr + [0.0] for arr in interpolated_points])

    def direction(self, from_start=True):
        return self.end_point - self.start_point
