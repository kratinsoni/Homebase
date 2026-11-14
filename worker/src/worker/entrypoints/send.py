import asyncio
import sys
import uuid

from worker.jobqueue.tasks import broker, run_agent

async def main():
    text = " ".join(sys.argv[1:]) or "Which files are in my workspace?"

    await broker.startup()

    try:
        task = await run_agent.kiq("demo-1", uuid.uuid4(), text)
        print("Job sent. Task id:", task.task_id)
        result = await task.wait_result(timeout=180)
        if result.is_err:
            print("Error: ", result.error)
        else:
            print("Reply: ", result.return_value)

    finally:
        await broker.shutdown()


asyncio.run(main())
