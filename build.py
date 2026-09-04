import json
import re
from pathlib import Path

from markdown import Markdown

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "README.md"
CSS = ROOT / "style.css"
OUTPUT = ROOT / "Hermes_Desktop_Automation_Quick_Start_Guide.html"
VERSIONS = ROOT / "versions.json"


def build() -> Path:
    source = SOURCE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    versions = json.loads(VERSIONS.read_text(encoding="utf-8"))
    document = versions["document"]
    doc_version = document["version"]
    doc_date = document["date"]

    md = Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={
            "toc": {
                "toc_depth": "1-3",
                "permalink": False,
                "title": "",
            }
        },
        output_format="html5",
    )
    body = md.convert(source)
    toc_source = re.sub(
        r'<div class="cover-markdown".*?</div>',
        "",
        source,
        count=1,
        flags=re.DOTALL,
    )
    toc_md = Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"toc_depth": "1-3", "permalink": False}},
        output_format="html5",
    )
    toc_md.convert(toc_source)
    toc = toc_md.toc

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Windows에서 Orca, Codex, Hermes Agent와 OpenAI Codex OAuth로 데스크탑 업무 자동화를 시작하는 실무 가이드">
  <title>Hermes 기반 데스크탑 업무 자동화 Quick Start Guide</title>
  <style>{css}</style>
</head>
<body>
  <div class="reading-progress" id="reading-progress"></div>
  <main class="shell">
    <aside class="toc-panel" aria-label="문서 목차">
      <div class="toc-brand">
        <div class="sigil">H</div>
        <div><b>HERMES QUICK START</b><span>Desktop Automation · v{doc_version}</span></div>
      </div>
      <nav>{toc}</nav>
    </aside>
    <article class="document">
      <div class="content">{body}</div>
      <footer class="meta-footer">Hermes 기반 데스크탑 업무 자동화 Quick Start Guide · v{doc_version} · {doc_date} · 공개 배포용</footer>
    </article>
  </main>
  <script>
    const bar = document.getElementById('reading-progress');
    const update = () => {{
      const max = document.documentElement.scrollHeight - innerHeight;
      bar.style.width = (max > 0 ? (scrollY / max) * 100 : 0) + '%';
    }};
    addEventListener('scroll', update, {{ passive: true }});
    update();
  </script>
</body>
</html>
"""
    OUTPUT.write_text(html, encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    print(build())
