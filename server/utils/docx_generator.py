import os
import json
import subprocess
import tempfile
import logging
from io import BytesIO
from pathlib import Path

logger = logging.getLogger("DOCX_BRIDGE")

# Get path to the JS generator script relative to this file
JS_GENERATOR = Path(__file__).parent / "docx_generator.js"

def build_docx_cv(data: dict, style="classic_1page") -> bytes:
    """
    Python Bridge to the Node.js docx_generator.js.
    Ensures 100% layout fidelity by using the original Node designs.
    """
    # Verify node availability first
    try:
        subprocess.run(["node", "-v"], capture_output=True, check=True)
    except Exception:
        logger.error("!!! CRITICAL: Node.js (node) is NOT FOUND in the system PATH.")
        raise RuntimeError("Node.js is not installed or not in PATH. Word generation failed.")

    # Create a temporary directory for the process
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_path = os.path.join(tmp_dir, "data.json")
        out_dir = os.path.join(tmp_dir, "output")
        os.makedirs(out_dir, exist_ok=True)
        
        # 1. Write the improved data to a temporary JSON file
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        # 2. Call Node.js to generate the document
        try:
            # Command: node utils/docx_generator.js <data.json> <style> <output_dir>
            cmd = ["node", str(JS_GENERATOR), data_path, style, out_dir]
            logger.info(f"RUNNING NODE DOCX: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=False, # We handle check manually to get stderr
                env=os.environ.copy(),
                cwd=str(Path(__file__).parent.parent)
            )

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                logger.error(f"NODE GEN ERROR (Exit {result.returncode}): {error_msg}")
                raise RuntimeError(f"Node.js Word generation failed (Exit {result.returncode}): {error_msg}")
            
            # 3. Read the generated file from the output directory
            # The JS script prints the resulting file path to stdout
            out_file = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
            if not out_file or not os.path.exists(out_file):
                # Fallback check in out_dir
                out_file = os.path.join(out_dir, f"cv_{style}.docx")
                
            if os.path.exists(out_file):
                print(f">>> [DOCX BRIDGE] Success: Generated {out_file}", flush=True)
                with open(out_file, "rb") as f:
                    return f.read()
            else:
                raise FileNotFoundError(f"Generated file not found at {out_file}. Output was: {result.stdout}")
                
        except Exception as e:
            logger.error(f"DOCX BRIDGE ERROR: {e}")
            raise Exception(f"Failed to bridge to Node.js for Word generation: {e}")

# This orchestrator remains the same for the web_app.py integration
# It just routes to the bridge instead of local python builders.