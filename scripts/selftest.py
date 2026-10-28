#!/usr/bin/env python3
"""Offline self-test: quote splitting, casting, and the check.py gate (both what it must block and what it must
let through). No network, no TTS calls. Run: python3 scripts/selftest.py"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import paragraph_runs, runs  # noqa: E402
from castlib import CastError, resolve  # noqa: E402

EXAMPLE = HERE.parent / "examples/red-headed-league"
fails = []


def expect(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


# ---- quote splitting ----
expect("zh quote+said", runs("「你好，」他說，「我是華生。」"), [("Q", "你好，"), ("N", "他說，"), ("Q", "我是華生。")])
expect("en curly", runs("“Well,” said he, “what then?”"), [("Q", "Well,"), ("N", "said he,"), ("Q", "what then?")])
expect("ascii", runs('He said "go away" quietly.'), [("N", "He said"), ("Q", "go away"), ("N", "quietly.")])
expect("nested stays outer", runs("「他說『快走』了嗎？」"), [("Q", "他說『快走』了嗎？")])
expect("multi-paragraph speech", paragraph_runs([
    {"id": "P1", "text": "“It began last year."}, {"id": "P2", "text": "“Then I saw it.”"},
    {"id": "P3", "text": "And so on."}]),
    {"P1": [("Q", "It began last year.")], "P2": [("Q", "Then I saw it.")], "P3": [("N", "And so on.")]})

# ---- casting ----
cfg = {"backend": "edge", "language": "en"}
v = resolve(cfg, {"P1": "holmes", "P2": "watson"},
            {"holmes": {"voice": "en-GB-ThomasNeural"}, "watson": "same:narrator"})
expect("alias shares narrator voice", v["watson"], v["narrator"])
for name, cast, sp in [
        ("missing voice", {}, {"P1": "holmes"}),
        ("duplicate voice", {"a": {"voice": "x"}, "b": {"voice": "x"}}, {"P1": "a", "P2": "b"}),
        ("unknown pool", {"a": "pool:dragon"}, {"P1": "a"})]:
    try:
        resolve(cfg, sp, cast)
        fails.append(f"cast {name}: not blocked")
    except CastError:
        pass

# ---- check.py gate on a copy of the example ----


def gate(mutate):
    with tempfile.TemporaryDirectory() as d:
        ep = Path(d) / "ep"
        shutil.copytree(EXAMPLE, ep, ignore=shutil.ignore_patterns("build", "*.m4a"))
        mutate(ep)
        return subprocess.run([sys.executable, str(HERE / "check.py"), str(ep)], capture_output=True).returncode


def edit(rel, fn):
    def m(ep):
        p = ep / rel
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d, ep)
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return m


must_block = {
    "dropped paragraph": edit("script/script.json", lambda d, ep: d.pop(5)),
    "speaker count": edit("script/speakers.json", lambda d, ep: d.update(P008=["holmes"])),
    "untranslated": edit("script/script.json", lambda d, ep: d[13].update(
        text=json.loads((ep / "source/source.json").read_text())[13]["text"])),
    "truncated": edit("script/script.json", lambda d, ep: d[11].update(text=d[11]["text"][:60] + "」")),
    "tag without quote": edit("script/speakers.json", lambda d, ep: d.update(P007="holmes")),
    "role without voice": edit("cast.json", lambda d, ep: d.pop("wilson")),
}
for name, m in must_block.items():
    if gate(m) == 0:
        fails.append(f"gate {name}: not blocked")
if gate(lambda ep: None) != 0:
    fails.append("gate: clean example was blocked")
if gate(edit("script/script.json", lambda d, ep: d[11].update(text=d[11]["text"][:60] + "」", allow_short=True))):
    fails.append("gate: allow_short escape hatch did not work")

for f in fails:
    print("FAIL", f)
print("selftest OK" if not fails else f"selftest FAILED ({len(fails)})")
sys.exit(1 if fails else 0)
