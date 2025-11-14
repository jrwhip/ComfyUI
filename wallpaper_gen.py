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
    """Use Gemini CLI to generate a varied noir city scene for the character."""
    log(f"Generating scene variation with Gemini for: {character['name']}...")

    # Add random seed to prevent Gemini from caching the same response
    random_seed = random.randint(1, 999999)

    # Build character description from character dict
    char_desc = f"- {character['hair']}, {character['eyes']}\n"
    char_desc += f"- {character['age']}, {character['build']}\n"
    if 'ethnicity' in character:
        char_desc += f"- {character['ethnicity']}\n"
    char_desc += f"- {character['vibe']} vibe\n"
    char_desc += f"- {character['footwear']}\n"
    if 'clothing' in character:
        char_desc += f"- {character['clothing']}\n"
    else:
        char_desc += "- Clothing varies (casual/street wear)\n"

    # Handle footwear visibility instruction
    if character['footwear'] == 'barefoot':
        footwear_instruction = "Make her bare feet visible."
    else:
        footwear_instruction = f"Make her {character['footwear']} visible."

    # Build a concise prompt (long prompts cause gemini to timeout)
    char_summary = f"{character['age']}, {character['hair']}, {character['eyes']}, {character['vibe']}, {character['footwear']}"
    if 'ethnicity' in character:
        char_summary = f"{character['ethnicity']}, " + char_summary

    gemini_prompt = f"""Describe a noir anime city wallpaper scene (1280x720). Character: {char_summary}. Vary location, weather, lighting, pose. Cool blue/gray tones with neon accents. Show footwear. 100-120 words."""

    try:
        # Run gemini from a different directory to avoid workspace detection
        result = subprocess.run(
            ['gemini', '-p', gemini_prompt],
            capture_output=True,
            text=True,
            cwd='/tmp',  # Run from /tmp to avoid comfyui directory being detected as a project
            timeout=30
        )

        if result.returncode == 0:
            generated_scene = result.stdout.strip()
            # Remove system messages
            lines = generated_scene.split('\n')
            scene_lines = [line for line in lines if not any(x in line.lower() for x in ['loaded', 'credentials', 'ready to assist', 'what can i do'])]
            generated_scene = '\n'.join(scene_lines).strip()

            log(f"Generated scene: {generated_scene[:80]}...")
            return generated_scene
        else:
            log(f"Gemini CLI failed: {result.stderr}")
            return None
    except Exception as e:
        log(f"Error calling Gemini: {e}")
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
        log("Injected dynamic scene into workflow")
    else:
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
