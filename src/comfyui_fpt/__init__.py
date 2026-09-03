from .nodes import FPTLoadVersion, FPTPublishVersion

NODE_CLASS_MAPPINGS = {"FPTLoadVersion": FPTLoadVersion,
                       "FPTPublishVersion": FPTPublishVersion}
NODE_DISPLAY_NAME_MAPPINGS = {"FPTLoadVersion": "Flow PT Load Version",
                             "FPTPublishVersion": "Flow PT Publish Version"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
