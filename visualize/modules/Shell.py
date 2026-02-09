from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeThickSolid
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Core.TopoDS import TopoDS_Shape

from visualize.base.RefiningVFeature import RefiningVFeature


class Shell(RefiningVFeature):
    def __init__(self, feat_name, feat_id, feat_type, entities, parameters, strict, debug):
        super().__init__(feat_name, feat_id, feat_type, entities, parameters, strict=strict, debug=debug)
        self.thickness = self.parameters["thickness"]

    @staticmethod
    def from_dict(feature, strict=False, debug=True):
        return Shell(feature["name"],
                     feature["id"],
                     feature["type"],
                     feature["entities"],
                     feature["parameters"], strict, debug)

    def _op(self, s: TopoDS_Shape, entities: dict[str, list[TopoDS_Shape]]) -> TopoDS_Shape:
        faces = TopTools_ListOfShape()
        for face in self.locate_faces(s, entities["faces"]):
            faces.Append(face)

        # =====================================================================
        if self.debug:
            from OCC.Display.SimpleGui import init_display
            display, start_display, add_menu, add_function_to_menu = init_display()
            from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
            display.DisplayShape(s, color=Quantity_Color(0, 0, 0, Quantity_TOC_RGB), transparency=0.5, update=True)
            cnt = 0
            for face in self.locate_faces(s, entities["faces"]):
                display.DisplayShape(face, color=Quantity_Color(1, 0, 0, Quantity_TOC_RGB), update=True)
                cnt += 1
            print("=====================================================================")
            print(f"         {self.feat_name}: Number of op edges: {cnt}")
            print("=====================================================================")
            start_display()
        # =====================================================================

        shell = BRepOffsetAPI_MakeThickSolid()
        shell.MakeThickSolidByJoin(
            s,
            faces,
            -1 * abs(self.thickness),
            1e-5,
            # BRepOffset_Skin,
            # True,
            # True,
            # GeomAbs_Arc,
            # True
        )
        s = shell.Shape()
        return s

    def transform_param(self, translation, scale):
        self.thickness *= scale

    def numericalize(self, n=256):
        self.thickness = float((self.thickness * (n / 2)).round().clip(min=0, max=n).astype(int))
        self.thickness = max(self.thickness, 1.0)

    def back2json(self):
        return {
            "name": self.feat_name,
            "id": self.feat_id,
            "type": self.feat_type,
            "entities": self.entities,
            "parameters": {
                "thickness": self.thickness
            }
        }

    def to_deepcad_json(self):
        pass
