"""更新文档版本索引 versions.json。"""

import json
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
    new_version = sys.argv[2]

    versions: list[dict[str, str]] = []
    if path.exists():
        versions = json.loads(path.read_text())

    existing = {v["version"] for v in versions}
    if new_version not in existing:
        entry = {"version": new_version, "url": f"../{new_version}/"}
        if new_version == "latest":
            versions.insert(0, entry)
        else:
            idx = next(
                (i for i, v in enumerate(versions) if v["version"] != "latest"),
                len(versions),
            )
            versions.insert(idx, entry)

    path.write_text(json.dumps(versions, indent=2) + "\n")


if __name__ == "__main__":
    main()
