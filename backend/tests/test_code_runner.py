from app.services.code_runner_service import code_runner_service
from app.models.question import TestCase

def test_code_runner_correct_solution():
    code = """
class Solution:
    def solve(self, n: int) -> int:
        return n * 2
"""
    test_cases = [
        TestCase(input="5", expected_output="10", is_hidden=False),
        TestCase(input="0", expected_output="0", is_hidden=False)
    ]
    result = code_runner_service.evaluate_python_code(code, test_cases)
    assert result.passed is True
    assert result.passed_tests == 2

def test_code_runner_security_sandbox():
    # Attempting to import os or sys should be blocked immediately
    code = """
import os
class Solution:
    def solve(self, s: str):
        return os.getcwd()
"""
    test_cases = [TestCase(input="'test'", expected_output="'test'", is_hidden=False)]
    result = code_runner_service.evaluate_python_code(code, test_cases)
    assert result.passed is False
    assert "Security Restriction" in result.error

def test_code_runner_syntax_error():
    code = "def broken(:"
    result = code_runner_service.evaluate_python_code(code, [])
    assert result.passed is False
    assert "Syntax Error" in result.error
