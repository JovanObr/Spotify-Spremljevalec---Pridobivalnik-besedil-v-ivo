
from pathlib import Path
from pyaxis import pyaxis

project_root = Path(__file__).resolve().parent.parent
px_path = project_root / "data" / "european_live_performances.px"

result = pyaxis.parse(
    str(px_path),
    encoding="utf-8",
)

print("Parsed successfully.")
print("\nAvailable sections:", result.keys())

print("\nMetadata:")
print(result.get("METADATA"))

print("\nData:")
print(result.get("DATA"))
