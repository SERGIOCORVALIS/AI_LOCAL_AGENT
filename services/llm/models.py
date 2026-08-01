from __future__ import annotations


def normalize_model_name(name: str) -> str:
    return name.strip()


def model_base(name: str) -> str:
    """Return the untagged model family (before the first ':')."""
    return normalize_model_name(name).split(":", 1)[0]


def model_matches(requested: str, installed: str) -> bool:
    """True when an installed tag satisfies a configured model id."""
    want = normalize_model_name(requested)
    have = normalize_model_name(installed)
    if not want or not have:
        return False
    if want == have:
        return True
    if have.startswith(f"{want}:"):
        return True
    want_base = model_base(want)
    have_base = model_base(have)
    if want_base == have_base:
        # Configured tag vs installed tag of the same family.
        return ":" not in want or want == have
    return False


def resolve_model_name(requested: str, installed: list[str]) -> str | None:
    """Pick the best installed Ollama tag for a configured model id."""
    want = normalize_model_name(requested)
    if not want:
        return None
    if want in installed:
        return want

    exact_prefix = [tag for tag in installed if tag.startswith(f"{want}:")]
    if exact_prefix:
        return exact_prefix[0]

    want_base = model_base(want)
    family = [
        tag
        for tag in installed
        if model_base(tag) == want_base and model_matches(want, tag)
    ]
    if family:
        # Prefer an exact configured tag, else first family match.
        for tag in family:
            if tag == want:
                return tag
        return family[0]

    soft = [tag for tag in installed if want_base and want_base in model_base(tag)]
    if soft:
        return soft[0]
    return None


def model_is_available(requested: str, installed: list[str]) -> bool:
    return resolve_model_name(requested, installed) is not None
