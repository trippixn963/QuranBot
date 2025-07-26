# =============================================================================
# QuranBot - Test Runner and Validation
# =============================================================================
# Comprehensive test runner that validates test suite setup, runs different
# test categories, and provides detailed reporting on test coverage and results.
# =============================================================================

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Optional


def run_command(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    """Run a command and return detailed results."""
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,  # 5 minute timeout
        )

        end_time = time.time()

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": end_time - start_time,
            "command": " ".join(command),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out after 5 minutes",
            "duration": time.time() - start_time,
            "command": " ".join(command),
        }

    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "duration": time.time() - start_time,
            "command": " ".join(command),
        }


class TestRunner:
    """Comprehensive test runner for QuranBot test suite."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_results: dict[str, dict[str, Any]] = {}

    def validate_test_environment(self) -> bool:
        """Validate that the test environment is properly set up."""
        print("🔍 Validating test environment...")

        # Check required files exist
        required_files = [
            "pyproject.toml",
            "tests/conftest.py",
            "tests/__init__.py",
        ]

        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"❌ Missing required files: {missing_files}")
            return False

        # Check that pytest is available
        pytest_check = run_command(["python", "-m", "pytest", "--version"])
        if not pytest_check["success"]:
            print("❌ pytest is not available")
            print(f"Error: {pytest_check['stderr']}")
            return False

        print("✅ Test environment validation passed")
        return True

    def run_unit_tests(self, test_pattern: str = None) -> dict[str, Any]:
        """Run unit tests with optional pattern filtering."""
        print("🧪 Running unit tests...")

        command = [
            "python",
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--durations=10",
            "--strict-markers",
        ]

        if test_pattern:
            command.extend(["-k", test_pattern])

        # Add coverage for unit tests
        command.extend(
            [
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-fail-under=70",  # Require at least 70% coverage
            ]
        )

        result = run_command(command, cwd=self.project_root)
        self.test_results["unit_tests"] = result

        if result["success"]:
            print("✅ Unit tests passed")
        else:
            print("❌ Unit tests failed")
            print(f"Error output: {result['stderr']}")

        return result

    def run_integration_tests(self) -> dict[str, Any]:
        """Run integration tests specifically."""
        print("🔄 Running integration tests...")

        command = [
            "python",
            "-m",
            "pytest",
            "tests/test_integration_comprehensive.py",
            "tests/test_integration.py",
            "-v",
            "--tb=short",
            "-m",
            "not slow",  # Skip slow tests unless specifically requested
        ]

        result = run_command(command, cwd=self.project_root)
        self.test_results["integration_tests"] = result

        if result["success"]:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")
            print(f"Error output: {result['stderr']}")

        return result

    def run_performance_tests(self) -> dict[str, Any]:
        """Run performance and load tests."""
        print("⚡ Running performance tests...")

        command = [
            "python",
            "-m",
            "pytest",
            "tests/test_performance.py",
            "tests/test_core_services.py::TestPerformanceUnderLoad",
            "-v",
            "--tb=short",
            "-m",
            "not slow",
        ]

        result = run_command(command, cwd=self.project_root)
        self.test_results["performance_tests"] = result

        if result["success"]:
            print("✅ Performance tests passed")
        else:
            print("❌ Performance tests failed")
            print(f"Error output: {result['stderr']}")

        return result

    def run_security_tests(self) -> dict[str, Any]:
        """Run security-related tests."""
        print("🔒 Running security tests...")

        command = [
            "python",
            "-m",
            "pytest",
            "tests/test_security.py",
            "tests/test_security_comprehensive.py",
            "-v",
            "--tb=short",
        ]

        result = run_command(command, cwd=self.project_root)
        self.test_results["security_tests"] = result

        if result["success"]:
            print("✅ Security tests passed")
        else:
            print("❌ Security tests failed")
            print(f"Error output: {result['stderr']}")

        return result

    def run_lint_checks(self) -> dict[str, Any]:
        """Run code quality and linting checks."""
        print("🔍 Running code quality checks...")

        # Run mypy type checking
        mypy_result = run_command(
            [
                "python",
                "-m",
                "mypy",
                "src/",
                "--ignore-missing-imports",
                "--show-error-codes",
            ],
            cwd=self.project_root,
        )

        # Run ruff linting
        ruff_result = run_command(
            ["python", "-m", "ruff", "check", "src/", "tests/"], cwd=self.project_root
        )

        # Run black formatting check
        black_result = run_command(
            ["python", "-m", "black", "src/", "tests/", "--check", "--diff"],
            cwd=self.project_root,
        )

        overall_success = (
            mypy_result["returncode"] == 0
            and ruff_result["returncode"] == 0
            and black_result["returncode"] == 0
        )

        result = {
            "success": overall_success,
            "mypy": mypy_result,
            "ruff": ruff_result,
            "black": black_result,
            "duration": sum(
                [
                    mypy_result["duration"],
                    ruff_result["duration"],
                    black_result["duration"],
                ]
            ),
        }

        self.test_results["lint_checks"] = result

        if overall_success:
            print("✅ Code quality checks passed")
        else:
            print("❌ Code quality checks failed")
            if mypy_result["returncode"] != 0:
                print(f"MyPy errors: {mypy_result['stderr']}")
            if ruff_result["returncode"] != 0:
                print(f"Ruff errors: {ruff_result['stderr']}")
            if black_result["returncode"] != 0:
                print(f"Black formatting issues: {black_result['stderr']}")

        return result

    def run_coverage_analysis(self) -> dict[str, Any]:
        """Run detailed coverage analysis."""
        print("📊 Running coverage analysis...")

        command = [
            "python",
            "-m",
            "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=json:coverage.json",
            "--cov-report=xml:coverage.xml",
            "--quiet",
        ]

        result = run_command(command, cwd=self.project_root)

        # Parse coverage results if available
        coverage_data = {}
        coverage_file = self.project_root / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
            except Exception as e:
                print(f"Warning: Could not parse coverage data: {e}")

        result["coverage_data"] = coverage_data
        self.test_results["coverage_analysis"] = result

        if result["success"]:
            total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
            print(f"✅ Coverage analysis completed - {total_coverage:.1f}% coverage")
        else:
            print("❌ Coverage analysis failed")

        return result

    def run_dependency_checks(self) -> dict[str, Any]:
        """Check for dependency issues and security vulnerabilities."""
        print("📦 Checking dependencies...")

        # Check for known security vulnerabilities
        safety_result = run_command(
            ["python", "-m", "pip", "list", "--format=json"], cwd=self.project_root
        )

        # Check for outdated packages
        outdated_result = run_command(
            ["python", "-m", "pip", "list", "--outdated"], cwd=self.project_root
        )

        result = {
            "success": safety_result["success"],
            "safety": safety_result,
            "outdated": outdated_result,
            "duration": safety_result["duration"] + outdated_result["duration"],
        }

        self.test_results["dependency_checks"] = result

        if result["success"]:
            print("✅ Dependency checks completed")
        else:
            print("❌ Dependency checks failed")

        return result

    def generate_test_report(self) -> str:
        """Generate a comprehensive test report."""
        report_lines = [
            "# QuranBot Test Suite Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
        ]

        total_tests = 0
        passed_tests = 0
        total_duration = 0

        for test_category, result in self.test_results.items():
            status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
            duration = result.get("duration", 0)
            total_duration += duration

            report_lines.append(f"- **{test_category}**: {status} ({duration:.2f}s)")

            if result.get("success", False):
                passed_tests += 1
            total_tests += 1

        report_lines.extend(
            [
                "",
                f"**Overall**: {passed_tests}/{total_tests} test categories passed",
                f"**Total Duration**: {total_duration:.2f}s",
                "",
                "## Details",
                "",
            ]
        )

        # Add detailed results for each category
        for test_category, result in self.test_results.items():
            report_lines.extend(
                [
                    f"### {test_category.replace('_', ' ').title()}",
                    f"- **Status**: {'PASSED' if result.get('success', False) else 'FAILED'}",
                    f"- **Duration**: {result.get('duration', 0):.2f}s",
                    f"- **Return Code**: {result.get('returncode', 'N/A')}",
                    "",
                ]
            )

            if result.get("stderr"):
                report_lines.extend(
                    [
                        "**Error Output:**",
                        "```",
                        result["stderr"][:500],  # Limit error output
                        "```",
                        "",
                    ]
                )

        # Add coverage information if available
        if "coverage_analysis" in self.test_results:
            coverage_data = self.test_results["coverage_analysis"].get(
                "coverage_data", {}
            )
            if coverage_data:
                totals = coverage_data.get("totals", {})
                report_lines.extend(
                    [
                        "## Coverage Analysis",
                        f"- **Total Coverage**: {totals.get('percent_covered', 0):.1f}%",
                        f"- **Lines Covered**: {totals.get('covered_lines', 0)}",
                        f"- **Total Lines**: {totals.get('num_statements', 0)}",
                        f"- **Missing Lines**: {totals.get('missing_lines', 0)}",
                        "",
                    ]
                )

        return "\n".join(report_lines)

    def save_report(self, report: str, filename: str = "test_report.md"):
        """Save test report to file."""
        report_path = self.project_root / filename
        with open(report_path, "w") as f:
            f.write(report)
        print(f"📄 Test report saved to: {report_path}")

    def run_all_tests(
        self,
        include_slow: bool = False,
        test_pattern: str = None,
        skip_lint: bool = False,
    ) -> bool:
        """Run the complete test suite."""
        print("🚀 Starting comprehensive test suite...")
        print("=" * 60)

        # Validate environment first
        if not self.validate_test_environment():
            return False

        # Run all test categories
        test_functions = [
            ("Unit Tests", lambda: self.run_unit_tests(test_pattern)),
            ("Integration Tests", self.run_integration_tests),
            ("Performance Tests", self.run_performance_tests),
            ("Security Tests", self.run_security_tests),
            ("Coverage Analysis", self.run_coverage_analysis),
            ("Dependency Checks", self.run_dependency_checks),
        ]

        if not skip_lint:
            test_functions.append(("Code Quality", self.run_lint_checks))

        all_passed = True

        for test_name, test_func in test_functions:
            print(f"\n{'-' * 40}")
            result = test_func()
            if not result.get("success", False):
                all_passed = False

        print(f"\n{'=' * 60}")

        # Generate and save report
        report = self.generate_test_report()
        self.save_report(report)

        if all_passed:
            print("🎉 All tests passed! Test suite is comprehensive and working.")
        else:
            print("⚠️  Some tests failed. See report for details.")

        return all_passed


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="QuranBot Test Runner")
    parser.add_argument("--pattern", "-k", help="Test pattern to match")
    parser.add_argument(
        "--include-slow", action="store_true", help="Include slow tests"
    )
    parser.add_argument("--skip-lint", action="store_true", help="Skip linting checks")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--integration-only", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--performance-only", action="store_true", help="Run only performance tests"
    )
    parser.add_argument(
        "--security-only", action="store_true", help="Run only security tests"
    )
    parser.add_argument(
        "--coverage-only", action="store_true", help="Run only coverage analysis"
    )

    args = parser.parse_args()

    # Find project root (directory containing pyproject.toml)
    current_dir = Path.cwd()
    project_root = current_dir

    while (
        not (project_root / "pyproject.toml").exists()
        and project_root != project_root.parent
    ):
        project_root = project_root.parent

    if not (project_root / "pyproject.toml").exists():
        print("❌ Could not find project root (no pyproject.toml found)")
        sys.exit(1)

    print(f"Project root: {project_root}")

    runner = TestRunner(project_root)

    # Run specific test category if requested
    if args.unit_only:
        result = runner.run_unit_tests(args.pattern)
        sys.exit(0 if result["success"] else 1)
    elif args.integration_only:
        result = runner.run_integration_tests()
        sys.exit(0 if result["success"] else 1)
    elif args.performance_only:
        result = runner.run_performance_tests()
        sys.exit(0 if result["success"] else 1)
    elif args.security_only:
        result = runner.run_security_tests()
        sys.exit(0 if result["success"] else 1)
    elif args.coverage_only:
        result = runner.run_coverage_analysis()
        sys.exit(0 if result["success"] else 1)
    else:
        # Run all tests
        success = runner.run_all_tests(
            include_slow=args.include_slow,
            test_pattern=args.pattern,
            skip_lint=args.skip_lint,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
