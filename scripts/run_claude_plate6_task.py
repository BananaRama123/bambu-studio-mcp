"""Task for Claude Opus sub-agent."""
from src.bambu_studio_mcp.claude_worker import delegate_to_claude

task = """
We have a Bambu 3MF project at:
`C:\\Users\\cplacentile\\Downloads\\SSBAP02_Black.3mf`

User Request:
'The parts on plate 6 are currently filiments type 4 can you change it to filiment type 2 and then slice all plates.'

Please create `scripts/update_plate6_and_slice.py` that:
1. Inspects and modifies `Metadata/model_settings.config` inside `C:\\Users\\cplacentile\\Downloads\\SSBAP02_Black.3mf` so that Object_4 (object id=6, which is on Plate 6) has its extruder changed from 4 to 2 (both at object level and any child part metadata level).
2. Verifies that all other objects (Plate 1 = 4, Plate 2 = 4, Plate 3 = 1, Plate 4 = 1, Plate 5 = 2) retain their original filament assignments.
3. Writes the modified archive to `C:\\Users\\cplacentile\\Downloads\\SSBAP02_Plate6_Fila2.3mf`.
4. Executes the script and verifies the output 3MF is valid.
5. Launches or slices the updated project using `bambu-studio.exe`.
"""

res = delegate_to_claude(task_prompt=task)
print("SUCCESS:", res.get("success"))
print("MODEL:", res.get("model"))
print("RESPONSE:\n", res.get("claude_response"))
