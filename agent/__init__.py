"""InferenceAtlas public agent package."""

from ._env import load_dotenv

load_dotenv()

__all__ = ["InferenceAtlasAgent"]


def __getattr__(name: str):
    if name == "InferenceAtlasAgent":
        from .agent import InferenceAtlasAgent

        return InferenceAtlasAgent
    raise AttributeError(f"module 'agent' has no attribute {name!r}")
