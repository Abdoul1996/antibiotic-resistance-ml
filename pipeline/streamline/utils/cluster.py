import os
import sys
import time
import subprocess
from typing import Optional

import dask.config
from dask.distributed import Client
from dask_jobqueue import SLURMCluster


def _print_squeue_for_user() -> None:
    """Print current SLURM jobs for the user (best-effort)."""
    username = os.getenv("USER") or os.getenv("USERNAME")
    if not username:
        return

    try:
        result = subprocess.run(
            ["squeue", "-u", username],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print("\nCurrent SLURM jobs:")
            print(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # squeue not available or command timed out
        pass


def get_cluster(
    cluster_type: str = "SLURM",
    output_path: str = ".",
    queue: str = "cpucluster",
    memory: int = 32,     # GB per worker (128 CPUs × 1GB per CPU)
    cores: int = 16,      # CPUs per worker (128 CPUs per node)
    n_workers: int = 2,    # number of workers / jobs (3 nodes)
    walltime: str = "17:00:00",
    show_job_script: bool = True,
    wait_for_workers: bool = True,
    max_wait_time: int = 300,   # seconds
) -> Client:
    if cluster_type != "SLURM":
        raise ValueError("Only 'SLURM' cluster_type is supported in this setup.")

    # Sanity checks
    if memory <= 0:
        memory = 32
    if cores <= 0:
        cores = 1
    if n_workers <= 0:
        n_workers = 1

    # Configure Dask networking + retries
    dask.config.set({
        "distributed.comm.timeouts.connect": "60s",
        "distributed.comm.timeouts.tcp": "60s",
        "distributed.comm.retry.count": 3,
        "distributed.scheduler.allowed-failures": 3,
        "distributed.comm.compression": "auto",
        "distributed.comm.max-shard-size": "2GB",
        # Prevent workers from being removed when idle
        "distributed.scheduler.worker-ttl": None,  # Don't remove idle workers
        "distributed.worker.timeout": "60s",  # Keep workers alive
    })

    memory_str = f"{memory}GB"

    try:
        # Create the SLURM-backed Dask cluster
        cluster = SLURMCluster(
            queue=queue,
            cores=cores,
            processes=1,               # one worker process per SLURM job
            memory=memory_str,         # Dask memory limit per worker
            walltime=walltime,
            log_directory=os.path.join(output_path, "dask_logs"),
            job_extra=[
                "--mem=0",             # SLURM: let Dask manage memory inside job
                f"--cpus-per-task={cores}",
                f"--time={walltime}",
                "--export=ALL",
                # Prevent SLURM from killing idle workers
                "--signal=B:USR1@60",  # Send signal before killing (gives workers time to clean up)
            ],
            # Use the same Python (and env) as this script
            python=sys.executable,
            nanny=False,
            # Prevent automatic scaling down
            silence_logs=False,  # Keep logs to debug issues
        )

        if show_job_script:
            print("\n===== DASK SLURM JOB SCRIPT =====")
            print(cluster.job_script())
            print("=================================\n")

        # Connect client to the cluster
        client = Client(
            cluster,
            timeout="100s",
            set_as_default=True,
        )

        print("Creating SLURM Dask cluster...")
        print(f"  Queue        : {queue}")
        print(f"  Workers      : {n_workers}")
        print(f"  Cores/worker : {cores}")
        print(f"  Mem/worker   : {memory} GB")
        print(f"  Scheduler    : {cluster.scheduler_address}")

        # Start the requested number of workers
        print(f"\nRequesting {n_workers} workers from SLURM...")
        cluster.scale(n_workers)

        # Give SLURM more time for workers to start and connect
        print("Waiting for SLURM to allocate workers...")
        time.sleep(10)  # Increased from 5 to 10 seconds
        _print_squeue_for_user()
        
        # Verify workers are actually requested
        try:
            pending_jobs = len(cluster.pending_jobs)
            running_jobs = len(cluster.running_jobs)
            print(f"SLURM cluster status: {running_jobs} running, {pending_jobs} pending")
        except Exception as e:
            print(f"Could not check cluster status: {e}")

        if wait_for_workers:
            print(f"\nWaiting for up to {max_wait_time}s for workers to connect...")
            start = time.time()

            while True:
                try:
                    num_workers = len(client.scheduler_info().get("workers", {}))
                    # Also check how many workers are actually requested
                    requested_workers = len(cluster.workers)
                except Exception as exc:
                    print(f"  Warning: error checking workers: {exc}")
                    num_workers = 0
                    requested_workers = 0

                if num_workers >= n_workers:
                    print(f"  ✓ {num_workers}/{n_workers} workers connected.")
                    break

                elapsed = time.time() - start
                if elapsed >= max_wait_time:
                    print(
                        f"  ⚠ Timeout: only {num_workers}/{n_workers} workers "
                        f"connected after {int(elapsed)}s."
                    )
                    print(f"  Requested workers: {requested_workers}, Connected: {num_workers}")
                    print(f"  Note: Pipeline will continue with {num_workers} worker(s).")
                    break

                print(f"  {num_workers}/{n_workers} workers connected (requested: {requested_workers})... retrying in 5s")
                time.sleep(5)

        # Final summary
        connected = len(client.scheduler_info().get("workers", {}))
        try:
            # Check actual SLURM jobs
            running_jobs = len(cluster.running_jobs) if hasattr(cluster, 'running_jobs') else 0
            pending_jobs = len(cluster.pending_jobs) if hasattr(cluster, 'pending_jobs') else 0
        except:
            running_jobs = 0
            pending_jobs = 0
            
        print("\nCluster ready.")
        print(f"  Dashboard : {client.dashboard_link}")
        print(f"  Workers   : {connected}/{n_workers} connected")
        print(f"  SLURM jobs: {running_jobs} running, {pending_jobs} pending")
        
        if connected < n_workers:
            print(f"  ⚠ Warning: Only {connected} of {n_workers} workers connected.")
            if running_jobs < n_workers:
                print(f"  ⚠ Only {running_jobs} SLURM jobs running. Check queue for issues.")
            print(f"  Pipeline will continue, but processing may be slower.")
        
        # Store cluster reference to prevent garbage collection
        # This helps keep workers alive
        if not hasattr(get_cluster, '_cluster_refs'):
            get_cluster._cluster_refs = []
        get_cluster._cluster_refs.append(cluster)

        return client

    except Exception as exc:
        print(f"Error creating Dask cluster: {exc!r}")
        raise
