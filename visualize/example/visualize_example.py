import json
import sys
import os
from pathlib import Path

from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Display.SimpleGui import init_display
from OCC.Extend.DataExchange import write_step_file

sys.path.append(str(Path(os.path.abspath(os.path.dirname(__file__))).parent.parent))
from visualize.codify.code2json import code2json
from visualize.sequence import CADSequence

display, start_display, add_menu, add_function_to_menu = init_display()

"""
Example of visualization from JSON file, and how to export the created shape to STEP file and image file, as well as how to quantize the geometry and export back to JSON file. 
"""

# example json file
json_path = "./00000066.json"

with open(json_path, 'r', encoding="utf-8") as fp:
    data = json.load(fp)
# create shape
cad_seq = CADSequence.from_dict(data, _clean_shape=True, validate=True, strict=False, debug=False)
s = cad_seq.create_CAD()
BRepMesh_IncrementalMesh(s, 0.0001, True, 0.1, True)
display.DisplayShape(s, transparency=0, update=True)
display.FitAll()
display.ZoomFactor(0.9)
start_display()

# export to STEP file
write_step_file(s, "./00000066.step")

# export to image file
display.View.Dump("./00000066.png")

# quantize if you needed
# WARNING: we do not guarantee the quantization will not cause any geometry illegality, please use it with caution and check the exported geometry after quantization
cad_seq.normalize()
cad_seq.numericalize(n=256)

# export back to JSON file (note this JSON is quantized as we applied quantization to `cad_seq`)
export_json = cad_seq.back2json()
with open("./00000066_export.json", "w", encoding="utf-8") as fp:
    json.dump(export_json, fp, indent=4)

# we also support export to DeepCAD json format for the convenience of using DeepCAD-related code
deepcad_format_json = cad_seq.to_deepcad_json()
with open("./00000066_deepcad_format.json", "w", encoding="utf-8") as fp:
    json.dump(deepcad_format_json, fp, indent=4)

# convert the sequence of operations to code format
code = cad_seq.get_code()
with open("./00000066_code.py", "w", encoding="utf-8") as fp:
    fp.write(code)

# we provide a function to directly convert the code back to JSON format, which then can be used to create the shape and visualize, export, etc.
json_from_code = code2json(code)
with open("./00000066_code2json.json", "w", encoding="utf-8") as fp:
    json.dump(json_from_code, fp, indent=4)

# visualize the shape created from code
display, start_display, add_menu, add_function_to_menu = init_display()
cad_seq = CADSequence.from_dict(json_from_code, _clean_shape=True, validate=True, strict=False, debug=False)
s = cad_seq.create_CAD()
BRepMesh_IncrementalMesh(s, 0.0001, True, 0.1, True)
display.DisplayShape(s, transparency=0, update=True)
display.FitAll()
display.ZoomFactor(0.9)
start_display()