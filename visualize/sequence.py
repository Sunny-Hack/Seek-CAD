from visualize.base.RefiningVFeature import RefiningVFeature
from visualize.macro import *
from visualize.modules.Chamfer import Chamfer
from visualize.modules.Extrude import *
from visualize.modules.Fillet import Fillet
from visualize.modules.Revolve import Revolve
from visualize.modules.Shell import Shell
from visualize.modules.Sketch import Sketch
from visualize.base.SketchBasedVFeature import SketchBasedVFeature
from visualize.utils.occ_utils import clean_shape, get_bbox, is_shape_valid, get_mass, show_shape


class TripleWrapper:
    def __init__(self, skt: Sketch, skt_op: SketchBasedVFeature, refines: list[RefiningVFeature], _clean_shape):
        self.skt = skt
        self.skt_op = skt_op
        self.refines = refines
        self._clean_shape = _clean_shape
        self.boolean_type = BooleanOp[self.skt_op.parameters["operationType"]]

    def build(self) -> TopoDS_Shape:
        s = self.skt_op.op(self.skt)
        for r in self.refines:
            s = r.op(s, self.skt, self.skt_op)
        if self._clean_shape:
            s = clean_shape(s)
        return s


class CADSequence(object):
    def __init__(self, seq, _clean_shape, validate=True, strict=False, debug=False):
        self.seq = seq
        self._clean_shape = _clean_shape
        self.validate = validate
        self.strict = strict
        self.debug = debug
        self.triple_wrappers = self.__get_triple_wrappers()

    @property
    def bbox(self):
        s = self.create_CAD()
        return get_bbox(s)

    @staticmethod
    def from_dict(json_data, _clean_shape=True, validate=True, strict=False, debug=False):
        seq = []
        for item in json_data["sequence"]:
            feature = json_data["features"][item["feature_id"]]
            if item["type"] == "sketch":
                sketch = Sketch.from_dict(feature)
                seq.append(sketch)
            if item["type"] == "extrude":
                extrude = Extrude.from_dict(feature)
                seq.append(extrude)
            elif item["type"] == "revolve":
                revolve = Revolve.from_dict(feature)
                seq.append(revolve)
            elif item["type"] == "chamfer":
                chamfer = Chamfer.from_dict(feature, strict, debug)
                seq.append(chamfer)
            elif item["type"] == "fillet":
                fillet = Fillet.from_dict(feature, strict, debug)
                seq.append(fillet)
            elif item["type"] == "shell":
                shell = Shell.from_dict(feature, strict, debug)
                seq.append(shell)
        return CADSequence(seq, _clean_shape, validate, strict, debug)

    def __check_shape(self, shape):
        if self.validate:
            if not is_shape_valid(shape):
                raise ValueError("The created shape is invalid.")

    def __check_shape_by_mass(self, shape):
        if self.validate:
            mass = get_mass(shape)
            if mass == 0.0:
                raise ValueError("The created shape has zero mass, which is invalid.")
            # print(f"{mass=}")

    def __get_triple_wrappers(self):
        _triples = []
        assert self.seq[0].feat_type == "sketch", "the first feature must be a sketch"
        triple = [self.seq[0]]
        for feat in self.seq[1:]:
            if feat.feat_type == "sketch":
                _triples.append(triple)
                triple = [feat]
            else:
                triple.append(feat)
        _triples.append(triple)

        pairs = []
        for p in _triples:
            if len(p) <= 1:
                continue
            pairs.append(p)

        wrappers = []
        for p in pairs:
            refines = []
            if len(p) > 2:
                refines = p[2:]
            wrapper = TripleWrapper(p[0], p[1], refines, self._clean_shape)
            wrappers.append(wrapper)
        if len(wrappers) == 0:
            raise ValueError("No valid pairs found in the sequence.")
        return wrappers

    def create_CAD(self):
        shape = self.triple_wrappers[0].build()
        if self.debug:
            show_shape(shape)
        self.__check_shape(shape)
        for wrapper in self.triple_wrappers[1:]:
            local_shape = wrapper.build()
            if self.debug:
                show_shape(local_shape)
            self.__check_shape(local_shape)
            shape = SketchBasedVFeature.op_boolean(shape, local_shape, wrapper.boolean_type)
            if shape is None:
                raise ValueError("The created shape is invalid.")
            if self.debug:
                show_shape(shape)

        self.__check_shape(shape)
        self.__check_shape_by_mass(shape)
        # if self.validate:
        #     if not is_shape_valid(shape):
        #         raise ValueError("The created shape is invalid.")
        return shape

    def normalize(self, size=1.0):
        """(1)normalize the shape into unit cube (-1~1). """
        # scale = size / np.max(np.abs(self.bbox))
        scale = size * NORM_FACTOR / np.max(np.abs(self.bbox))
        self.transform_param(np.array([0, 0, 0]), scale)

    def transform_param(self, translation: np.array, scale):
        assert len(translation) == 3 and isinstance(translation, np.ndarray)
        for item in self.seq:
            item.transform_param(translation, scale)

    def numericalize(self, n=256):
        """
        - Global quantities (e.g. origin quantization), local quantities (e.g. curve quantization),
          and scalar values follow the same quantization strategy as sketch positions.
            pos = (pos * (n / 2)).round().clip(min=-n/2, max=n/2).astype(int)
        - Scalar quantization: in general, 1.0 is mapped to 128.
          * Special case:
            extrude_length is normalized to (-1, 1) and can be negative:
                depth = (depth * (n / 2)).round().clip(min=-n/2, max=n/2).astype(int)
          * Other scalar values are always non-negative:
                size = (size * (n / 2)).round().clip(min=0, max=n).astype(int)
        - Angles are handled separately:
                angle = angle.round().clip(min=-360, max=360).astype(int)
        - Coordinates: range [-1, 1] → [-128, 128]
        - Scalars:     range [0, 2]  → [0, 256]
        """
        for item in self.seq:
            item.numericalize(n)

    def back2json(self):
        _res = {
            "features": {},
            "sequence": [],
        }
        for idx, feat in enumerate(self.seq):
            json_feat = feat.back2json()
            _res["features"][feat.feat_id] = json_feat
            _res["sequence"].append({
                "index": idx,
                "type": feat.feat_type,
                "name": feat.feat_name,
                "feature_id": feat.feat_id
            })
        return _res

    def get_ssr_triples(self):
        res = []
        assert self.seq[0].feat_type == "sketch"
        triples = [self.seq[0]]
        for feat in self.seq[1:]:
            if feat.feat_type == "sketch":
                res.append(triples)
                triples = [feat]
            else:
                triples.append(feat)
        res.append(triples)
        return res

    @staticmethod
    def get_all_ref_ids(features: list) -> set:
        _ids = set()
        for feat in features:
            if "entities" in feat.__dict__:
                for e in feat.__dict__.get("entities"):
                    _ids.add(e["referenceId"])
        return _ids

    @staticmethod
    def get_code_ssr(SSR, param: dict):
        """get code representation"""
        if "index" not in param:
            param["index"] = 0
        param["ref_ids"] = CADSequence.get_all_ref_ids(SSR)
        if "shape_name" not in param:
            param["shape_name"] = f"shape{param['index']}"
        _code = ""
        for feat in SSR:
            _code += feat.get_code(param)
            _code += "\n"
        return _code.strip().replace("'", "\"")

    def get_code(self, param={}):
        SSRs = self.get_ssr_triples()
        return self.get_code_sub(SSRs, param)

    @staticmethod
    def get_code_sub(SSRs, param=None):
        """get code representation"""
        if param is None:
            param = {}
        _code = ""
        for idx, SSR in enumerate(SSRs):
            param["index"] = idx
            param["shape_name"] = f"shape{idx}"
            _code += CADSequence.get_code_ssr(SSR, param)
            _code += "\n"
            if idx > 0:
                op_type = SSR[1].parameters["operationType"]
                if op_type == "REMOVE":
                    boolean_name = "cut"
                elif op_type == "INTERSECT":
                    boolean_name = "intersect"
                else:
                    boolean_name = "union"
                _code += f"shape0 = shape0.{boolean_name}(shape{idx})\n"
            _code = _code.strip() + "\n\n"

        _code = (_code.strip() +
                 "\n" +
                 "# End of code")

        return _code.replace("'", "\"")

    def to_deepcad_json(self):
        bbox = self.bbox.tolist()
        max_corner, min_corner = bbox[0], bbox[1]
        cad_json = {
            "entities": {},
            "properties": {
                "bounding_box": {
                    "max_point": {
                        "x": max_corner[0],
                        "y": max_corner[1],
                        "z": max_corner[2]
                    },
                    "type": "BoundingBox3D",
                    "min_point": {
                        "x": min_corner[0],
                        "y": min_corner[1],
                        "z": min_corner[2]
                    }
                }},
            "sequence": []
        }
        idx = 0
        for triple in self.triple_wrappers:
            sketch = triple.skt
            extrude = triple.skt_op

            if extrude.feat_type == "revolve":
                continue

            skt_json = sketch.to_deepcad_json()
            skt_id = skt_json["name"]

            ext_json = extrude.to_deepcad_json()
            ext_id = ext_json["name"]
            cad_json["sequence"].append({
                "index": idx,
                "type": "Sketch",
                "entity": skt_id
            })
            idx += 1
            cad_json["entities"][skt_id] = skt_json

            cad_json["sequence"].append({
                "index": idx,
                "type": "ExtrudeFeature",
                "entity": ext_id
            })
            idx += 1
            cad_json["entities"][ext_id] = ext_json
        return cad_json
