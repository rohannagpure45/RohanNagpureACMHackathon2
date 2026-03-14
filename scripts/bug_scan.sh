#!/bin/bash
# Bug scanning script for RohanNagpureACMHackathon2
# This script scans for bugs and can create GitHub issues

REPO_DIR="/home/ubuntu/.openclaw/workspace/RohanNagpureACMHackathon2"
cd "$REPO_DIR" || exit 1

# Check if git remote exists
if ! git remote get-url origin >/dev/null 2>&1; then
    echo "Not a git repository with remote"
    exit 1
fi

echo "=== Bug Scan Report ==="
echo "Date: $(date)"
echo ""

# Track if we found bugs
FOUND_BUGS=0

# Check 1: Frontend TypeScript type mismatches
echo "--- Checking TypeScript types ---"
if grep -q "id: string" frontend/src/types/index.ts 2>/dev/null; then
    # Check if backend returns int
    if grep -q "id: int" backend/api/schemas.py 2>/dev/null; then
        echo "BUG: Type mismatch - Session.id is string in frontend but int in backend"
        FOUND_BUGS=1
    fi
fi

if grep -q "session_id: string" frontend/src/types/index.ts 2>/dev/null; then
    if grep -q "session_id: int" backend/api/schemas.py 2>/dev/null; then
        echo "BUG: Type mismatch - UploadResponse.session_id is string in frontend but int in backend"
        FOUND_BUGS=1
    fi
fi

# Check 2: Look for TODO/FIXME/BUG comments
echo "--- Checking for TODO/FIXME/BUG comments ---"
TODOS=$(find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) -exec grep -l "TODO\|FIXME\|BUG\|XXX\|HACK" {} \; 2>/dev/null | head -10)
if [ -n "$TODOS" ]; then
    echo "Found TODO/FIXME comments in:"
    echo "$TODOS"
    FOUND_BUGS=1
fi

# Check 3: Check for potential division by zero issues
echo "--- Checking for division by zero risks ---"
if grep -r "np.diff(times_arr)" backend/core/*.py 2>/dev/null | grep -v "dt\[dt == 0\]" >/dev/null; then
    echo "Potential division by zero in time-based calculations"
    FOUND_BUGS=1
fi

# Check 4: Check CORS configuration
echo "--- Checking CORS ---"
if grep -q 'allow_origins=\["http://localhost:5173"' backend/main.py 2>/dev/null; then
    echo "INFO: CORS only allows localhost (may need adjustment for production)"
fi

# Check 5: Check for hardcoded localhost URLs
echo "--- Checking for hardcoded URLs ---"
HARDCODED=$(grep -r "localhost:8000\|127.0.0.1:8000" frontend/src --include="*.ts" --include="*.tsx" 2>/dev/null)
if [ -n "$HARDCODED" ]; then
    echo "Hardcoded API URLs found in frontend (may want to use environment variables):"
    echo "$HARDCODED"
    FOUND_BUGS=1
fi

# Check 6: Check for missing error handling
echo "--- Checking error handling ---"
if grep -q "except:" backend/api/routes_upload.py 2>/dev/null; then
    echo "WARNING: Bare except clause found in routes_upload.py"
fi

echo ""
echo "=== Summary ==="
if [ $FOUND_BUGS -eq 1 ]; then
    echo "Potential issues found!"
    exit 1
else
    echo "No significant bugs detected"
    exit 0
fi
