"""One-off reel (owner 14 Nov): Kandha Sashti temples, Coimbatore 360 news-reel design + Valluvar voice; one photo per sentence.
python custom/make.py <out.mp4>   (run from the repo root; never posts)"""
import json, os, sys
from pathlib import Path

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / "reel"), str(ROOT / "poster"), str(ROOT / "research_free")]
os.environ["REEL_PUNCH"] = "0"
import reel4
R, V3 = reel4.R, reel4.V3

story = json.loads((ROOT / "custom" / "story.json").read_text())
story["images"] = [str(ROOT / "custom" / "img" / Path(p).name) for p in story["images"]]
spec = ROOT / "custom" / "story_run.json"
spec.write_text(json.dumps(story, ensure_ascii=False))

STARTS = []
_mvt = R.make_voice_track


def grab(work, texts, starts, total):
    STARTS[:] = starts
    return _mvt(work, texts, starts, total)


def per_sentence(n_img, content_end, snaps):
    """one temple photo for each spoken sentence (photo i while sentence i is read)"""
    cuts = [0.0] + [STARTS[i] - 0.15 for i in range(1, n_img)] + [content_end + 5]
    shots = []
    for i in range(n_img):
        z0, z1, fx, fy, px, py = reel4.SINGLE_MOVES[i % len(reel4.SINGLE_MOVES)]
        shots.append({"a": round(cuts[i], 3), "b": round(cuts[i + 1], 3), "img": i,
                      "z0": min(z0, V3.MAX_ZOOM), "z1": min(z1, V3.MAX_ZOOM), "fx": fx, "fy": fy, "px": px, "py": py})
    return shots


R.make_voice_track = grab
reel4.plan_shots = per_sentence
reel4.main(str(spec), sys.argv[1], "coimbatore")
