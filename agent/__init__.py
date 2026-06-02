"""InferenceAtlas public agent package."""

__all__ = ["InferenceAtlasAgent"]


def __getattr__(name: str):
    if name == "InferenceAtlasAgent":
        from .agent import InferenceAtlasAgent

        return InferenceAtlasAgent
    raise AttributeError(f"module 'agent' has no attribute {name!r}")
