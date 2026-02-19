#!/usr/bin/env python3

import sys
import argparse
from typing import List, Dict, Any, LiteralString, cast

from turingbench.abstract_warmup_driver import AbstractWarmupDriver

from neo4j import GraphDatabase


class Neo4jOptimisedDriver(AbstractWarmupDriver):
    """Neo4j-specific implementation of DatabaseBenchmark"""
    def __init__(self, runtime: str, warmups: int = 0):
        super().__init__(warmups)
        self.parallel = runtime == "parallel"

        if self.parallel:
            print("Using Neo4j Enterprise parallel runtime")

    def connect(
        self, url: str, username: str | None, password: str | None, database: str = "neo4j", auth: bool = True
    ) -> None:
        """Establish connection to Neo4j"""
        try:
            if auth:
                self.driver = GraphDatabase.driver(url, auth=(username, password))
            else:
                self.driver = GraphDatabase.driver(url)

            self.database = database
            print(f"Connected to {url}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            sys.exit(1)

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a Neo4j query and return results"""
        if self.parallel:
            query = f"CYPHER runtime = parallel\n{query}"

        with self.driver.session(database=self.database) as session:
            return [dict(r) for r in session.run(cast(LiteralString, query))]

    def close(self) -> None:
        """Close the Neo4j driver"""
        if hasattr(self, "driver") and self.driver:
            self.driver.close()
            print("Closed Neo4j connection")

    @classmethod
    def add_db_arguments(cls, parser: argparse.ArgumentParser) -> None:
        """Add Neo4j-specific arguments"""
        parser.add_argument(
            "--url",
            "-u",
            default="bolt://localhost:7687",
            help="Neo4j connection URL (default: bolt://localhost:7687)",
        )
        parser.add_argument(
            "--auth", "-a", default=True, help="Use Neo4j authentication"
        )
        parser.add_argument(
            "--username", "-n", default="neo4j", help="Username (default: neo4j)"
        )
        parser.add_argument(
            "--password", "-p", default="neo4j", help="Password (default: neo4j)"
        )
        parser.add_argument(
            "--database", "-g", default="neo4j", help="Database name (default: neo4j)"
        )
        parser.add_argument(
            "--runtime", choices=("slotted", "pipelined", "parallel"), default="slotted", help="Neo4j runtime (default: slotted)"
        )
        parser.add_argument(
            "--warmups", "-w", type=int, default=0, help="The number of warmup runs per benchmark"
        )


def main(args: argparse.Namespace) -> None:
    driver = Neo4jOptimisedDriver(args.runtime, args.warmups)

    try:
        if args.auth:
            driver.connect(
                url=args.url,
                username=args.username,
                password=args.password,
                database=args.database,
            )
        else:
            driver.connect(
                url=args.url,
                username=None,
                password=None,
                database=args.database,
                auth=False
            )

        # Load queries from file
        with open(args.query, "r") as f:
            queries = [line.strip().split(";")[0] for line in f if line.strip()]

        # Run benchmark
        driver.run_benchmark(queries, args.runs)

    finally:
        driver.close()


if __name__ == "__main__":
    parser = Neo4jOptimisedDriver.create_argument_parser(description="Neo4j Benchmarking Tool")
    args = parser.parse_args()

    main(args)
