"""Checkout-level operations over evidence custody.

`custody.py` knows bundles and the transport. This module knows the Steward
checkout: where receipts live, how a dispatch is found, and how verification is
run against restored evidence. The CLI and the full-run driver both call these,
so there is exactly one implementation of each fail-closed boundary.

Boundaries (each returns or raises; none is advisory):

1. `publishDispatch`  dispatch issued      -> scan + dispatch receipts durable + read back
2. `acceptBuild`      builder accepts work -> the dispatch must already be durable
3. `publishBuild`     patch complete       -> diff + validated proof durable + read back
4. `verifyFromCustody` verifier retrieves  -> restore from custody, authenticate, run the canonical verifier
5. `publishVerdict`   outcome recorded     -> mechanical verdict receipt durable + read back
6. `readiness`        before READY/PR      -> whole chain re-read and re-verified from the remote
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, NamedTuple

from gaia_cli.steward.custody import (
    BLOCKED_PREFIX,
    Custody,
    CustodyError,
    CustodyRefused,
    Loaded,
    PublishResult,
    Restored,
    buildBundle,
    dispatchBundle,
    handoffRecord,
    authenticateDispatch,
    requirePins,
    restoreChain,
    verdictBundle,
)
from gaia_cli.steward.policy import StewardPolicy

REFUSED_EFFORTS = ("", "default", "inherit")
MAX_INPUT_BYTES = 8 * 1024 * 1024


class Verification(NamedTuple):
    """What verifying restored evidence produced, for any caller that needs more than the verdict."""

    result: Any
    restored: Restored
    prompt: str | None
    diffText: str | None
    outputs: Mapping[int, tuple[str, ...]] | None


def writerRecord(*, role: str, agentId: str | None, model: str | None, effort: str | None, runId: str | None = None) -> dict[str, Any]:
    """Who wrote a bundle. Model and effort are explicit or the write is refused."""

    if role in ("builder", "verifier"):
        if not model or not model.strip():
            raise CustodyRefused(f"a {role} bundle must name the model that did the work")
        if (effort or "").strip().lower() in REFUSED_EFFORTS:
            raise CustodyRefused(f"a {role} bundle must name an explicit effort; 'default' and 'inherit' are refused")
    record: dict[str, Any] = {"role": role}
    for key, value in (("agentId", agentId), ("model", model), ("effort", effort), ("runId", runId)):
        if value:
            record[key] = value
    return record


def receiptsDirectory(root: Path) -> tuple[Path, Path]:
    policy = StewardPolicy.load(root)
    state = root / policy.state_directory
    return state / policy.receipts_directory, state


def readBounded(path: Path, label: str) -> bytes:
    if not path.is_file():
        raise CustodyRefused(f"{label} {path} does not exist")
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise CustodyRefused(f"{label} {path.name} is {size} bytes, over the {MAX_INPUT_BYTES} byte bound")
    return path.read_bytes()


def localDispatch(root: Path, debtId: str, dispatchId: str | None = None) -> tuple[bytes, bytes]:
    """Exact bytes of the newest local dispatch receipt for a debt, and of the scan behind it."""

    from gaia_cli.steward.routing import RoutingError, _dispatch_receipt_for

    receipts, _state = receiptsDirectory(root)
    try:
        data = _dispatch_receipt_for(receipts, debtId, dispatchId)
    except RoutingError as exc:
        raise CustodyRefused(f"no local dispatch receipt to preserve: {exc}") from exc
    dispatchRaw = readBounded(receipts / f"{data['runId']}.json", "dispatch receipt")
    scanRaw = readBounded(receipts / f"{data.get('scanReceiptId')}.json", "scan receipt")
    return scanRaw, dispatchRaw


# -- 1. dispatch issued -------------------------------------------------------


def publishDispatch(
    root: Path, custody: Custody, debtId: str, *, writer: Mapping[str, Any], dispatchId: str | None = None,
    scanRaw: bytes | None = None, dispatchRaw: bytes | None = None, prompt: str | None = None,
) -> PublishResult:
    """Make the original scan and dispatch receipts durable. Idempotent per receipt."""

    if scanRaw is None or dispatchRaw is None:
        scanRaw, dispatchRaw = localDispatch(root, debtId, dispatchId)
    bundle, objects = dispatchBundle(
        debtId=debtId, scanRaw=scanRaw, dispatchRaw=dispatchRaw, writer=writer,
        promptRaw=prompt.encode("utf-8") if prompt is not None else None,
    )
    return custody.publish(bundle, objects)


# -- 2. builder accepts work ---------------------------------------------------


def acceptBuild(custody: Custody, debtId: str, *, bundleId: str | None = None, dispatchId: str | None = None) -> Loaded:
    """A builder may only take work whose authorizing receipts are already durable and intact."""

    commit, selected = custody.select(debtId, "dispatch", bundleId=bundleId, dispatchId=dispatchId)
    return custody.loadAt(commit, selected.bundleId, debtId)


# -- 3. patch complete, proof captured ------------------------------------------


def publishBuild(
    root: Path, custody: Custody, debtId: str, *, writer: Mapping[str, Any], summary: str, noChange: bool,
    diffPath: Path | None, proofPath: Path | None, dispatchBundleId: str | None = None,
    dispatchId: str | None = None,
) -> PublishResult:
    if not summary or not summary.strip():
        raise CustodyRefused("a build bundle needs a non-empty summary")
    dispatch = acceptBuild(custody, debtId, bundleId=dispatchBundleId, dispatchId=dispatchId)
    diffRaw = readBounded(diffPath, "candidate diff") if diffPath is not None else None
    proofRaw = readBounded(proofPath, "proof transcript") if proofPath is not None else None
    bundle, objects = buildBundle(
        dispatch=dispatch, diffRaw=diffRaw, proofRaw=proofRaw, noChange=noChange, summary=summary.strip(), writer=writer,
    )
    return custody.publish(bundle, objects)


# -- 4. independent verifier retrieves artifacts ---------------------------------


def restore(
    root: Path, custody: Custody, debtId: str, *, bundleId: str | None = None, pinBundle: str | None = None,
    pinCommit: str | None = None, expectDispatchBundle: str | None = None, expectDispatchId: str | None = None,
) -> Restored:
    receipts, state = receiptsDirectory(root)
    return restoreChain(
        custody, root, debtId, bundleId=bundleId, receiptsDirectory=receipts, stateRoot=state,
        pinBundle=pinBundle, pinCommit=pinCommit,
        expectDispatchBundle=expectDispatchBundle, expectDispatchId=expectDispatchId,
    )


def verifyFromCustody(
    root: Path, custody: Custody, debtId: str, *, bundleId: str | None = None, controller: Any = None,
    prompt: bool = False, pinBundle: str | None = None, pinCommit: str | None = None,
    expectDispatchBundle: str | None = None, expectDispatchId: str | None = None,
) -> Verification:
    """Restore the original evidence from custody and run the canonical mechanical verifier on it.

    `gaia steward verify` itself is unchanged: this only supplies it with the
    exact receipts and the exact patch that were durable, and refuses if the
    verifier would pick a different receipt than the one that authorized the work.
    """

    from gaia_cli.steward.routing import (
        RoutingError,
        _dispatch_receipt_for,
        render_verification,
        render_verifier_prompt_for,
    )

    restored = restore(
        root, custody, debtId, bundleId=bundleId, pinBundle=pinBundle, pinCommit=pinCommit,
        expectDispatchBundle=expectDispatchBundle, expectDispatchId=expectDispatchId,
    )
    if restored.build is None:
        raise CustodyRefused("custody holds a dispatch for this debt but no build output to verify")
    if restored.diffPath is None or restored.proofPath is None:
        raise CustodyRefused("the build in custody reported no change; there is no patch to verify mechanically")
    dispatchIdentity = restored.dispatch.bundle.identity
    receipts, _state = receiptsDirectory(root)
    try:
        chosen = _dispatch_receipt_for(receipts, debtId, str(dispatchIdentity["dispatchId"]))
    except RoutingError as exc:
        raise CustodyRefused(f"restored dispatch cannot be used: {exc}") from exc
    if chosen.get("runId") != dispatchIdentity["dispatchReceiptId"]:
        raise CustodyRefused(
            "this checkout holds a newer dispatch receipt for the debt than the one that authorized the build; "
            "the verifier would judge the wrong envelope"
        )
    renderer = render_verifier_prompt_for if prompt else render_verification
    try:
        rendered = renderer(
            root, debtId, diff_path=restored.diffPath, proof_path=restored.proofPath,
            controller=controller, dispatch_id=str(dispatchIdentity["dispatchId"]),
        )
    except RoutingError as exc:
        raise CustodyRefused(f"verification against restored evidence was refused: {exc}") from exc
    if prompt:
        return Verification(rendered[0], restored, rendered[1], None, None)
    return Verification(rendered[0], restored, None, rendered[1], rendered[2])


# -- 5. verification outcome recorded ---------------------------------------------


def publishVerdict(
    root: Path, custody: Custody, debtId: str, *, receiptPath: Path, buildBundleId: str, writer: Mapping[str, Any],
) -> PublishResult:
    receiptRaw = readBounded(receiptPath, "verification receipt")
    commit, selected = custody.select(debtId, "build", bundleId=buildBundleId)
    build = custody.loadAt(commit, selected.bundleId, debtId)
    bundle, objects = verdictBundle(build=build, receiptRaw=receiptRaw, writer=writer)
    return custody.publish(bundle, objects)


# -- 6. before READY / PR handoff ---------------------------------------------------


def readiness(
    custody: Custody, debtId: str, *, bundleId: str | None = None, pinBundle: str | None = None,
    pinCommit: str | None = None,
) -> dict[str, Any]:
    """Re-read the whole chain from the remote. Anything missing or altered raises.

    A READY handoff needs a dispatch, a build with its patch and proof, and a
    recorded mechanical verdict of `pending` (no objection). It never reports
    acceptance: that is the independent verifier's, recorded through the lane.
    """

    links = custody.chain(debtId, bundleId)  # re-authenticates every link, including verdict-to-build binding
    requirePins(custody, links, pinBundle=pinBundle, pinCommit=pinCommit)
    kinds = [link.bundle.kind for link in links]
    if kinds != ["dispatch", "build", "verdict"]:
        raise CustodyRefused(f"the evidence chain is incomplete ({' -> '.join(kinds)}); a handoff needs dispatch -> build -> verdict")
    verdict = str(links[-1].bundle.identity.get("verdict"))
    if verdict != "pending":
        raise CustodyRefused(f"the recorded mechanical verdict is {verdict!r}, not 'pending'; this work is not ready")
    record = handoffRecord(links, custody.store.ref)
    record["mechanicalVerdict"] = verdict
    record["independentVerifierRequired"] = True
    # Honest scope: integrity and binding are proven here; WHO may write the ref is a repository-permission question.
    record["writerAuthorization"] = (
        "not verified by this command: ref permissions are repository configuration. Pin the bundle ids and "
        "evidence commit from the ledger or the Lead's PR handoff (--pin-bundle / --pin-commit)."
    )
    return record


def originalPrompt(custody: Custody, debtId: str, *, dispatchBundle: str, dispatchId: str) -> str:
    """The exact builder prompt rendered when this work was dispatched, restored from custody.

    Never re-renders and never consults current policy: if the original dispatch
    cannot be authenticated, or it carries no preserved prompt, this raises and
    the caller stays blocked.
    """

    tip = custody.store.snapshot()
    loaded = custody.loadAt(tip, dispatchBundle, debtId)
    if loaded.bundle.kind != "dispatch":
        raise CustodyRefused("the ledger's dispatch pointer does not name a dispatch bundle")
    if loaded.bundle.identity.get("dispatchId") != dispatchId:
        raise CustodyRefused("the custody dispatch belongs to a different dispatch than this work item")
    authenticateDispatch(loaded.files["scan-receipt"], loaded.files["dispatch-receipt"], debtId=debtId)
    raw = loaded.files.get("builder-prompt")
    if raw is None:
        raise CustodyRefused(
            "the original builder prompt was not preserved in this dispatch bundle; it will not be re-rendered "
            "from current policy"
        )
    return raw.decode("utf-8")


def blockedMessage(exc: CustodyError) -> str:
    return exc.blocked()


__all__ = ["BLOCKED_PREFIX"]
