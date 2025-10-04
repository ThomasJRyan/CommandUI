import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import WebSocket, WebSocketDisconnect

from starlette.websockets import WebSocketState

from pyats_runner.engine import Engine


class PyATSRunnerAPI(FastAPI):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

@asynccontextmanager
async def lifespan(app: PyATSRunnerAPI):
    app.state.engine = Engine()
    engine_task = asyncio.create_task(app.state.engine.run_forever())
    yield

    engine_task.cancel()
    try:
        await engine_task
    except asyncio.CancelledError:
        pass

app = PyATSRunnerAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/queue_job/")
async def queue_job(job_script: str = "", testbed: str = ""):
    """Endpoint to queue a pyATS job script for execution."""
    job_script = "_testing/jobs/basic_job.py"
    testbed = "_testing/testbeds/local_testbed.yaml"
    # job_cmd = ("pyats", "run", "job", job_script, "--testbed-file", testbed)
    # job_cmd = ("ls", "-l")
    job_cmd = ("bash", "-c", "second=0; while true; do echo \"Hello world $second\"; sleep 1; ((second++)); done")
    job_id = await app.state.engine.queue_job(job_cmd)
    return {"status": "job queued", "job_cmd": job_cmd, "job_id": job_id}

@app.get("/running_jobs/")
async def get_running_jobs():
    """Endpoint to get the list of currently running jobs."""
    running_jobs = list(app.state.engine.running_jobs.keys())
    return {"running_jobs": running_jobs}

@app.websocket("/ws/job_stdout/{job_id}")
async def websocket_job_stdout(websocket: WebSocket, job_id: str):
    await websocket.accept()
    engine = app.state.engine
    
    if job_id not in engine.running_jobs:
        await websocket.send_text(f"Job {job_id} not found.")
        await websocket.close()
        return

    try:
        async for output in engine.get_job_output(job_id):
            if websocket.application_state != WebSocketState.CONNECTED:
                break
            await websocket.send_text(output)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_text(f"Error: {str(e)}")
    finally:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()