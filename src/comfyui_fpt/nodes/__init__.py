"""The node classes, one module each. The mappings ComfyUI reads are in the package `__init__`."""
from .load_version import FPTLoadVersion
from .publish_version import FPTPublishVersion

__all__ = ["FPTLoadVersion", "FPTPublishVersion"]
