from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCC.Core.TopoDS import TopoDS_Shape

from visualize.base.RefiningVFeature import RefiningVFeature


class Fillet(RefiningVFeature):
    def __init__(self, feat_name, feat_id, feat_type, entities, parameters, strict, debug):
        super().__init__(feat_name, feat_id, feat_type, entities, parameters, strict=strict, debug=debug)
        self.radius = self.parameters["radius"]

    @staticmethod
    def from_dict(feature, strict=False, debug=True):
        return Fillet(feature["name"],
                      feature["id"],
                      feature["type"],
                      feature["entities"],
                      feature["parameters"], strict, debug)

    def _op(self, s: TopoDS_Shape, entities: dict[str, list[TopoDS_Shape]]) -> TopoDS_Shape:
        # =====================================================================
        if self.debug:
            from OCC.Display.SimpleGui import init_display
            display, start_display, add_menu, add_function_to_menu = init_display()
            from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
            display.DisplayShape(s, color=Quantity_Color(0, 0, 0, Quantity_TOC_RGB), transparency=0.5, update=True)
            cnt = 0
            for edge in self.locate_edges(s, entities["edges"], self.strict):
                display.DisplayShape(edge, color=Quantity_Color(1, 0, 0, Quantity_TOC_RGB), update=True)
                cnt += 1
            for edge in self.locate_edges_from_faces(s, entities["faces"], self.strict):
                display.DisplayShape(edge, color=Quantity_Color(1, 0, 0, Quantity_TOC_RGB), update=True)
                cnt += 1
            print("=====================================================================")
            print(f"         {self.feat_name}: Number of op edges: {cnt}")
            print("=====================================================================")
            start_display()
        # =====================================================================

        fillet = BRepFilletAPI_MakeFillet(s)
        for edge in self.locate_edges(s, entities["edges"], self.strict):
            fillet.Add(self.radius, edge)
        for edge in self.locate_edges_from_faces(s, entities["faces"], self.strict):
            fillet.Add(self.radius, edge)
        return fillet.Shape()

    def transform_param(self, translation, scale):
        self.radius *= scale

    def numericalize(self, n=256):
        self.radius = float((self.radius * (n / 2)).round().clip(min=0, max=n).astype(int))
        self.radius = max(self.radius, 1.0)

    def back2json(self):
        return {
            "name": self.feat_name,
            "id": self.feat_id,
            "type": self.feat_type,
            "entities": self.entities,
            "parameters": {
                "radius": self.radius
            }
        }

    def to_deepcad_json(self):
        pass
