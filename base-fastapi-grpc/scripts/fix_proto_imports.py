import re
import sys
from pathlib import Path


def main() -> int:
    proto_out_dir = Path(sys.argv[1])
    proto_src_dir = Path(sys.argv[2])

    prefix = package_prefix(proto_out_dir)
    roots = [directory.name for directory in proto_src_dir.iterdir() if directory.is_dir()]

    for pattern in ("*_pb2.py", "*_pb2.pyi", "*_pb2_grpc.py"):
        for file_path in proto_out_dir.rglob(pattern):
            content = file_path.read_text(encoding="utf-8")
            for root in roots:
                content = re.sub(
                    r"^from (" + root + r"(?:\.[a-zA-Z0-9_]+)*) import",
                    f"from {prefix}.\\1 import",
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r"^import (" + root + r"(?:\.[a-zA-Z0-9_]+)*_pb2)",
                    f"import {prefix}.\\1",
                    content,
                    flags=re.MULTILINE,
                )
            file_path.write_text(content, encoding="utf-8")
    return 0


def package_prefix(path: Path) -> str:
    parts = path.parts
    for marker in ("core", "app"):
        if marker in parts:
            return ".".join(parts[parts.index(marker):])
    return ".".join(part for part in parts if part not in (".", ".."))


if __name__ == "__main__":
    raise SystemExit(main())
