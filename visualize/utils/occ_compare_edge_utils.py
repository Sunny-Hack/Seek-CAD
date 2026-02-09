from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.GeomAbs import GeomAbs_Line, GeomAbs_Circle, GeomAbs_BSplineCurve, GeomAbs_CurveType
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Edge
from OCC.Core.gp import gp_Pnt


def curve_type(an_edge: TopoDS_Edge):
    c = BRepAdaptor_Curve(an_edge)
    return c.GetType()


def compare_line_by_points(s1: gp_Pnt, e1: gp_Pnt, s2: gp_Pnt, e2: gp_Pnt, tol=1e-3):
    return ((s1.IsEqual(s2, tol) and e1.IsEqual(e2, tol)) or
            (s1.IsEqual(e2, tol) and e1.IsEqual(s2, tol)))


def curve_param(an_edge: TopoDS_Edge, edge_type: GeomAbs_CurveType):
    curve = BRepAdaptor_Curve(an_edge)
    if edge_type == GeomAbs_Line:
        _, first_param, last_param = BRep_Tool.Curve(an_edge)
        start_point = curve.Value(first_param)
        end_point = curve.Value(last_param)
        return start_point, end_point
    elif edge_type == GeomAbs_Circle:  # Arc or Circle
        # gp_circle = curve.Circle()
        # center = gp_circle.Location()
        # radius = gp_circle.Radius()
        # start_angle = curve.FirstParameter()
        # end_angle = curve.LastParameter()
        # return center, radius, start_angle, end_angle
        res = BRep_Tool.Curve(an_edge)
        first_param = res[-2]
        last_param = res[-1]
        start_point = curve.Value(first_param)
        mid_point = curve.Value((first_param + last_param) / 2)
        end_point = curve.Value(last_param)
        return start_point, mid_point, end_point
    elif edge_type == GeomAbs_BSplineCurve:
        the_spline = curve.BSpline()
        start_point = the_spline.StartPoint()
        end_point = the_spline.EndPoint()
        return start_point, end_point
    else:
        raise NotImplementedError(f"curve type {edge_type} not supported")


def is_equal(edge1: TopoDS_Edge, edge2: TopoDS_Edge, tol=1e-3):
    c_type = curve_type(edge1)
    if c_type != curve_type(edge2):
        return False
    else:
        if c_type in [GeomAbs_Line, GeomAbs_BSplineCurve]:
            s1, e1 = curve_param(edge1, c_type)
            s2, e2 = curve_param(edge2, c_type)
            return compare_line_by_points(s1, e1, s2, e2, tol)
        elif c_type == GeomAbs_Circle:
            s1, m1, e1 = curve_param(edge1, c_type)
            s2, m2, e2 = curve_param(edge2, c_type)
            return compare_line_by_points(s1, e1, s2, e2, tol) and m1.IsEqual(m2, tol)
        else:
            raise NotImplementedError(f"curve type {c_type} not supported")


def is_equal_any(edge: TopoDS_Edge, any_edges_in, tol=1e-4):
    """
    This function uses a non-strict approach to determine whether two edge equal.
    """
    res = False
    for _edge in any_edges_in:
        if is_equal(_edge, edge, tol):
            res = True
    return res


def is_edges_intersected(edge1: TopoDS_Edge, edge2: TopoDS_Edge) -> bool:
    sec = BRepAlgoAPI_Section(edge1, edge2)
    sec.Build()
    comm_shape = sec.Shape()
    explorer = TopExp_Explorer(comm_shape, TopAbs_EDGE)
    if explorer.More():
        return True
    return False


def is_edges_intersected_any(edge: TopoDS_Edge, any_edges_in) -> bool:
    res = False
    for _edge in any_edges_in:
        if is_edges_intersected(_edge, edge):
            res = True
    return res

# def print_edge(an_edge: TopoDS_Edge):
#     curve = BRepAdaptor_Curve(an_edge)
#     curve_type = curve.GetType()
#     if curve_type == GeomAbs_Line:
#         print("Identified Line Geometry")
#         curve_handle, first_param, last_param = BRep_Tool.Curve(an_edge)
#         start_point_curve = curve.Value(first_param)
#         end_point_curve = curve.Value(last_param)
#         print("Start Point (Curve):", (start_point_curve.X(), start_point_curve.Y(), start_point_curve.Z()))
#         print("End Point (Curve):", (end_point_curve.X(), end_point_curve.Y(), end_point_curve.Z()))
#     elif curve_type == GeomAbs_Circle:
#         print("Identified Circle Geometry")
#         gp_circle = curve.Circle()
#         center = gp_circle.Location()
#         radius = gp_circle.Radius()
#         print(f"--> Center: ({center.X()}, {center.Y()}, {center.Z()})")
#         print(f"--> Radius: {radius}")
#         curve_handle, first_param, last_param = BRep_Tool.Curve(an_edge)
#         start_point = gp_Pnt()
#         curve_handle.D0(first_param, start_point)
#         end_point = gp_Pnt()
#         curve_handle.D0(last_param, end_point)
#         mid_param = (first_param + last_param) / 2.0
#         mid_point = gp_Pnt()
#         curve_handle.D0(mid_param, mid_point)
#         print(f"--> start_point: ({start_point.X()}, {start_point.Y()}, {start_point.Z()})")
#         print(f"--> mid_point: ({mid_point.X()}, {mid_point.Y()}, {mid_point.Z()})")
#         print(f"--> end_point: ({end_point.X()}, {end_point.Y()}, {end_point.Z()})")
#         start_angle = curve.FirstParameter()
#         end_angle = curve.LastParameter()
#         print(f"Start Angle: {start_angle}, End Angle: {end_angle}")
#     elif curve_type == GeomAbs_BSplineCurve:
#         print("Identified BSpline Curve Geometry")
#     else:
#         print(f"Edge type {curve_type} recognition not implemented")
