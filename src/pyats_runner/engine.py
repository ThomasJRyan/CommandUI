import logging
import asyncio
import subprocess
import dataclasses

from uuid import uuid4

from typing import AsyncGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@dataclasses.dataclass
class JobData:
    id: str
    command: tuple
    process: asyncio.subprocess.Process
    stdout_buffer: str = ""
    stderr_buffer: str = ""

class Engine:
    def __init__(self):
        self.job_queue = asyncio.Queue()
        self.running_jobs: dict[str, JobData] = {}

    async def queue_job(self, job_cmd: tuple) -> str:
        """Queue a new job for execution."""
        job_id = str(uuid4())
        await self.job_queue.put((job_id, job_cmd))
        return job_id

    async def process_job(self, job_id: str, job_cmd: tuple) -> str:
        """
        Process a single job from the queue.
        This method runs the job command in a subprocess.
        
        Arguments:
            job_cmd (tuple): The command to execute the job

        Returns:
            str: A unique job ID for tracking the job
        """

        process = await asyncio.create_subprocess_exec(
            *job_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.running_jobs[job_id] = JobData(
            id=job_id,
            command=job_cmd,
            process=process
        )

        return job_id
    
    async def get_job_output(self, job_id: str) -> AsyncGenerator[str, None]:
        """Retrieve the stdout and stderr output of a running job."""
        if job_id not in self.running_jobs:
            raise ValueError(f"Job {job_id} not found")

        job_data = self.running_jobs[job_id]
        process = job_data.process

        if job_data.stdout_buffer:
            yield job_data.stdout_buffer

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode()
            job_data.stdout_buffer += decoded_line
            yield decoded_line
    
    async def run_forever(self):
        """Main loop to continuously check for and process jobs."""

        while True:
            logger.debug("Engine loop iteration")
            if self.job_queue.qsize():
                job_data = await self.job_queue.get()
                asyncio.create_task(self.process_job(*job_data))
                self.job_queue.task_done()

            for job_id, job_data in self.running_jobs.copy().items():
                retcode = job_data.process.returncode
                if retcode is not None:
                    del self.running_jobs[job_id]


            await asyncio.sleep(1)  # Prevent tight loop