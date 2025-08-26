from .core import Job, QUEUE
from .broadcast import broadcast
from stores.core import get_store
import asyncio

async def worker():
    while True:
        job: Job = await QUEUE.get()
        job.status = "processing"
        job.log("Job resumed." if job.processed > 0 else "Job started.")
        job.save()
        await broadcast(job)

        try:
            # inside your worker, before starting ingestion:
            s = get_store(job.store)

            # 1) Make sure index reflects all entries already on disk
            await s.reconcile_index(batch_size=job.batch_size if hasattr(job, "batch_size") else 64, job=job)

            # 2) Compute how many lines are already persisted as entries
            already = len(s.get_all())

            # 3) Read upload file and skip what’s already persisted
            lines = await asyncio.to_thread(
                lambda: [ln.strip() for ln in open(job.path, "r") if ln.strip()]
            )
            remaining = lines[already:]

            # 4) Now ingest only the remainder (this will persist per batch)
            await s.add_texts(remaining, batch_size=job.batch_size if hasattr(job, "batch_size") else 64, job=job)

            job.status = "done"
            job.log("Job finished successfully.")
            job.save()
            await broadcast(job)

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.log(f"Error: {e}")
            job.save()
            await broadcast(job)

        finally:
            QUEUE.task_done()
