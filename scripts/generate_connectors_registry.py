"""Generate web/static/connectors-registry.json from agent/ui_connectors.py."""

from __future__ import annotations

import json

from agent.scenarios import ROOT_DIR
from agent.ui_connectors import build_connectors_payload

OUTPUT = ROOT_DIR / "web" / "static" / "connectors-registry.json"


def main() -> None:
    OUTPUT.write_text(
        json.dumps(build_connectors_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT.relative_to(ROOT_DIR))


if __name__ == "__main__":
    main()
