from abc import ABC, abstractmethod
from visualize.codify.Sketch import *
from visualize.macro import BooleanOp

SER_PAIRS = []


def InitSERPairs():
    SER_PAIRS.clear()


class SketchBasedFeat(ABC):
    def __init__(self, sketch: Sketch, feat_type: str):
        SER_PAIRS.append(self)
        self.sketch = sketch
        self.feat_type = feat_type
        self.id = str(uuid.uuid4())
        self.refine_feats = []
        self.boolean_type = BooleanOp.NEW.value

    def union(self, shape: 'SketchBasedFeat'):
        shape.boolean_type = BooleanOp.ADD.value
        return self

    def cut(self, shape: 'SketchBasedFeat'):
        shape.boolean_type = BooleanOp.REMOVE.value
        return self

    def intersect(self, shape: 'SketchBasedFeat'):
        shape.boolean_type = BooleanOp.INTERSECT.value
        return self

    def Chamfer(self, width, entities):
        uid = str(uuid.uuid4())
        self.refine_feats.append({
            "name": uid,
            "id": uid,
            "type": "chamfer",
            "entities": entities,
            "parameters": {
                "width": width
            }
        })
        return self

    def Fillet(self, radius, entities):
        uid = str(uuid.uuid4())
        self.refine_feats.append({
            "name": uid,
            "id": uid,
            "type": "fillet",
            "entities": entities,
            "parameters": {
                "radius": radius
            }
        })
        return self

    def Shell(self, thickness, entities):
        uid = str(uuid.uuid4())
        self.refine_feats.append({
            "name": uid,
            "id": uid,
            "type": "shell",
            "entities": entities,
            "parameters": {
                "thickness": thickness
            }
        })
        return self

    @abstractmethod
    def getSketchBasedFeat(self) -> dict:
        pass

    def back2json(self):
        _res = [self.sketch.back2json(), self.getSketchBasedFeat()]
        for feat in self.refine_feats:
            _res.append(feat)
        return _res


class Extrude(SketchBasedFeat):
    def __init__(self, sketch: Sketch, distance):
        super().__init__(sketch, feat_type="extrude")
        if isinstance(distance, (int, float)):
            self.depthOne = distance
            self.depthTwo = 0.0
        elif isinstance(distance, (tuple, list)) and len(distance) == 2:
            self.depthOne = distance[0]
            self.depthTwo = distance[1]
        else:
            raise ValueError("Distance must be a number or a tuple/list of two numbers.")

    def getSketchBasedFeat(self) -> dict:
        return {
            "name": self.id,
            "id": self.id,
            "type": "extrude",
            "sketch_id": self.sketch.id,
            "parameters": {
                "bodyType": "SOLID",
                "operationType": self.boolean_type,
                "endBound": "BLIND",
                "depthOne": self.depthOne,
                "depthTwo": self.depthTwo
            }
        }


class Revolve(SketchBasedFeat):
    def __init__(self, sketch: Sketch, axis: dict, angle):
        super().__init__(sketch, feat_type="revolve")
        self.axis = axis
        if isinstance(angle, (int, float)):
            self.angleOne = angle
            self.angleTwo = 0.0
        elif isinstance(angle, (tuple, list)) and len(angle) == 2:
            self.angleOne = angle[0]
            self.angleTwo = angle[1]
        else:
            raise ValueError("Angle must be a number or a tuple/list of two numbers.")

    def getSketchBasedFeat(self) -> dict:
        return {
            "name": self.id,
            "id": self.id,
            "type": "revolve",
            "sketch_id": self.sketch.id,
            "parameters": {
                "bodyType": "SOLID",
                "operationType": self.boolean_type,
                "revolveType": "",
                "axis": self.axis,
                "angleOne": self.angleOne,
                "angleTwo": self.angleTwo
            }
        }
