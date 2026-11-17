"""
Regenerate the Python code for companion.proto:

    python -m grpc_api.generate

Needs grpcio-tools (in requirements.txt). Run it from the project root after
editing the .proto file; the generated files are committed, so running the
app doesn't need this step.
"""

from pathlib import Path

from grpc_tools import protoc


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROTO = "grpc_api/companion.proto"


def main() -> None:
    # Paths relative to the project root, so the generated code imports
    # "from grpc_api import companion_pb2"
    result = protoc.main([
        "grpc_tools.protoc",
        f"--proto_path={PROJECT_ROOT}",
        f"--python_out={PROJECT_ROOT}",
        f"--pyi_out={PROJECT_ROOT}",
        f"--grpc_python_out={PROJECT_ROOT}",
        str(PROJECT_ROOT / PROTO),
    ])
    if result != 0:
        raise SystemExit(f"protoc failed with exit code {result}")
    print("Generated grpc_api/companion_pb2.py, companion_pb2.pyi and companion_pb2_grpc.py")


if __name__ == "__main__":
    main()
