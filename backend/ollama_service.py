import os
import subprocess
import asyncio
import threading
import logging

# Configure logging
logging.basicConfig(
    filename='ollama.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables for CUDA
os.environ['PATH'] += ':/usr/local/cuda/bin'
os.environ['LD_LIBRARY_PATH'] = '/usr/lib64-nvidia:/usr/local/cuda/lib64'

def is_ollama_installed():
    """Check if Ollama is installed."""
    try:
        subprocess.run(['ollama', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Ollama is installed.")
        return True
    except FileNotFoundError:
        logger.error("Ollama is not installed. Please install Ollama before proceeding.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking Ollama installation: {e}")
        return False

def are_models_pulled():
    """Check if the required models are pulled in Ollama, and pull them if missing."""
    required_models = ["llama2", "deepseek-coder-1"]
    try:
        result = subprocess.run(['ollama', 'list'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        available_models = result.stdout.decode().strip()

        # Check if both models exist
        missing_models = [model for model in required_models if model not in available_models]

        if not missing_models:
            logger.info("All required models are available.")
            return True
        
        # Pull missing models
        for model in missing_models:
            logger.warning(f"Model {model} is missing. Pulling now...")
            pull_result = subprocess.run(['ollama', 'pull', model], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Successfully pulled {model}: {pull_result.stdout.decode().strip()}")

        return True  # Assume success after pulling missing models

    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking or pulling models: {e}")
        return False

async def run_process(cmd):
    """Run a subprocess asynchronously and stream its output."""
    logger.info('>>> Starting: %s', ' '.join(cmd))
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def pipe(lines, stream_name):
        async for line in lines:
            log_line = line.decode().strip()
            logger.info("[%s] %s", stream_name, log_line)

    await asyncio.gather(
        pipe(process.stdout, "stdout"),
        pipe(process.stderr, "stderr"),
    )

async def start_ollama_serve():
    """Start the Ollama server."""
    if is_ollama_installed() and are_models_pulled():
        await run_process(['ollama', 'serve'])
    else:
        logger.error("Unable to start Ollama server. Ensure Ollama is installed and the required models are pulled.")

def run_async_in_thread(loop, coro):
    """Run an async coroutine in a separate thread."""
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)
    loop.close()

# Create a new event loop that will run in a new thread
new_loop = asyncio.new_event_loop()

# Start Ollama serve in a separate thread
thread = threading.Thread(target=run_async_in_thread, args=(new_loop, start_ollama_serve()))
thread.start()
