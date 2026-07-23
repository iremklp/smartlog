from .stages import PipelineStage

__all__ = ["PipelineStage"]


def __getattr__(name: str) -> object:
    if name == "LogProcessingPipeline":
        from .pipeline import LogProcessingPipeline

        return LogProcessingPipeline
    raise AttributeError(name)
