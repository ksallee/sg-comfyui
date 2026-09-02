from .nodes import FPTFetchVersion, FPTPublishVersion

NODE_CLASS_MAPPINGS = {"FPTFetchVersion": FPTFetchVersion,
                       "FPTPublishVersion": FPTPublishVersion}
NODE_DISPLAY_NAME_MAPPINGS = {"FPTFetchVersion": "Flow PT Fetch Version",
                             "FPTPublishVersion": "Flow PT Publish Version"}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
