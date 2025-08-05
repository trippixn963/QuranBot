# =============================================================================
# QuranBot - Test Runner
# =============================================================================
# Test runner script for executing tests with different configurations
# and generating comprehensive test reports.
# =============================================================================

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


def run_tests(
    categories: Optional[List[str]] = None,
    markers: Optional[List[str]] = None,
    verbose: bool = False,
    coverage: bool = False,
    parallel: bool = False,
    output_file: Optional[str] = None
) -> int:
    """
    Run tests with specified configuration.
    
    Args:
        categories: List of test categories to run
        markers: List of pytest markers to include
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        parallel: Run tests in parallel
        output_file: Output file for test results
        
    Returns:
        Exit code from pytest
    """
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd.append("tests/")
    
    # Add categories if specified
    if categories:
        for category in categories:
            cmd.extend(["-m", category])
    
    # Add markers if specified
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add output file
    if output_file:
        cmd.extend(["--junitxml", output_file])
    
    # Add additional useful flags
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    print(f"Running tests with command: {' '.join(cmd)}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def run_unit_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run unit tests only."""
    return run_tests(
        markers=["unit"],
        verbose=verbose,
        coverage=coverage
    )


def run_integration_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run integration tests only."""
    return run_tests(
        markers=["integration"],
        verbose=verbose,
        coverage=coverage
    )


def run_core_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run core functionality tests."""
    return run_tests(
        categories=["core", "config", "logging", "errors"],
        verbose=verbose,
        coverage=coverage
    )


def run_service_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run service tests."""
    return run_tests(
        categories=["services"],
        verbose=verbose,
        coverage=coverage
    )


def run_bot_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run bot functionality tests."""
    return run_tests(
        categories=["bot"],
        verbose=verbose,
        coverage=coverage
    )


def run_all_tests(verbose: bool = False, coverage: bool = False, parallel: bool = False) -> int:
    """Run all tests."""
    return run_tests(
        verbose=verbose,
        coverage=coverage,
        parallel=parallel
    )


def run_performance_tests(verbose: bool = False) -> int:
    """Run performance tests."""
    return run_tests(
        markers=["performance"],
        verbose=verbose
    )


def run_reliability_tests(verbose: bool = False) -> int:
    """Run reliability tests."""
    return run_tests(
        markers=["reliability"],
        verbose=verbose
    )


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="QuranBot Test Runner")
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    
    parser.add_argument(
        "--core",
        action="store_true",
        help="Run core functionality tests"
    )
    
    parser.add_argument(
        "--services",
        action="store_true",
        help="Run service tests"
    )
    
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Run bot functionality tests"
    )
    
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests"
    )
    
    parser.add_argument(
        "--reliability",
        action="store_true",
        help="Run reliability tests"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Enable coverage reporting"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for test results"
    )
    
    parser.add_argument(
        "--categories",
        nargs="+",
        help="Specific test categories to run"
    )
    
    parser.add_argument(
        "--markers",
        nargs="+",
        help="Specific pytest markers to include"
    )
    
    args = parser.parse_args()
    
    # Determine which tests to run
    if args.unit:
        exit_code = run_unit_tests(args.verbose, args.coverage)
    elif args.integration:
        exit_code = run_integration_tests(args.verbose, args.coverage)
    elif args.core:
        exit_code = run_core_tests(args.verbose, args.coverage)
    elif args.services:
        exit_code = run_service_tests(args.verbose, args.coverage)
    elif args.bot:
        exit_code = run_bot_tests(args.verbose, args.coverage)
    elif args.performance:
        exit_code = run_performance_tests(args.verbose)
    elif args.reliability:
        exit_code = run_reliability_tests(args.verbose)
    elif args.all:
        exit_code = run_all_tests(args.verbose, args.coverage, args.parallel)
    elif args.categories or args.markers:
        exit_code = run_tests(
            categories=args.categories,
            markers=args.markers,
            verbose=args.verbose,
            coverage=args.coverage,
            parallel=args.parallel,
            output_file=args.output
        )
    else:
        # Default: run all tests
        exit_code = run_all_tests(args.verbose, args.coverage, args.parallel)
    
    # Print summary
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main()) 