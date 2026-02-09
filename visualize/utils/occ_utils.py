import numpy as np
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.GProp import GProp_GProps
from OCC.Core.ShapeFix import ShapeFix_Shape
from OCC.Core.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.V3d import V3d_DirectionalLight, V3d_TypeOfOrientation
from OCC.Display.SimpleGui import init_display


def clean_shape(shape):
    fixer = ShapeFix_Shape(shape)
    fixer.Perform()
    fixed = fixer.Shape()

    unifier = ShapeUpgrade_UnifySameDomain(fixed, True, True, True)
    unifier.Build()
    return unifier.Shape()


def get_bbox(shape: TopoDS_Shape):
    bounding_box = Bnd_Box()
    brepbndlib.Add(shape, bounding_box)
    x_min, y_min, z_min, x_max, y_max, z_max = bounding_box.Get()
    min_corner = np.array([x_min, y_min, z_min])
    max_corner = np.array([x_max, y_max, z_max])
    return np.stack([min_corner, max_corner], axis=0)


def set_light(display):
    light = V3d_DirectionalLight()
    light.SetDirection(V3d_TypeOfOrientation(5))
    light.SetIntensity(0.8)
    display.View.SetLightOn(light)


def is_shape_valid(shape):
    analyzer = BRepCheck_Analyzer(shape)
    return analyzer.IsValid()


def get_mass(shape: TopoDS_Shape):
    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    mass = props.Mass()
    return mass


def show_shape(shape):
    display, start_display, add_menu, add_function_to_menu = init_display()
    set_light(display)
    display.DisplayShape(shape, update=True)
    display.View.TriedronErase()
    start_display()
