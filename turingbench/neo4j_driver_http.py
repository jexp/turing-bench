#!/usr/bin/env python3

import sys
import argparse
import json
from typing import List, Dict, Any, Optional

import requests

from turingbench.abstract_warmup_driver import AbstractWarmupDriver


class Neo4jHttpDriver(AbstractWarmupDriver):
    """Neo4j-specific implementation using HTTP commit endpoint"""
    def __init__(self, runtime: str, warmups: int = 0, mode: str = "jolt"):
        super().__init__(warmups)
        self.parallel = runtime == "parallel"
        self.base_url: Optional[str] = None
        self.commit_url: Optional[str] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.use_auth: bool = True
        self.mode = mode
        if self.parallel:
            print("Using Neo4j Enterprise parallel runtime")

    def connect(
        self, url: str, username: Optional[str], password: Optional[str], database: str = "neo4j", auth: bool = True
    ) -> None:
        """Configure HTTP endpoint and authentication for Neo4j commit API"""
        try:
            # Accept bolt:// by converting to http:// if provided
            if url.startswith("bolt://"):
                url = "http://" + url[len("bolt://"):]

            self.base_url = url.rstrip("/")
            self.username = username
            self.password = password
            self.use_auth = auth

            # If user provided a full commit URL, use it; otherwise construct one
            if "/db/" in self.base_url and self.base_url.endswith("/tx/commit"):
                self.commit_url = self.base_url
            else:
                self.commit_url = f"{self.base_url}/db/{database}/tx/commit"

            self.database = database
            print(f"Connected to {self.commit_url}")
        except Exception as e:
            print(f"Failed to configure HTTP connection: {e}")
            sys.exit(1)

    def _post_commit(self, payload: Dict[str, Any]) -> requests.Response:
        if self.mode == "json":
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
            }
        else:
            headers = {
                "accept": "application/vnd.neo4j.jolt-v2+json-seq",
                "content-type": "application/json",
            }

        auth = (self.username, self.password) if self.use_auth and self.username is not None else None
        resp = requests.post(self.commit_url, json=payload, headers=headers, auth=auth, timeout=30)
        resp.raise_for_status()
        return resp

    def _unwrap_jolt_value(self, value: Any) -> Any:
        """Unwrap Jolt type-labeled values to Python types
        
        In sparse mode (default), JSON-compatible types (string, number, boolean, null, array, object)
        are returned without type labels. Only Neo4j-specific types have labels.
        """
        # Handle primitives that are already JSON-compatible (sparse mode)
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        
        # Handle lists - recursively unwrap items
        if isinstance(value, list):
            return [self._unwrap_jolt_value(item) for item in value]
        
        if not isinstance(value, dict):
            return value
        
        # Check for Jolt type labels (single-key dict with specific type markers)
        if len(value) == 1:
            key = next(iter(value))
            val = value[key]
            
            # Base types (these appear in strict mode or for non-JSON types)
            if key == "Z":  # Integer
                return int(val) if isinstance(val, str) else val
            elif key == "R":  # Float
                return float(val) if isinstance(val, str) else val
            elif key == "U":  # String
                return val
            elif key == "?":  # Boolean
                return val == "true" if isinstance(val, str) else bool(val)
            elif key == "T":  # Temporal (keep as string)
                return val
            elif key == "@":  # Spatial (keep as string)
                return val
            elif key == "#":  # Hexadecimal (keep as string)
                return val
            # Composite types
            elif key == "[]":  # List (strict mode)
                return [self._unwrap_jolt_value(item) for item in val] if isinstance(val, list) else val
            elif key == "{}":  # Map (strict mode)
                return {k: self._unwrap_jolt_value(v) for k, v in val.items()} if isinstance(val, dict) else val
            # Entity types - return as-is for now (could expand to structured objects)
            elif key == "()":  # Node
                return value
            elif key == "->":  # Relationship (outgoing)
                return value
            elif key == "<-":  # Relationship (incoming)
                return value
            elif key == "..":  # Path
                return value
        
        # Plain dict without type label (sparse mode) - recursively unwrap values
        return {k: self._unwrap_jolt_value(v) for k, v in value.items()}

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a Cypher query via the HTTP commit endpoint and return results as list of dicts"""
        if self.parallel:
            query = f"CYPHER runtime = parallel\n{query}"

        statement = {"statement": query}
        
        # Add resultDataContents for JSON mode
        if self.mode == "json":
            statement["resultDataContents"] = ["row"]
        
        payload = {"statements": [statement]}

        resp = self._post_commit(payload)

        if self.mode == "json":
            # Parse standard JSON format
            return self._parse_json_response(resp)
        else:
            # Parse jolt-v2+json-seq format (newline-delimited JSON)
            return self._parse_jolt_response(resp)
    
    def _parse_json_response(self, resp: requests.Response) -> List[Dict[str, Any]]:
        """Parse standard JSON response format with results[].columns and results[].data[].row"""
        rows: List[Dict[str, Any]] = []
        
        try:
            body = resp.json()
        except ValueError:
            return rows
        
        # Iterate through results (one per statement)
        for result in body.get("results", []):
            columns = result.get("columns", [])
            
            # Extract rows from data array
            for data_item in result.get("data", []):
                row_values = data_item.get("row", [])
                if columns and row_values:
                    rows.append({columns[i]: row_values[i] for i in range(min(len(columns), len(row_values)))})
        
        return rows
    
    def _parse_jolt_response(self, resp: requests.Response) -> List[Dict[str, Any]]:
        """Parse Jolt v2 JSON sequence format (newline-delimited)"""
        rows: List[Dict[str, Any]] = []
        fields: List[str] = []
        
        for line in resp.text.splitlines():
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except ValueError:
                continue
            
            # Extract field names from header
            if "header" in chunk:
                fields = chunk["header"].get("fields", [])
            
            # Extract data rows - each data line contains an array of type-labeled values
            elif "data" in chunk:
                data_values = chunk["data"]
                if fields and isinstance(data_values, list):
                    # Unwrap Jolt type labels from each value
                    unwrapped_values = [self._unwrap_jolt_value(val) for val in data_values]
                    rows.append({fields[i]: unwrapped_values[i] for i in range(min(len(fields), len(unwrapped_values)))})
        
        return rows

    def close(self) -> None:
        """No persistent driver to close for HTTP client"""
        print("Closed Neo4j HTTP connection")

    @classmethod
    def add_db_arguments(cls, parser: argparse.ArgumentParser) -> None:
        """Add Neo4j-specific arguments (HTTP)"""
        parser.add_argument(
            "--url",
            "-u",
            default="http://localhost:7474",
            help="Neo4j HTTP base URL (default: http://localhost:7474)",
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
            "--runtime", choices=("slotted", "pipelined", "parallel"), default="pipelined", help="Neo4j runtime (default: slotted)"
        )
        parser.add_argument(
            "--mode", choices=("jolt", "json"), default="jolt", help="http response mode"
        )
        parser.add_argument(
            "--warmups", "-w", type=int, default=0, help="The number of warmup runs per benchmark"
        )


def main(args: argparse.Namespace) -> None:
    driver = Neo4jHttpDriver(args.runtime, args.warmups, args.mode)

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
