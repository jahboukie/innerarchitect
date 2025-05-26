#!/bin/bash
# Script to run tests for The Inner Architect

set -e

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: This script must be run from the project root directory."
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run tests for The Inner Architect."
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -u, --unit           Run unit tests only"
    echo "  -i, --integration    Run integration tests only"
    echo "  -c, --coverage       Generate coverage report"
    echo "  -l, --lint           Run linting checks"
    echo "  -a, --all            Run all tests and checks (default)"
    echo "  -v, --verbose        Verbose output"
    echo ""
    exit 0
}

# Parse command line arguments
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_COVERAGE=false
RUN_LINT=false
VERBOSE=""

# If no arguments, run all
if [ $# -eq 0 ]; then
    RUN_UNIT=true
    RUN_INTEGRATION=true
    RUN_COVERAGE=true
    RUN_LINT=true
fi

while [ "$1" != "" ]; do
    case $1 in
        -h | --help )          show_usage
                               ;;
        -u | --unit )          RUN_UNIT=true
                               ;;
        -i | --integration )   RUN_INTEGRATION=true
                               ;;
        -c | --coverage )      RUN_COVERAGE=true
                               ;;
        -l | --lint )          RUN_LINT=true
                               ;;
        -a | --all )           RUN_UNIT=true
                               RUN_INTEGRATION=true
                               RUN_COVERAGE=true
                               RUN_LINT=true
                               ;;
        -v | --verbose )       VERBOSE="-v"
                               ;;
        * )                    echo "Unknown option: $1"
                               show_usage
                               exit 1
    esac
    shift
done

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Set environment variables for testing
export FLASK_APP=inner_architect.wsgi
export FLASK_ENV=testing
export TESTING=true
export SECRET_KEY=test_key
export SQLALCHEMY_DATABASE_URI=sqlite:///test.db

# Run linting if requested
if [ "$RUN_LINT" = true ]; then
    echo "Running linting checks..."
    
    echo "Running flake8..."
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    
    echo "Running black..."
    black --check .
    
    echo "Running isort..."
    isort --check-only --profile black .
    
    echo "Running mypy..."
    mypy .
fi

# Prepare test command
TEST_CMD="pytest"

if [ "$VERBOSE" = "-v" ]; then
    TEST_CMD="$TEST_CMD -v"
fi

# Run unit tests if requested
if [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = false ]; then
    echo "Running unit tests..."
    $TEST_CMD inner_architect/tests/unit/
fi

# Run integration tests if requested
if [ "$RUN_INTEGRATION" = true ] && [ "$RUN_UNIT" = false ]; then
    echo "Running integration tests..."
    $TEST_CMD inner_architect/tests/integration/
fi

# Run all tests if both are requested
if [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = true ]; then
    echo "Running all tests..."
    $TEST_CMD inner_architect/tests/
fi

# Generate coverage report if requested
if [ "$RUN_COVERAGE" = true ]; then
    echo "Generating coverage report..."
    pytest --cov=inner_architect --cov-report=term --cov-report=html inner_architect/tests/
    echo "Coverage report generated in htmlcov/ directory"
fi

echo "All tests completed!"