from typing import Tuple

import numpy as np
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_CompCurve
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCC.Core.GeomAbs import GeomAbs_Plane, GeomAbs_SurfaceType
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.TopoDS import topods, TopoDS_Face, TopoDS_Edge
from OCC.Core.gp import gp_Pnt


def pnt2list(_, return_np_array=True):
    res = [_.X(), _.Y(), _.Z()]
    if return_np_array:
        return np.array(res)
    return res


def get_surface_type(face: TopoDS_Face) -> GeomAbs_SurfaceType:
    adaptor = BRepAdaptor_Surface(face)
    return adaptor.GetType()


def get_plane(face: TopoDS_Face, return_np_array=True):
    # face should be a plane
    adaptor = BRepAdaptor_Surface(face)
    assert adaptor.GetType() == GeomAbs_Plane
    gp_ax3 = adaptor.Plane().Position()
    origin = gp_ax3.Location()
    normal = gp_ax3.Direction()
    x = gp_ax3.XDirection()
    if return_np_array:
        return {
            "normal": pnt2list(normal, return_np_array),
            "origin": pnt2list(origin, return_np_array),
            "x": pnt2list(x, return_np_array),
        }
    else:
        return {
            "normal": normal,
            "origin": origin,
            "x": x,
        }


def is_faces_intersected_any(face: TopoDS_Face, any_faces_in) -> bool:
    """
    This function uses a non-strict approach to determine whether two faces intersect.
    """
    res = False
    for _face in any_faces_in:
        if is_faces_intersected(face, _face):
            res = True
    return res


def get_start_end_points(edge: TopoDS_Edge) -> Tuple[gp_Pnt, gp_Pnt]:
    curve_handle, first_param, last_param = BRep_Tool.Curve(edge)
    start_point = gp_Pnt()
    curve_handle.D0(first_param, start_point)
    end_point = gp_Pnt()
    curve_handle.D0(last_param, end_point)
    return start_point, end_point


def is_faces_intersected(
        face1: TopoDS_Face,
        face2: TopoDS_Face,
        tol: float = 1e-4,
) -> bool:
    """
    Return True if two faces intersect with a closed intersection curve.
    """

    t1 = get_surface_type(face1)
    t2 = get_surface_type(face2)
    if t1 != t2:
        return False

    if t1 == GeomAbs_Plane:
        plane1 = get_plane(face1)
        plane2 = get_plane(face2)

        # normals must be parallel
        if np.linalg.norm(np.cross(plane1["normal"], plane2["normal"])) > tol:
            return False

        # distance between planes
        if abs(np.dot(plane2["normal"], plane1["origin"] - plane2["origin"])) > tol:
            return False

    sec = BRepAlgoAPI_Section(face1, face2)
    sec.Build()
    if not sec.IsDone():
        return False

    comm_shape = sec.Shape()
    explorer = TopExp_Explorer(comm_shape, TopAbs_EDGE)

    edges = []
    while explorer.More():
        edges.append(topods.Edge(explorer.Current()))
        explorer.Next()

    if not edges:
        return False

    try:
        wire_maker = BRepBuilderAPI_MakeWire()
        for e in edges:
            wire_maker.Add(e)

        if wire_maker.IsDone():
            wire = wire_maker.Wire()
            if BRepAdaptor_CompCurve(wire).IsClosed():
                return True
    except Exception:
        pass

    vertices = []
    for edge in edges:
        p0, p1 = get_start_end_points(edge)
        vertices.extend([p0, p1])

    while vertices:
        v = vertices.pop(0)
        matched = False
        for i, u in enumerate(vertices):
            if u.IsEqual(v, tol):
                vertices.pop(i)
                matched = True
                break
        if not matched:
            return False

    return True
