import json
import os

from pathlib import Path as P
from typing import Dict

import _jsonnet

from commodore.helpers import yaml_load, yaml_load_all, yaml_dump, yaml_dump_all
from commodore import __install_dir__

#  Returns content if worked, None if file not found, or throws an exception


def _try_path(basedir, rel):
    if not rel:
        raise RuntimeError("Got invalid filename (empty string).")
    if rel[0] == "/":
        full_path = P(rel)
    else:
        full_path = P(basedir) / rel
    if full_path.is_dir():
        raise RuntimeError("Attempted to import a directory")

    if not full_path.is_file():
        return full_path.name, None
    with open(full_path) as f:
        return full_path.name, f.read()


def _import_callback_with_searchpath(search, basedir, rel):
    full_path, content = _try_path(basedir, rel)
    if content:
        return full_path, content
    for p in search:
        full_path, content = _try_path(p, rel)
        if content:
            return full_path, content
    raise RuntimeError("File not found")


def _import_cb(basedir, rel):
    # Add current working dir to search path for Jsonnet import callback
    search_path = [
        P(".").resolve(),
        __install_dir__.resolve(),
        P("./dependencies").resolve(),
    ]
    return _import_callback_with_searchpath(search_path, basedir, rel)


def _list_dir(basedir, basename):
    """
    Non-recursively list files in directory `basedir`. If `basename` is set to
    True, only return the file name itself and not the full path.
    """
    files = [x for x in P(basedir).iterdir() if x.is_file()]

    if basename:
        return [f.parts[-1] for f in files]

    return files


_native_callbacks = {
    "yaml_load": (("file",), yaml_load),
    "yaml_load_all": (("file",), yaml_load_all),
    "list_dir": (
        (
            "dir",
            "basename",
        ),
        _list_dir,
    ),
}


# pylint: disable=too-many-arguments
def jsonnet_runner(inv, component, path, jsonnet_func, jsonnet_input, **kwargs):
    def _inventory():
        return inv

    _native_cb = _native_callbacks
    _native_cb["inventory"] = ((), _inventory)
    kwargs["target"] = component
    kwargs["component"] = component
    output_dir = P("compiled", component, path)
    kwargs["output_path"] = str(output_dir)
    output = jsonnet_func(
        str(jsonnet_input),
        import_callback=_import_cb,
        native_callbacks=_native_cb,
        ext_vars=kwargs,
    )
    out_objs = json.loads(output)
    for outobj, outcontents in out_objs.items():
        outpath = output_dir / f"{outobj}.yaml"
        if not outpath.exists():
            print(f"   > {outpath} doesn't exist, creating...")
            os.makedirs(outpath.parent, exist_ok=True)
        if isinstance(outcontents, list):
            yaml_dump_all(outcontents, outpath)
        else:
            yaml_dump(outcontents, outpath)


def _filter_file(component: str, filterpath: str) -> P:
    # TODO: Do we need to handle search path better?
    return P("dependencies") / component / filterpath


def run_jsonnet_filter(
    inventory: Dict, component: str, filterid: str, path: P, **filterargs: str
):
    """
    Run user-supplied jsonnet as postprocessing filter. This is the original
    way of doing postprocessing filters.
    """
    filterfile = _filter_file(component, filterid)
    # pylint: disable=c-extension-no-member
    jsonnet_runner(
        inventory, component, path, _jsonnet.evaluate_file, filterfile, **filterargs
    )


def validate_jsonnet_filter(cn: str, fd: Dict):
    filterfile = _filter_file(cn, fd["filter"])
    if not filterfile.is_file():
        raise ValueError("Jsonnet filter definition does not exist")
