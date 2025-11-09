#!/usr/bin/env python3
"""Extract workflow from ComfyUI-generated PNG files."""

import sys
import json
from pathlib import Path
from PIL import Image

def extract_workflow(png_path, output_path=None):
    """Extract workflow metadata from PNG file."""
    img = Image.open(png_path)

    if 'workflow' in img.info:
        workflow = json.loads(img.info['workflow'])

        if output_path:
            with open(output_path, 'w') as f:
                json.dump(workflow, f, indent=2)
            print(f"Workflow saved to: {output_path}")
        else:
            print(json.dumps(workflow, indent=2))
        return workflow
    else:
        print(f"No workflow metadata found in {png_path}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_workflow.py <image.png> [output.json]")
        print("\nExample:")
        print("  python extract_workflow.py output/ComfyUI_00001_.png")
        print("  python extract_workflow.py output/ComfyUI_00001_.png workflow.json")
        sys.exit(1)

    png_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    extract_workflow(png_path, output_path)
