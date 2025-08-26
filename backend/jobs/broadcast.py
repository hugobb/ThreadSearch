from .core import JOBS, clients, Job

async def broadcast(job: Job):
    """
    Broadcast a job update to all connected websocket clients.
    Also update JOBS dict and persist job to disk.
    """
    # Ensure it's saved + visible in JOBS
    JOBS[job.id] = job
    job.save()

    # Prepare payload
    msg = {"type": "job_update", "job": job.dict()}

    # Broadcast to all connected clients
    dead_clients = []
    for ws in list(clients):
        try:
            await ws.send_json(msg)
        except Exception as e:
            print(f"[broadcast] Failed to send to a client: {e}")
            dead_clients.append(ws)

    # Cleanup broken sockets
    for ws in dead_clients:
        clients.discard(ws)
