# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Repeat the two unstable pyogrio readers in one Python process."""

import argparse
import faulthandler
import gc
import importlib.util
from pathlib import Path

import sedonadb


def load_test_module(test_file: Path):
    spec = importlib.util.spec_from_file_location("sedonadb_test_pyogrio", test_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load tests from {test_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_with_traceback_deadline(function, connection, timeout_seconds: int) -> None:
    faulthandler.dump_traceback_later(timeout_seconds, repeat=False)
    try:
        function(connection)
    finally:
        faulthandler.cancel_dump_traceback_later()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-file", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, required=True)
    parser.add_argument("--faulthandler-timeout", type=int, required=True)
    args = parser.parse_args()

    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    if args.faulthandler_timeout < 1:
        parser.error("--faulthandler-timeout must be positive")

    faulthandler.enable(all_threads=True)
    tests = load_test_module(args.test_file)
    connection = sedonadb.connect()

    for iteration in range(1, args.repetitions + 1):
        print(f"in-process iteration {iteration}/{args.repetitions}", flush=True)
        run_with_traceback_deadline(
            tests.test_read_ogr_multi_file,
            connection,
            args.faulthandler_timeout,
        )
        run_with_traceback_deadline(
            tests.test_read_ogr_partitioned,
            connection,
            args.faulthandler_timeout,
        )
        gc.collect()


if __name__ == "__main__":
    main()
