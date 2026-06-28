# Gaia Skill Tree: Model Weight Security Guidelines

## Banned Formats
- Python `pickle` (`.pkl`, `.pickle`, `.pt` with pickle serialization)
- Any model weight serialization format that executes arbitrary code on deserialization

## Required Safe Formats
- `safetensors` (recommended default for tensor-safe weights)
- `GGUF` (for quantized, edge, and cpu-friendly deployments)
- `ONNX` (for cross-framework interoperability)

## Why This Matters
Python's standard `pickle` protocol can execute arbitrary code during deserialization by exploiting the `__reduce__` method. Over 3,300 models on Hugging Face have been identified as carrying malicious or vulnerable pickle-based weights that can compromise a user's system upon loading. 

As a public capability registry, Gaia inherits supply chain risks if our skill definitions reference unsafe weights. To maintain a secure ecosystem, Gaia will not reference, recommend, or endorse model weights in unsafe formats.

## Compliance
- All model weights referenced in `gaia.json` or skill definitions MUST point to safe weight formats.
- Pull Requests containing pickle-based formats (like `.pkl` or `.pickle` extensions) will be auto-rejected.
- Existing registry entries with legacy unsafe weight formats have a 90-day migration window to transition to safe formats.
