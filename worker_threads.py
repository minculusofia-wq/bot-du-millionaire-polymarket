# -*- coding: utf-8 -*-
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List
class WorkerThreadPool:
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    def submit_trader_task(self, trader_address: str, callback: Callable, *args):
        return self.executor.submit(callback, trader_address, *args)
    def submit_batch_tasks(self, tasks: List[Dict]) -> Dict:
        futures = {task['trader']: self.executor.submit(task['callback'], task['trader'], *task.get('args', [])) for task in tasks}
        results = {}
        for trader, future in futures.items():
            try:
                results[trader] = future.result(timeout=5)
            except Exception as e:
                results[trader] = {'error': str(e)[:50]}
        return results
    def shutdown(self):
        self.executor.shutdown(wait=False)
worker_pool = WorkerThreadPool(max_workers=10)
