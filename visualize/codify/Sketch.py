import uuid


class Loop(object):
    def __init__(self):
        self.curves = []
        self.start_point_tag = None
        self.last_point = None
        self.last_curve = None

    def pushCurve(self):
        if self.last_curve is not None:
            self.curves.append(self.last_curve)

    def moveTo(self, x, y):
        self.last_point = [x, y]
        return self

    def close(self):
        x, y = self.curves[0]["start_point"]
        return self.lineTo(x, y)

    def closeTo(self):
        return self.close()

    def lineTo(self, x, y):
        self.pushCurve()
        self.last_curve = {
            "type": "Line2D",
            "id": "dummy",
            "start_point": self.last_point,
            "end_point": [x, y],
            "start_point_id": "dummy",
            "end_point_id": "dummy"
        }
        self.last_point = [x, y]
        return self

    def threePointArc(self, p1: tuple, p2: tuple):
        self.pushCurve()
        self.last_curve = {
            "type": "Arc2D",
            "id": "dummy",
            "start_point": self.last_point,
            "end_point": [p2[0], p2[1]],
            "start_point_id": "dummy",
            "end_point_id": "dummy",
            "center_point": [0, 0],
            "radius": None,
            "start_angle": None,
            "end_angle": None,
            "midpoint": [p1[0], p1[1]]
        }
        self.last_point = [p2[0], p2[1]]
        return self

    def splineTo(self, *points):
        self.pushCurve()
        self.last_curve = {
            "type": "BSplineCurve2D",
            "id": "dummy",
            "start_point": self.last_point,
            "end_point": [points[-1][0], points[-1][1]],
            "start_point_id": "dummy",
            "end_point_id": "dummy",
            "is_periodic": False,
            "interpolated_points": [self.last_point]
        }
        for point in points:
            self.last_curve["interpolated_points"].append([point[0], point[1]])
        self.last_point = [points[-1][0], points[-1][1]]
        return self

    def circle(self, radius):
        self.pushCurve()
        self.last_curve = {
            "type": "Circle2D",
            "id": "dummy",
            "center_point": self.last_point,
            "radius": radius
        }
        self.last_point = None
        return self

    def pointTag(self, tag):
        if self.last_curve is None:
            self.start_point_tag = tag
        else:
            self.last_curve["end_point_id"] = tag
        return self

    def curveTag(self, tag):
        self.last_curve["id"] = tag
        return self

    def back2json(self):
        self.pushCurve()
        if self.start_point_tag is not None:
            self.curves[0]["start_point_id"] = self.start_point_tag
        return {
            "loop_curves": self.curves
        }


class Profile(object):
    def __init__(self, tag=None):
        self.tag = str(uuid.uuid4()) if tag is None else tag
        self.loops = []

    def addLoop(self, *loops):
        for loop in loops:
            self.loops.append(loop)

    def back2json(self):
        return {
            "loops": [loop.back2json() for loop in self.loops]
        }


class Sketch(object):
    def __init__(self, plane: dict):
        self.id = str(uuid.uuid4())
        self.plane = plane
        self.profiles = []

    def addProfile(self, *profiles):
        for profile in profiles:
            self.profiles.append(profile)

    def back2json(self):
        _sk = {
            "name": self.id,
            "id": self.id,
            "type": "sketch",
            "profiles": {},
            "plane": self.plane
        }
        for p in self.profiles:
            _sk["profiles"][p.tag] = p.back2json()
        return _sk
