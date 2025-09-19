from .core import Job, JOBS, QUEUE
from .broadcast import broadcast
from stores.core import get_store
import asyncio


async def worker():
    while True:
        task = await QUEUE.get()

        # --- Graph-building job ---
        if isinstance(task, tuple) and task[0] == "build_graph":
            _, params, job_id = task
            job = JOBS[job_id]
            job.status = "processing"
            job.log("Graph build started.")
            job.save()
            await broadcast(job)

            try:
                s = get_store(params["store"])
                await s.build_graph(
                    k=params.get("k", 10),
                    efConstruction=params.get("efConstruction", 200),
                    M=params.get("M", 32),
                    job=job,
                )

                job.status = "done"
                job.log("Graph build finished successfully.")
                job.save()
                await broadcast(job)

            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                job.log(f"Graph build failed: {e}")
                job.save()
                await broadcast(job)

            finally:
                QUEUE.task_done()
                continue

        # --- Ingestion job ---
        job: Job = task
        job.status = "processing"
        job.log("Job resumed." if job.processed > 0 else "Job started.")
        job.save()
        await broadcast(job)

        try:
            s = get_store(job.store)

            # 1. Reconcile index with existing entries
            await s.reconcile_index(
                batch_size=getattr(job, "batch_size", 64),
                job=job,
            )

            # 2. Count already persisted lines
            already = len(s.get_all())

            # 3. Read upload file, skip already-ingested lines
            lines = await asyncio.to_thread(
                lambda: [ln.strip() for ln in open(job.path, "r") if ln.strip()]
            )
            remaining = lines[already:]

            # 4. Ingest remainder incrementally
            await s.add_texts(
                remaining,
                batch_size=getattr(job, "batch_size", 64),
                job=job,
            )

            job.status = "done"
            job.log("Ingestion finished successfully.")
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
