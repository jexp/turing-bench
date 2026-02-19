#!/usr/bin/env python3

import time
from abc import ABC
from typing import List

from turingbench.abstract_driver import AbstractDriver, BenchmarkResult


class AbstractWarmupDriver(AbstractDriver, ABC):
    """Abstract base class for database benchmarking with warmups"""

    def __init__(self, warmups: int = 0):
        super().__init__()
        self.warmups = warmups

    def run_queries(self, queries: List[str], runs: int = 1) -> BenchmarkResult:
        """
        Run benchmark queries multiple times and collect timing data.
        This method is generic and doesn't need to be overridden.
        """
        res = BenchmarkResult()

        for query in queries:
            print(f"Running benchmarks for: {query}")
            for _ in range(self.warmups):
                _ = self.execute_query(query)

            for _ in range(1, runs + 1):
                query_timer = time.perf_counter_ns()
                result = self.execute_query(query)
                elapsed_us = (
                    time.perf_counter_ns() - query_timer
                ) // 1_000  # microseconds

                res.query_times.setdefault(query, []).append(elapsed_us)

                if query not in res.query_sizes:
                    res.query_sizes[query] = len(result)

        return res
