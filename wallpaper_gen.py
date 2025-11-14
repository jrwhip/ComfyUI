"""
Generate a wallpaper using ComfyUI and set it as the system wallpaper.
Integrates with Omarchy theme system.

Usage: ./venv/bin/python wallpaper_gen.py
"""

import json
import urllib.request
import urllib.parse
import websocket
import uuid
import os
import subprocess
import time
import sys
import random
from datetime import datetime

# Configuration
COMFYUI_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_PATH = os.path.join(COMFYUI_DIR, "wallpaper_api.json")
COMFYUI_SERVER = "127.0.0.1:8188"
WALLPAPER_DIR = os.path.expanduser("~/.config/omarchy/backgrounds/comfyui")
WALLPAPER_SYMLINK = os.path.expanduser("~/.config/omarchy/current/background")
LOG_FILE = os.path.join(COMFYUI_DIR, "wallpaper-gen.log")
GEMINI_TIMEOUT = 45  # Timeout in seconds for Gemini CLI calls

# Artist tags to randomly select from
ARTIST_TAGS = [
    "@0202ase",
    "@0002koko",
    "@00kashian00",
    "@0930erina",
    "@0jae",
    "@1=2",
    "@122pxsheol",
    "@159cm",
    "@200f_(nifu)",
    "@218",
    "@2dswirl",
    "@2zuz4hru",
    "@33_gaff",
    "@40hara",
    "@547th_sy",
    "@4b-enpitsu",
    "@987645321o",
    "@a.nori",
    "@abbystea",
    "@abi_(abimel10)",
    "@abpart",
    "@abutomato",
    "@acubi_tomaranai",
    "@adelheid_(moschiola)",
    "@adarin",
    "@adsouto",
    "@adda",
    "@advarcher",
    "@afuro",
    "@afunai",
    "@agahari",
]

# Characters to randomly select from
CHARACTERS = [
    {
        "name": "Red-haired Melancholic Teen",
        "hair": "red hair",
        "eyes": "amber eyes",
        "age": "teen",
        "build": "slender",
        "vibe": "melancholic",
        "footwear": "barefoot",
    },
    {
        "name": "Happy Filipino Woman",
        "hair": "long straight black hair",
        "eyes": "dark brown eyes",
        "age": "23 year old",
        "build": "slender and short",
        "ethnicity": "Filipino",
        "vibe": "happy",
        "footwear": "wearing flip flops",
    },
    {
        "name": "Confident Blonde",
        "hair": "short blonde hair",
        "eyes": "green eyes",
        "age": "early 30s",
        "build": "average build",
        "vibe": "confident",
        "footwear": "wearing combat boots",
    },
    {
        "name": "Mysterious Kimono Girl",
        "hair": "long silvery white hair",
        "eyes": "red eyes",
        "age": "12 year old",
        "build": "slender",
        "vibe": "mysterious",
        "clothing": "Japanese kimono-inspired clothing",
        "footwear": "traditional footwear",
    },
    {
        "name": "Energetic Twin-tails",
        "hair": "pink twin-tailed hair",
        "eyes": "blue eyes",
        "age": "younger teen",
        "build": "petite",
        "vibe": "energetic",
        "footwear": "wearing sneakers",
    },
]

