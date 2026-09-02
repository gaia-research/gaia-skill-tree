"""Bounded sentence-transformers fixture used only by the playbook dry-run."""


class _FixtureVector(list):
    def tolist(self):
        return list(self)


class SentenceTransformer:
    def __init__(self, model_name):
        if model_name != "all-MiniLM-L6-v2":
            raise ValueError(f"unexpected fixture model: {model_name}")

    def encode(self, inputs, convert_to_numpy=True):
        if len(inputs) != 1 or not inputs[0].startswith("Example Skill:"):
            raise ValueError("unexpected fixture embedding input")
        return [_FixtureVector([1.0, 0.0, 0.0])]
