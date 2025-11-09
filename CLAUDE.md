# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyUI is a powerful node-based visual AI engine for designing and executing stable diffusion pipelines. It supports multiple AI model types (image, video, audio, 3D) through a graph/flowchart interface. The codebase is highly modular with support for custom extensions and efficient memory management for large models.

## Running ComfyUI

This installation uses a desktop launcher and virtual environment.

Launch via application launcher:
```bash
# Press Super+Space and type "comfyui"
# Or run directly:
comfyui
```

The launcher script (`/home/jrwhip/.local/bin/comfyui`) executes:
```bash
cd ~/.local/share/comfyui
./venv/bin/python main.py "$@"
```

Run manually with options:
```bash
cd ~/.local/share/comfyui
./venv/bin/python main.py [options]
```

Common development options:
```bash
# Run with high-quality previews
./venv/bin/python main.py --preview-method taesd

# Run with CPU only (for testing without GPU)
./venv/bin/python main.py --cpu

# Enable verbose logging
./venv/bin/python main.py --verbose DEBUG

# Disable custom nodes (for testing core functionality)
./venv/bin/python main.py --disable-all-custom-nodes

# Listen on specific address
./venv/bin/python main.py --listen 127.0.0.1 --port 8188
```

## Testing

Run unit tests:
```bash
cd ~/.local/share/comfyui
./venv/bin/python -m pytest tests-unit/
```

Run specific test:
```bash
./venv/bin/python -m pytest tests-unit/comfy_test/ -v
```

## Code Quality

Linting with ruff:
```bash
cd ~/.local/share/comfyui
./venv/bin/python -m ruff check .
```

The project uses ruff for linting. Key rules enforced:
- F series (Pyflakes): syntax errors and undefined names
- T: print usage warnings
- S307: suspicious eval usage
- N805: invalid first argument name for methods

## Architecture Overview

### Entry Point and Server

**main.py** is the entry point:
- Initializes logging, loads custom paths and prestartup scripts
- Creates `PromptServer` (aiohttp-based web/WebSocket server)
- Loads custom nodes via `nodes.init_extra_nodes()`
- Starts background thread running `prompt_worker()` for execution queue
- Starts HTTP server at http://127.0.0.1:8188

**server.py** - `PromptServer` class:
- WebSocket endpoint: `/ws` for real-time communication
- REST API endpoints for prompts, queue, history, models
- Routes work with both `/` and `/api/` prefixes

### Node System

**Core concepts:**
- Nodes are Python classes defining `INPUT_TYPES()`, `RETURN_TYPES`, and a `FUNCTION` method
- `NODE_CLASS_MAPPINGS`: Global dict mapping node type names to classes
- `NODE_DISPLAY_NAME_MAPPINGS`: Maps internal names to display names
- Two APIs: V1 (legacy) and V3 (modern with `comfy_entrypoint()`)

**Built-in nodes:**
- `nodes.py` - Core built-in nodes (Load Checkpoint, KSampler, etc.)
- `comfy_extras/` - Additional built-in nodes (80+ files for various models/features)
- `comfy_api_nodes/` - Cloud API integration nodes (OpenAI, Runway, etc.)

**Custom nodes:**
- Located in `custom_nodes/` directory
- Define `NODE_CLASS_MAPPINGS` (V1 API) or `comfy_entrypoint()` (V3 API)
- Can include web extensions via `WEB_DIRECTORY`
- Loaded automatically on server startup
- Require server restart after changes

### Execution System

**execution.py** - Main execution logic:
- `PromptQueue`: Thread-safe priority queue for workflow execution
- `PromptExecutor`: Executes workflows in topological order
- `DynamicPrompt`: Tracks original + runtime-generated nodes
- `ExecutionList`: Determines execution order via topological sort

**Execution flow:**
1. Workflow submitted via `/prompt` endpoint → validated
2. Added to `PromptQueue` (supports priority via "front" flag)
3. Background `prompt_worker` thread picks from queue
4. `PromptExecutor.execute()` creates execution plan
5. Nodes executed in topological order
6. Results cached, progress sent via WebSocket to browser

