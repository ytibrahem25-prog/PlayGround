#!/usr/bin/env bash
# Ibrahim Amer Minecraft — static preview deployment.
#
# Build: generates dist/ (static showcase page + preview image) from the
# existing project files inside PROJECT_DIR. The only write outside the
# project is worker metadata: deployment-output.json in OPENCODE_WEB_DIR.
# Serve: foreground static file server on $PORT (default 3000).
# Every substantive command below is timed with /usr/bin/time -p.
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$PWD"
PORT="${PORT:-3000}"
DIST="$ROOT/dist"
GAME_DIR="$ROOT/ibrahim_amer_minecraft"
DEPLOY_JSON="${OPENCODE_WEB_DIR:?OPENCODE_WEB_DIR must be set}/deployment-output.json"

case "$PORT" in ''|*[!0-9]*) echo "PORT must be numeric, got: $PORT" >&2; exit 1;; esac

# --- dependencies: the static build needs only python3, nothing to install ---
/usr/bin/time -p python3 --version

# --- build dist/ when needed (missing output or newer sources) ---
/usr/bin/time -p mkdir -p "$DIST"
/usr/bin/time -p python3 - "$ROOT" <<'PYEOF'
import html
import os
import shutil
import sys

root = sys.argv[1]
game = os.path.join(root, "ibrahim_amer_minecraft")
dist = os.path.join(root, "dist")
os.makedirs(dist, exist_ok=True)

sources = [
    os.path.join(root, "start.sh"),
    os.path.join(root, "README.md"),
    os.path.join(game, "world_core.py"),
    os.path.join(game, "main.py"),
    os.path.join(game, "textures.py"),
    os.path.join(game, "README_AR.md"),
    os.path.join(game, "preview.png"),
]
sources = [p for p in sources if os.path.isfile(p)]
target = os.path.join(dist, "index.html")
if os.path.isfile(target) and sources and all(
    os.path.getmtime(target) >= os.path.getmtime(p) for p in sources
):
    print("build fresh, skipping regenerate")
else:
    title = "Ibrahim Amer Minecraft"
    rights = "(c) Ibrahim Amer"
    try:
        ns = {}
        with open(os.path.join(game, "world_core.py"), encoding="utf-8") as fh:
            exec(compile(fh.read(), "world_core.py", "exec"), ns)
        title = ns.get("GAME_TITLE", title)
        rights = ns.get("COPYRIGHT", rights).replace("\u00a9", "(c)")
    except Exception as exc:
        print("warning: falling back to default title:", exc)
    shot = os.path.join(game, "preview.png")
    if os.path.isfile(shot):
        shutil.copyfile(shot, os.path.join(dist, "preview.png"))
        img_tag = '<img src="preview.png" alt="Ibrahim Amer Minecraft preview">'
    else:
        img_tag = "<p>No preview image available.</p>"
    page = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:system-ui,'Segoe UI',Tahoma,Arial,sans-serif;margin:0 auto;max-width:960px;padding:24px;line-height:1.8;background:#0e1626;color:#eef2f7}}
h1{{color:#7cc4ff}}h2{{color:#a8d8ff;border-bottom:1px solid #24405e;padding-bottom:4px}}
img{{max-width:100%;border-radius:8px;border:1px solid #24405e}}
code{{background:#1a2942;padding:2px 6px;border-radius:4px;direction:ltr;display:inline-block}}
ul{{padding-right:20px}}footer{{margin-top:32px;color:#9fb3c8}}
.badge{{display:inline-block;background:#1a2942;border:1px solid #2f5b8f;border-radius:12px;padding:2px 12px;margin:2px}}
</style>
</head>
<body>
<h1>{title}</h1>
<p><span class="badge">3D</span> <span class="badge">Python</span> <span class="badge">Minecraft-like</span> <span class="badge">Android-ready</span></p>
{img}
<h2>عن اللعبة</h2>
<p>لعبة مكعبات ثلاثية الأبعاد بأسلوب Minecraft مكتوبة بلغة Python: عالم بلوكات يتولد تلقائياً، حركة وقفز وكاميرا لمس، كسر ووضع البلوكات، وأنواع Grass وDirt وStone وWood مع أزرار تحكم على الشاشة وواجهة عربية.</p>
<h2>التحكم</h2>
<ul>
<li><code>WASD</code> حركة، مسافة قفز، ماوس تدوير الكاميرا</li>
<li>كليك يسار كسر بلوك، كليك يمين بناء، مفاتيح <code>1-4</code> اختيار البلوك</li>
<li>على الموبايل: أزرار أمام/خلف/يسار/يمين + قفز + كسر + بناء، والسحب لتدوير الكاميرا</li>
</ul>
<h2>التشغيل</h2>
<ul>
<li>كمبيوتر: <code>pip install -r requirements.txt &amp;&amp; python main.py</code> داخل <code>ibrahim_amer_minecraft/</code></li>
<li>أندرويد: <code>buildozer android debug</code> باستخدام <code>buildozer.spec</code></li>
</ul>
<footer>{rights} — جميع الحقوق محفوظة</footer>
</body>
</html>
""".format(title=html.escape(title), rights=html.escape(rights), img=img_tag)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("built", target)
PYEOF

# --- deployment metadata for the controller (worker metadata dir only) ---
ROOT="$ROOT" DIST="$DIST" OUT="$DEPLOY_JSON" /usr/bin/time -p python3 -c 'import json, os; json.dump({"project": os.environ["ROOT"], "directory": os.environ["DIST"]}, open(os.environ["OUT"], "w")); print("wrote", os.environ["OUT"])'

echo "serving $DIST on port $PORT (project: $ROOT)"
# --- serve the built directory in the foreground ---
/usr/bin/time -p python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$DIST"
