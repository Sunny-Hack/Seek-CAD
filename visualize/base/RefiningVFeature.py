from abc import ABC, abstractmethod

from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Edge, TopoDS_Face, topods

from visualize.utils.occ_compare_edge_utils import is_equal_any, is_edges_intersected_any
from visualize.utils.occ_compare_face_utils import is_faces_intersected_any
from visualize.base.BaseVFeature import BaseVFeature
from visualize.modules.Sketch import Sketch
from visualize.macro import CapType
from visualize.base.SketchBasedVFeature import SketchBasedVFeature
from visualize.modules.Extrude import Extrude
from visualize.modules.Revolve import Revolve


class RefiningVFeature(BaseVFeature, ABC):
    def __init__(self, feat_name, feat_id, feat_type, entities, parameters, strict=False, debug=True):
        super().__init__(feat_name, feat_id, feat_type, parameters)
        self.entities = entities
        self.strict = strict
        self.debug = debug

    def resolve_entities_to_topods(self, skt: Sketch, skt_op: SketchBasedVFeature) -> dict[str, list[TopoDS_Shape]]:
        entities_topods = {"faces": [], "edges": []}
        for entity in self.entities:
            ref_id = entity["referenceId"]
            cap_type = CapType[entity["capType"]]
            topods = skt.find_id(ref_id)
            if topods is None:
                raise AssertionError(f"Reference Id `{ref_id}` can not found in the Sketch.")
            if cap_type == CapType.SWEPT:
                # this may result in TopoDS-related errors; see SketchBasedFeature._resolve_cap_entities().
                # such cases should be considered failures of model generation.
                if isinstance(skt_op, Extrude):
                    entity_topods = skt_op._op(topods, skt.plane["normal"])
                elif isinstance(skt_op, Revolve):
                    entity_topods = skt_op._op(topods)
                else:
                    raise ValueError(f"Unknown SketchBasedVFeature type: {type(skt_op)}")
            else:
                entity_topods = skt_op.transform(topods, cap_type, param={"normal": skt.plane["normal"]})

            if isinstance(entity_topods, TopoDS_Edge):
                entities_topods["edges"].append(entity_topods)
            elif isinstance(entity_topods, TopoDS_Face):
                entities_topods["faces"].append(entity_topods)
        return entities_topods

    @abstractmethod
    def _op(self, s: TopoDS_Shape, entities: dict[str, list[TopoDS_Shape]]) -> TopoDS_Shape:
        pass

    @staticmethod
    def locate_edges(s: TopoDS_Shape, ref_edges: list[TopoDS_Shape], strict: bool) -> list[TopoDS_Edge]:
        targets = []
        explorer = TopExp_Explorer(s, TopAbs_EDGE)
        while explorer.More():
            edge = topods.Edge(explorer.Current())
            explorer.Next()

            if edge.Orientation() and is_equal_any(edge, ref_edges):
                targets.append(edge)
            elif not strict and edge.Orientation() and is_edges_intersected_any(edge, ref_edges):
                targets.append(edge)
        return targets

    @staticmethod
    def locate_edges_from_faces(s: TopoDS_Shape, ref_faces: list[TopoDS_Shape], strict: bool) -> list[TopoDS_Edge]:
        ref_edges = []
        for face in ref_faces:
            explorer = TopExp_Explorer(face, TopAbs_EDGE)
            while explorer.More():
                edge = topods.Edge(explorer.Current())
                ref_edges.append(edge)
                explorer.Next()
        return RefiningVFeature.locate_edges(s, ref_edges, strict)

    @staticmethod
    def locate_faces(s: TopoDS_Shape, ref_faces: list[TopoDS_Shape]) -> list[TopoDS_Face]:
        targets = []
        explorer = TopExp_Explorer(s, TopAbs_FACE)
        while explorer.More():
            face = topods.Face(explorer.Current())
            explorer.Next()
            if is_faces_intersected_any(face, ref_faces):
                targets.append(face)
        return targets

    def op(self, s: TopoDS_Shape, skt: Sketch, skt_op: SketchBasedVFeature) -> TopoDS_Shape:
        entities = self.resolve_entities_to_topods(skt, skt_op)
        s = self._op(s, entities)
        return s

    def get_code(self, param: dict):
        shape_name = param.get("shape_name", "shape")
        entities = []
        for entity in self.entities:
            entities.append({
                "referenceId": entity["referenceId"],
                "capType": entity["capType"]
            })
        measure = None
        if self.feat_type == "fillet":
            measure = "radius"
        elif self.feat_type == "shell":
            measure = "thickness"
        elif self.feat_type == "chamfer":
            measure = "width"
        v = self.__dict__.get(measure)
        _res = ""
        if "desc" in param:
            _res += f"# {param['desc'][self.feat_id]['target']}\n"
        _res += f"{shape_name}.{self.feat_type.capitalize()}({measure}={v}, entities={entities})"
        return _res

    def get_all_ref_ids(self):
        ref_ids = set()
        for entity in self.entities:
            refer_id = entity["referenceId"]
            ref_ids.add(refer_id)
        return ref_ids

    def get_code_SSR(self, param: dict):
        type2ids = {}
        for entity in self.entities:
            cap_type = entity["capType"]
            refer_id = entity["referenceId"]
            if cap_type not in type2ids:
                type2ids[cap_type] = [refer_id]
            else:
                type2ids[cap_type].append(refer_id)
        entities = []

        for cap_type, refer_ids in type2ids.items():
            if len(refer_ids) == 0:
                continue
            entities.append({
                "referIds": refer_ids,
                "referType": cap_type
            })

        if len(entities) == 0:
            raise ValueError("No reference ids in Refine Feature.")

        measure = None
        if self.feat_type == "fillet":
            measure = "radius"
        elif self.feat_type == "shell":
            measure = "thickness"
        elif self.feat_type == "chamfer":
            measure = "width"
        else:
            raise NotImplemented(f"Feature type {self.feat_type} not supported.")

        v = self.__dict__.get(measure)

        _res = f"{self.feat_type.capitalize()}({measure}={v}, entities={entities})"
        return _res