**comfy_execution/** - Modern execution engine:
- `graph.py` - Graph management and validation
- `caching.py` - Cache strategies: Classic, LRU, RAMPressure, None
- `progress.py` - Per-node progress tracking
- Supports async node functions and lazy input evaluation

### Model Loading System

**folder_paths.py** - Model discovery:
- `folder_names_and_paths`: Maps model types to (paths, extensions)
- Default types: checkpoints, loras, vae, clip, controlnet, upscale_models, etc.
- Recursive directory scanning with caching
- Custom paths via `extra_model_paths.yaml`

**comfy/model_management.py** - Memory management:
- VRAM state detection: DISABLED, NO_VRAM, LOW_VRAM, NORMAL_VRAM, HIGH_VRAM, SHARED
- Smart model offloading between GPU/CPU based on available VRAM
- Supports backends: CUDA, ROCm, DirectML, MPS, XPU
- Unloads unused models automatically to free memory

**comfy/model_patcher.py** - Model patching:
- Applies LoRAs, patches, and hooks without modifying base weights
- Lazy loading for memory efficiency
- Clone and patch operations for model variants

**comfy/supported_models.py** - Model architectures:
- Defines configs for SD1.x, SD2.x, SDXL, SD3, Flux, Stable Cascade, and many more
- Each specifies UNET config, VAE, CLIP encoders, and latent format

### Key Directories

- `/comfy/` - Core backend: model loading, sampling, CLIP, VAE, LoRA, ControlNet
- `/comfy_execution/` - Execution engine: graph management, caching, validation
- `/comfy_extras/` - Built-in extension nodes (nodes for various AI models)
- `/comfy_api/` - V3 API system for defining nodes
- `/comfy_api_nodes/` - Cloud API integration nodes
- `/comfy_config/` - Configuration management
- `/app/` - Application layer: users, models, custom nodes management
- `/api_server/` - Additional REST API routes and services
- `/middleware/` - HTTP middleware (CORS, caching, compression)
- `/custom_nodes/` - User-installed extensions
- `/models/` - Model storage (checkpoints, loras, vae, etc.)
- `/input/` - Input files (images, videos for workflows)
- `/output/` - Generated outputs
- `/temp/` - Temporary files
- `/user/` - User-specific settings
- `/web/` - Frontend assets (built-in, not for development)
- `/venv/` - Python virtual environment

### WebSocket Communication

- Feature flag negotiation on connection
- Binary events for preview images with metadata
- JSON events for status, progress, execution results
- Client-specific messages using session IDs

### Caching Strategies

Configure with command-line flags:
- `--cache-classic` - Basic node-ID based caching (default)
- `--cache-lru SIZE` - Least-recently-used with size limit
- `--cache-ram SIZE` - Evicts based on available RAM
- `--cache-none` - Disables caching

### Memory Management

Key flags for memory control:
- `--gpu-only` - Keep everything in GPU VRAM
- `--highvram` - GPU for everything, minimal offloading
- `--normalvram` - Default balanced mode
- `--lowvram` - Aggressive CPU offloading
- `--novram` - CPU-only for VRAM
- `--cpu` - CPU-only processing (no GPU)
- `--reserve-vram SIZE` - Reserve VRAM amount
- `--async-offload` - Async model offloading
- `--disable-pinned-memory` - Disable pinned memory (slower but less VRAM)

### Cross-Attention Options

- `--use-pytorch-cross-attention` - Standard PyTorch implementation
- `--use-split-cross-attention` - Split for low VRAM
- `--use-quad-cross-attention` - Quad-split for very low VRAM
- `--use-flash-attention` - Fast flash attention (if supported)
- `--use-sage-attention` - Sage attention implementation
- `--disable-xformers` - Disable xformers if causing issues

## Model File Locations

Place model files in subdirectories under `models/`:
- `models/checkpoints/` - Main model checkpoints (.ckpt, .safetensors)
- `models/loras/` - LoRA files
- `models/vae/` - VAE models
- `models/clip/` - CLIP models
- `models/controlnet/` - ControlNet models
- `models/upscale_models/` - ESRGAN and other upscalers
- `models/embeddings/` - Textual inversion embeddings
- `models/vae_approx/` - TAESD preview decoders (for `--preview-method taesd`)

Configure additional model paths in `extra_model_paths.yaml`.

## Development Workflow

**Modifying core nodes:**
1. Core nodes are in `nodes.py` and `comfy_extras/`
2. Changes require server restart
3. Test with `--disable-all-custom-nodes` to isolate changes

**Creating custom nodes:**
1. Create directory in `custom_nodes/`
2. Define `NODE_CLASS_MAPPINGS` (V1 API) or `comfy_entrypoint()` (V3 API)
3. Optionally add `WEB_DIRECTORY` for frontend extensions
4. Restart server to load

**Debugging:**
1. Use `--verbose DEBUG` for detailed logging
2. Check `/tmp/comfyui.log` for startup logs (when launched via desktop)
3. Check browser console for frontend errors
4. WebSocket messages visible in browser DevTools Network tab
5. Use `pytest` for unit testing changes

**Working with the virtual environment:**
```bash
# Activate venv
source ~/.local/share/comfyui/venv/bin/activate

# Install new dependencies
pip install package-name

# Update requirements.txt if needed
pip freeze > requirements.txt

# Deactivate when done
deactivate
```

## Important Implementation Patterns

**Execution is asynchronous:**
- The `prompt_worker` thread handles execution queue
- WebSocket sends real-time progress updates
- Nodes can define async functions for async execution

**Lazy evaluation:**
- Optional inputs only evaluated if needed
- Subgraphs can be dynamically expanded during execution

**Graph caching:**
- Only re-executes nodes that changed or depend on changed nodes
- Caching behavior configurable with `--cache-*` flags

**Model memory management:**
- Models loaded on-demand
- Automatic unloading when VRAM pressure detected
- Can pin models to prevent unloading

## History and Saved Workflows

**Execution history (in-memory only):**
- Stored by `PromptQueue` in execution.py
- Maximum 10,000 executions
- NOT persisted to disk - cleared on server restart
- Access via:
  - Web UI: Press `H` key
  - API: `GET http://127.0.0.1:8188/history`
  - API: `GET http://127.0.0.1:8188/history/{prompt_id}`

**Saved workflows:**
- Directory: `user/default/workflows/`
- Format: JSON files
- Save from web UI with Ctrl+S

**Workflows embedded in generated PNGs:**
- Every generated PNG in `output/` contains full workflow metadata
- Extract workflow from PNG:
  ```bash
  ./venv/bin/python extract_workflow.py output/ComfyUI_00001_.png
  # Or save to file:
  ./venv/bin/python extract_workflow.py output/ComfyUI_00001_.png workflow.json
  ```
- Or simply drag PNG into web UI to reload the workflow

## Python Version

This installation uses Python 3.13 (in venv). ComfyUI supports:
- Python 3.13: Very well supported (current)
- Python 3.12: Well supported
- Python 3.9+: Minimum requirement

## GPU Support

Configure PyTorch for your GPU:
- **NVIDIA**: CUDA backend (check `torch.cuda.is_available()`)
- **AMD**: ROCm backend
- **Intel**: XPU backend
- **Apple Silicon**: MPS backend
- **CPU fallback**: Use `--cpu` flag
