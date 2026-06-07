from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def spawn_workers(
    number_of_workers: int, tasks: List[T], common_fn: Callable[[T], R]
) -> List[R]:
    if number_of_workers <= 0:
        raise ValueError("number_of_workers must be greater than 0")

    if not tasks:
        return []

    workers = min(number_of_workers, len(tasks))
    result_by_index: List[Any] = [None] * len(tasks)

    # Split the task list so each worker gets either base_size or base_size + 1 tasks.
    base_size, remainder = divmod(len(tasks), workers)
    ranges = []
    start = 0
    for worker_index in range(workers):
        chunk_size = base_size + (1 if worker_index < remainder else 0)
        end = start + chunk_size
        ranges.append((worker_index, start, end))
        start = end

    def run_chunk(worker_id: int, chunk_start: int, chunk_end: int) -> List[R]:
        chunk_results: List[R] = []
        for task_index in range(chunk_start, chunk_end):
            print(f"[spawn_workers] worker={worker_id} processing task_index={task_index}")
            chunk_results.append(common_fn(tasks[task_index]))
        return chunk_results

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_range = {
            executor.submit(run_chunk, worker_id, chunk_start, chunk_end): (
                worker_id,
                chunk_start,
                chunk_end,
            )
            for worker_id, chunk_start, chunk_end in ranges
        }

        for future in as_completed(future_to_range):
            worker_id, chunk_start, chunk_end = future_to_range[future]
            chunk_results = future.result()
            result_by_index[chunk_start:chunk_end] = chunk_results
            print(
                f"[spawn_workers] worker={worker_id} completed task_indexes={chunk_start}-{chunk_end - 1}"
            )

    return result_by_index