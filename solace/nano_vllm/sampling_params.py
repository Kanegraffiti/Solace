from dataclasses import dataclass


@dataclass
class SamplingParams:
    """Minimal sampling parameter container from nano-vllm."""

    temperature: float = 1.0
    max_tokens: int = 64
    ignore_eos: bool = False
