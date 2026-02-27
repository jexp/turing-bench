import argparse
from turingbench.neo4j_driver import Neo4jDriver
from turingbench.neo4j_driver_opt import Neo4jOptimizedDriver
from turingbench.neo4j_driver_http import Neo4jHttpDriver
from turingbench.turingdb_driver import TuringDBDriver

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TuringBench tool to run benchmarks on TuringDB, Neo4j and Memgraph"
    )

    bench_group = parser.add_subparsers(dest="benchmark")
    bench_group.add_parser(
        "turingdb",
        parents=[TuringDBDriver.create_argument_parser()],
        add_help=False,
    )

    bench_group.add_parser(
        "memgraph",
        parents=[Neo4jDriver.create_argument_parser()],
        add_help=False,
    )

    bench_group.add_parser(
        "neo4j",
        parents=[Neo4jDriver.create_argument_parser()],
        add_help=False,
    )

    bench_group.add_parser(
        "neo4j_opt",
        parents=[Neo4jOptimizedDriver.create_argument_parser()],
        add_help=False,
    )

    bench_group.add_parser(
        "neo4j_http",
        parents=[Neo4jHttpDriver.create_argument_parser()],
        add_help=False,
    )
    args = parser.parse_args()

    if args.benchmark == "turingdb":
        from turingbench.turingdb_driver import main

        main(args)
    elif args.benchmark == "neo4j":
        from turingbench.neo4j_driver import main

        main(args)
    elif args.benchmark == "neo4j_opt":
        from turingbench.neo4j_driver_opt import main

        main(args)
    elif args.benchmark == "neo4j_http":
        from turingbench.neo4j_driver_http import main

        main(args)
    elif args.benchmark == "memgraph":
        from turingbench.neo4j_driver import main

        main(args)
    else:
        parser.print_help()
        exit(1)
