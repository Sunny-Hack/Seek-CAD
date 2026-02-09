import numpy as np


def format_offset(val):
    if val == 0:
        return "0"
    text = f"{val:.2f}"
    text = text.rstrip('0').rstrip('.') if '.' in text else text
    return text


def fmt_list(lst):
    return "[" + ", ".join(format_offset(v) for v in lst) + "]"


def numericalize_unit_vector(vec, n=256):
    vec = np.array(vec)
    vec = vec / np.linalg.norm(vec)
    vec = (vec * (n / 2)).round().clip(min=-n / 2, max=n / 2).astype(int)
    return vec.tolist()


def denumericalize_unit_vector(vec, return_np=False):
    vec = np.array(vec)
    vec = vec / np.linalg.norm(vec)
    if return_np:
        return vec
    return vec.tolist()