def log(message):
    """Log to both stdout and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + "\n")

def start_comfyui():
    """Start ComfyUI server in background."""
    log("Starting ComfyUI server...")
    proc = subprocess.Popen(
        [os.path.join(COMFYUI_DIR, "venv/bin/python"), "main.py", "--listen", "127.0.0.1"],
        cwd=COMFYUI_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    return proc

def stop_comfyui(proc):
    """Stop ComfyUI server."""
    log("Stopping ComfyUI server...")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        log("ComfyUI didn't stop gracefully, killing...")
        proc.kill()

def wait_for_comfyui(timeout=60):
    """Wait for ComfyUI server to be ready."""
    log("Waiting for ComfyUI server to be ready...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(f"http://{COMFYUI_SERVER}/", timeout=1)
            log("ComfyUI server is ready!")
            return True
        except Exception:
            time.sleep(1)
    log("ERROR: Timeout waiting for ComfyUI server")
    return False

def queue_prompt(prompt, client_id, prompt_id):
    """Submit a prompt to ComfyUI."""
    p = {"prompt": prompt, "client_id": client_id, "prompt_id": prompt_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFYUI_SERVER}/prompt", data=data)
    urllib.request.urlopen(req).read()

def get_image(filename, subfolder, folder_type):
    """Download an image from ComfyUI."""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{COMFYUI_SERVER}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    """Get execution history for a prompt."""
    with urllib.request.urlopen(f"http://{COMFYUI_SERVER}/history/{prompt_id}") as response:
        return json.loads(response.read())

def generate_image(ws, workflow, client_id):
    """Generate an image and return the image data."""
    prompt_id = str(uuid.uuid4())

    log(f"Submitting workflow (prompt_id: {prompt_id})...")
    queue_prompt(workflow, client_id, prompt_id)

    # Wait for execution to complete
    log("Waiting for image generation to complete...")
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    log("Image generation complete!")
                    break

    # Get the generated image
    history = get_history(prompt_id)[prompt_id]
    for node_id in history['outputs']:
        node_output = history['outputs'][node_id]
        if 'images' in node_output:
            for image in node_output['images']:
                log(f"Downloading generated image: {image['filename']}")
                return get_image(image['filename'], image['subfolder'], image['type'])

    return None

def set_wallpaper_swaybg(image_path):
    """Update symlink and restart swaybg with new wallpaper."""
    log(f"Setting wallpaper: {image_path}")

    # Update symlink
    symlink_dir = os.path.dirname(WALLPAPER_SYMLINK)
    os.makedirs(symlink_dir, exist_ok=True)

    if os.path.islink(WALLPAPER_SYMLINK) or os.path.exists(WALLPAPER_SYMLINK):
        os.remove(WALLPAPER_SYMLINK)
    os.symlink(image_path, WALLPAPER_SYMLINK)
    log(f"Updated symlink: {WALLPAPER_SYMLINK} -> {image_path}")

    # Kill existing swaybg
    subprocess.run(['pkill', 'swaybg'], stderr=subprocess.DEVNULL)
    time.sleep(0.5)

    # Start new swaybg
    subprocess.Popen(
        ['swaybg', '-i', WALLPAPER_SYMLINK, '-m', 'fill'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    log("Restarted swaybg with new wallpaper")

def generate_scene_with_gemini(character):
    """
    Use Gemini CLI to generate a varied noir city scene for the character.

    Args:
        character: Dict containing character attributes (name, hair, eyes, etc.)

    Returns:
        str: Generated scene description, or None if generation fails

    Note:
        Uses simplified prompt format to avoid timeouts. Long complex prompts
        (>1000 chars) cause Gemini CLI to hang. Current format completes in 8-20s.
    """
    log(f"Generating scene variation with Gemini for: {character['name']}...")

    # Kill any hung gemini processes from previous failed runs
    try:
        subprocess.run(['pkill', '-9', '-f', 'node.*gemini'],
                      stderr=subprocess.DEVNULL, timeout=2)
        time.sleep(0.3)
    except Exception:
        pass  # Ignore if pkill fails or no processes exist

    # Build a concise prompt (long prompts cause gemini to timeout)
    char_summary = f"{character['age']}, {character['hair']}, {character['eyes']}, {character['vibe']}"
    if 'ethnicity' in character:
        char_summary = f"{character['ethnicity']}, " + char_summary

    # Add footwear instruction conditionally
    if character['footwear'] == 'barefoot':
        footwear_note = "She is barefoot - show her bare feet."
    else:
        footwear_note = f"Show her {character['footwear']}."

    gemini_prompt = f"""Describe ONE noir anime city scene. Character: {char_summary}. {footwear_note} Choose one specific location, weather, lighting, and pose. Cool blue/gray tones with neon. Single cohesive scene, 100 words."""

    try:
        # Run gemini from /tmp to avoid workspace detection
        # Note: Gemini CLI detects project directories and may enter interactive mode
        log(f"Calling Gemini CLI (prompt: {len(gemini_prompt)} chars)...")
        start_time = time.time()

        result = subprocess.run(
            ['gemini', '-p', gemini_prompt],
            capture_output=True,
            text=True,
            cwd='/tmp',
            timeout=GEMINI_TIMEOUT,
            env=os.environ.copy()
        )

        elapsed = time.time() - start_time
        log(f"Gemini CLI completed in {elapsed:.1f}s (exit code: {result.returncode})")

        if result.returncode == 0:
            generated_scene = result.stdout.strip()

            # Remove system/status messages from output
            lines = generated_scene.split('\n')
            filter_keywords = ['loaded', 'credentials', 'ready to assist', 'what can i do',
                             'setup complete', 'ready.', '[warn]', 'warning:', 'shell cwd']
            scene_lines = [line for line in lines
                          if not any(keyword in line.lower() for keyword in filter_keywords)]
            generated_scene = '\n'.join(scene_lines).strip()

            if not generated_scene:
                log("WARNING: Gemini returned empty output after filtering")
                return None

            log(f"Generated scene (full): {generated_scene}")
            return generated_scene
        else:
            log(f"ERROR: Gemini CLI failed with exit code {result.returncode}")
            if result.stderr:
                log(f"Gemini stderr: {result.stderr[:200]}")
            return None

    except subprocess.TimeoutExpired:
        log(f"ERROR: Gemini CLI timed out after {GEMINI_TIMEOUT} seconds")
        # Kill the hung process
        try:
            subprocess.run(['pkill', '-9', '-f', 'node.*gemini'],
                          stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            pass
        return None
    except FileNotFoundError:
        log("ERROR: Gemini CLI not found. Is it installed and in PATH?")
        return None
    except Exception as e:
        log(f"ERROR: Unexpected error calling Gemini: {type(e).__name__}: {e}")
        return None

def load_workflow():
    """Load the workflow JSON file (API format)."""
    log(f"Loading workflow from: {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, 'r') as f:
        workflow = json.load(f)

    # Randomize the seed in the KSampler node (node "3")
    if "3" in workflow and "inputs" in workflow["3"] and "seed" in workflow["3"]["inputs"]:
        new_seed = random.randint(1, 2**32 - 1)
        workflow["3"]["inputs"]["seed"] = new_seed
        log(f"Randomized seed to: {new_seed}")

    # Randomly select a character
    character = random.choice(CHARACTERS)
    log(f"Selected character: {character['name']}")

    # Generate dynamic scene with Gemini
    generated_scene = generate_scene_with_gemini(character)
    if generated_scene and "6" in workflow and "inputs" in workflow["6"]:
        # Randomly select an artist tag
        artist_tag = random.choice(ARTIST_TAGS)
        log(f"Selected artist: {artist_tag}")

        # Build the full prompt with NetaYume format and artist tag
        netayume_prefix = "You are an assistant designed to generate high quality anime images based on textual prompts. <Prompt Start> "
        full_prompt = netayume_prefix + artist_tag + ", " + generated_scene
        workflow["6"]["inputs"]["text"] = full_prompt
        log("Successfully injected Gemini-generated scene into workflow")
    else:
        if not generated_scene:
            log("WARNING: Gemini scene generation failed, falling back to default prompt")
        log("Using default prompt from workflow file")

    log(f"Loaded workflow with {len(workflow)} nodes")
    return workflow

def main():
    log("=== ComfyUI Wallpaper Generator ===")

    # Ensure output directory exists
    os.makedirs(WALLPAPER_DIR, exist_ok=True)

    # Check if workflow exists
    if not os.path.exists(WORKFLOW_PATH):
        log(f"ERROR: Workflow file not found: {WORKFLOW_PATH}")
        return 1

    # Load workflow BEFORE starting ComfyUI (so Gemini can run first)
    workflow = load_workflow()

    # Start ComfyUI
    comfyui_proc = start_comfyui()

    try:
        # Wait for ComfyUI to be ready
        if not wait_for_comfyui():
            log("ERROR: ComfyUI server not available")
            return 1

        # Connect to WebSocket
        client_id = str(uuid.uuid4())
        log("Connecting to ComfyUI WebSocket...")
        ws = websocket.WebSocket()
        ws.connect(f"ws://{COMFYUI_SERVER}/ws?clientId={client_id}")

        try:
            # Generate image
            image_data = generate_image(ws, workflow, client_id)

            if image_data:
                # Save image with timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
                wallpaper_path = os.path.join(WALLPAPER_DIR, f"wallpaper-{timestamp}.png")

                with open(wallpaper_path, 'wb') as f:
                    f.write(image_data)
                log(f"Wallpaper saved to: {wallpaper_path}")

                # Set as wallpaper
                set_wallpaper_swaybg(wallpaper_path)
                log("Wallpaper set successfully!")
                return 0
            else:
                log("ERROR: Failed to generate image")
                return 1

        finally:
            ws.close()

    finally:
        # Always stop ComfyUI
        stop_comfyui(comfyui_proc)
        log("ComfyUI stopped")

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
