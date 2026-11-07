from __future__ import annotations

import ast

import pytest

from scripts.check_steward_coverage import _bound_kind_values


def _values(source: str, variable: str) -> set[str]:
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Observation")
    constants = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and isinstance(statement.value, (ast.Tuple, ast.List)):
            value = ast.literal_eval(statement.value)
            constants.update({target.id: value for target in statement.targets if isinstance(target, ast.Name)})
    return _bound_kind_values(variable, call, parents, constants)


def test_comprehension_bound_kind_is_detected() -> None:
    assert _values(
        'items = [Observation(kind=kind) for kind in ("credential_leak", "credential_review")] ',
        "kind",
    ) == {"credential_leak", "credential_review"}


def test_unresolvable_kind_name_is_not_counted() -> None:
    assert _values("items = [Observation(kind=kind) for kind in unknown_kinds]", "kind") == set()


@pytest.mark.parametrize(
    "source",
    [
        '''def f(external):
    for kind in ("ghost",):
        kind = external
        Observation(kind=kind)
''',
        '''def f(cm):
    for kind in ("ghost",):
        with cm as kind:
            Observation(kind=kind)
''',
        '''def f():
    for kind in ("ghost",):
        try:
            raise ValueError()
        except ValueError as kind:
            Observation(kind=kind)
''',
        '''def f():
    for kind in ("ghost",):
        del kind
        Observation(kind=kind)
''',
        '''def f(external):
    for kind in ("ghost",):
        kind += external
        Observation(kind=kind)
''',
        '''def f(external):
    for kind in ("ghost",):
        def change():
            nonlocal kind
            kind = external
        change()
        Observation(kind=kind)
''',
        '''for kind in ("ghost",):
    def change():
        global kind
        kind = "other"
    change()
    Observation(kind=kind)
''',
        '''def f(external):
    for kind in ("ghost",):
        return [Observation(kind=kind) for x in (1,) if (kind := external)]
''',
        # Fail closed even when the rebinding is after the use.
        '''def f(external):
    for kind in ("ghost",):
        Observation(kind=kind)
        kind = external
''',
    ],
)
def test_any_other_binding_makes_loop_target_unresolvable(source: str) -> None:
    assert _values(source, "kind") == set()
