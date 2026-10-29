"""Turn speakers.json + cast.json into one concrete voice per role."""
from common import ROOT, load


class CastError(Exception):
    pass


def preset(backend, language, style="bedtime"):
    p = load(ROOT / "voices" / f"{backend}.json")
    lang = language.split("-")[0].lower()
    block = p.get(lang) or p.get("any")
    defaults = p.get("defaults", {})
    if style in ("audiobook", "kids"):
        defaults = {**defaults, **p.get(f"{style}_defaults", {})}
    kn = p.get(f"{style}_narrator", {}).get(lang) or p.get(f"{style}_narrator", {}).get("any")
    if kn and block:
        block = {**block, "narrator": kn}
    if not block:
        raise CastError(f"voices/{backend}.json has no preset for {language!r}; add one, or name every voice in "
                        f"cast.json explicitly")
    return defaults, block


def roles_in(speakers):
    out = set()
    for v in speakers.values():
        for s in (v if isinstance(v, list) else [v]):
            if s:
                out.add(s)
    return out


def ident(v):
    """Two roles may not share an identity — that is how listeners tell characters apart."""
    return (v["voice"], v.get("pitch", ""), v.get("instructions", ""))


def resolve(cfg, speakers, cast):
    """{role: voice settings}. cast.json values:
         {"voice": "…", …}      a specific voice (plus backend options)
         "pool:man_mid"         first free voice of that pool in voices/<backend>.json
         "same:narrator"        share another role's voice (e.g. a first-person narrator who also speaks)
       narrator falls back to the preset's narrator."""
    defaults, block = preset(cfg["backend"], cfg["language"], cfg.get("style", "bedtime"))
    pools = block.get("pools", {})
    out, aliases = {}, {}
    wanted = {"narrator"} | roles_in(speakers) | set(cast)

    def full(v):
        return {**defaults, **v}

    for role in sorted(wanted):
        c = cast.get(role)
        if role == "narrator" and c is None:
            c = block.get("narrator")
            if c is None:
                raise CastError("no narrator voice: add \"narrator\" to cast.json")
        if isinstance(c, dict):
            if "voice" not in c:
                raise CastError(f"{role}: cast entry needs a \"voice\"")
            out[role] = full(c)
        elif isinstance(c, str) and c.startswith("same:"):
            aliases[role] = c[5:]
        elif c is None:
            raise CastError(f"{role}: no voice — add it to cast.json (\"pool:<kind>\" or {{\"voice\": …}})")
        elif not (isinstance(c, str) and c.startswith("pool:")):
            raise CastError(f"{role}: unknown cast value {c!r}")

    seen = {}
    for role, v in out.items():
        k = ident(v)
        if k in seen:
            raise CastError(f"{role} and {seen[k]} have the same voice {k[0]} — use \"same:{seen[k]}\" if intended")
        seen[k] = role

    for role in sorted(wanted - set(out) - set(aliases)):
        kind = cast[role][5:]
        if kind not in pools:
            raise CastError(f"{role}: pool {kind!r} not in voices/{cfg['backend']}.json ({', '.join(pools)})")
        free = [v for v in pools[kind] if ident(full(v)) not in seen]
        if not free:
            raise CastError(f"{role}: pool {kind!r} has no voice left in this episode — pick another pool or name "
                            f"a voice outright")
        # prefer a base voice nobody uses yet; a re-pitched copy of a voice already on stage is the last resort
        used = {k[0] for k in seen}
        free.sort(key=lambda v: v["voice"] in used)
        out[role] = full(free[0])
        seen[ident(out[role])] = role

    for role, target in aliases.items():
        seen_chain = {role}
        while target in aliases:
            if target in seen_chain:
                raise CastError(f"alias loop at {role}")
            seen_chain.add(target); target = aliases[target]
        if target not in out:
            raise CastError(f"{role}: same:{target} — {target} has no voice")
        out[role] = out[target]
    return out
