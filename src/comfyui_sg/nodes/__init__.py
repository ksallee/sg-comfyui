"""The node classes, one module each. The mappings ComfyUI reads are in the package `__init__`."""
from .load_version import SGLoadVersion
from .publish_version import SGPublishVersion

__all__ = ["SGLoadVersion", "SGPublishVersion"]
