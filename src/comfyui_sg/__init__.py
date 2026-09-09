"""ComfyUI nodes that publish generations to Flow Production Tracking with provenance.

Deliberately free of imports. The setup commands — `python -m comfyui_sg.fields`, `python -m
comfyui_sg.seed` — are run on whatever Python is to hand, and importing a node class here would
pull in torch and stop them. The mappings ComfyUI reads are built in the repo-root `__init__.py`.
"""
