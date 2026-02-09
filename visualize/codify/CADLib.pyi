from abc import ABC
from typing import List, Tuple, Union, Optional, Dict, Self


class Loop:
    def __init__(self) -> None: ...
    def moveTo(self, x: float, y: float) -> Self: ...  # Define start point of this loop
    def lineTo(self, x: float, y: float) -> Self: ...  # Draw straight line to point
    def threePointArc(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> Self: ...  # Arc to p2 via p1
    def splineTo(self, *p: Tuple[float, float]) -> Self: ...  # B-spline through given points
    def close(self) -> Self: ...  # Close loop (make a line back to start point)
    def circle(self, radius: float) -> Self: ...  # Draw circle with center at current point
    def pointTag(self, tag: str) -> Self: ...  # assign tag to the current point
    def curveTag(self, tag: str) -> Self: ...  # assign tag to the current curve


class Profile:
    def __init__(self, tag: Optional[str] = None) -> None: ...  # Create a face with optional ID for reference
    def addLoop(self, *loops: Loop) -> None: ...  # Add one or more loops to the face


class Sketch:
    def __init__(self, plane: Dict) -> None: ...
    def addProfile(self, *profiles: Profile) -> None: ...


class CADShape(ABC):
    def __init__(self) -> None: ...
    def Chamfer(self, width: float, entities: List[Dict]) -> Self: ...
    def Fillet(self, radius: float, entities: List[Dict]) -> Self: ...
    def Shell(self, thickness: float, entities: List[Dict]) -> Self: ...
    def union(self, shape: CADShape) -> Self: ...
    def cut(self, shape: CADShape) -> Self: ...
    def intersect(self, shape: CADShape) -> Self: ...


class Extrude(CADShape):
    def __init__(self, sketch: Sketch, distance: Union[float, Tuple[float, float]]) -> None: ...


class Revolve(CADShape):
    def __init__(self, sketch: Sketch, axis: Dict, angle: Union[float, Tuple[float, float]]) -> None: ...
