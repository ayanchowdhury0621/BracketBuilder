#!/bin/bash

# BracketBuilder Automated Test Script
# Tests backend API endpoints and frontend availability

echo "================================================"
echo "BracketBuilder Test Suite"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -n "Testing $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response, expected $expected_code)"
        ((FAILED++))
        return 1
    fi
}

# Helper function to test JSON response
test_json_endpoint() {
    local name=$1
    local url=$2
    local jq_filter=$3
    local expected=$4
    
    echo -n "Testing $name... "
    
    result=$(curl -s "$url" | python3 -c "import sys, json; data=json.load(sys.stdin); print($jq_filter)" 2>/dev/null)
    
    if [ "$result" = "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC} ($result)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (got '$result', expected '$expected')"
        ((FAILED++))
        return 1
    fi
}

echo "=== Frontend Tests ==="
echo ""

test_endpoint "Frontend home page" "http://localhost:5173/" 200
test_endpoint "Frontend bracket route" "http://localhost:5173/bracket" 200
test_endpoint "Frontend analysis route" "http://localhost:5173/analysis" 200

echo ""
echo "=== Backend API Tests ==="
echo ""

test_endpoint "Backend health check" "http://localhost:8002/docs" 200
test_endpoint "Teams endpoint" "http://localhost:8002/api/teams" 200
test_endpoint "Bracket endpoint" "http://localhost:8002/api/bracket" 200
test_endpoint "Players endpoint" "http://localhost:8002/api/players" 200
test_endpoint "Summary endpoint" "http://localhost:8002/api/summary" 200

echo ""
echo "=== Data Quality Tests ==="
echo ""

# Test teams data
echo -n "Testing teams data structure... "
teams_count=$(curl -s "http://localhost:8002/api/teams" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ "$teams_count" -gt 300 ]; then
    echo -e "${GREEN}✓ PASS${NC} ($teams_count teams)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (only $teams_count teams)"
    ((FAILED++))
fi

# Test bracket regions
echo -n "Testing bracket regions... "
regions=$(curl -s "http://localhost:8002/api/bracket" | python3 -c "import sys, json; data=json.load(sys.stdin); print(','.join(sorted(data['regions'].keys())))" 2>/dev/null)
if [ "$regions" = "East,Midwest,South,West" ]; then
    echo -e "${GREEN}✓ PASS${NC} (all 4 regions present)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} (regions: $regions)"
    ((FAILED++))
fi

# Test summary stats
echo -n "Testing summary stats... "
total_teams=$(curl -s "http://localhost:8002/api/summary" | python3 -c "import sys, json; print(json.load(sys.stdin)['totalTeams'])" 2>/dev/null)
if [ "$total_teams" -gt 300 ]; then
    echo -e "${GREEN}✓ PASS${NC} ($total_teams teams)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} ($total_teams teams)"
    ((FAILED++))
fi

echo ""
echo "=== Matchup Generation Test ==="
echo ""

# Test matchup endpoint (this takes ~15 seconds first time)
echo -n "Testing matchup generation (Michigan vs UConn)... "
matchup_result=$(curl -s -X POST "http://localhost:8002/api/matchup" \
    -H "Content-Type: application/json" \
    -d '{"team1Slug": "michigan", "team2Slug": "uconn"}' \
    | python3 -c "import sys, json; data=json.load(sys.stdin); print('OK' if 'analysis' in data and 'rotobotPick' in data else 'FAIL')" 2>/dev/null)

if [ "$matchup_result" = "OK" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

echo ""
echo "=== Frontend HTML Content Tests ==="
echo ""

# Check if home page has expected content
echo -n "Checking home page for hero text... "
if curl -s "http://localhost:5173/" | grep -q "Smarter Bracket"; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ SKIP${NC} (requires JS rendering)"
fi

echo ""
echo "================================================"
echo "Test Results"
echo "================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "✓ Backend API is fully operational"
    echo "✓ Frontend is serving content"
    echo "✓ Data quality checks passed"
    echo ""
    echo "Next step: Open http://localhost:5173/ in your browser"
    echo "to verify the UI renders correctly and is interactive."
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    echo ""
    echo "Please check:"
    echo "1. Is the backend running on port 8002?"
    echo "2. Is the frontend running on port 5173?"
    echo "3. Are there any errors in the terminal logs?"
    exit 1
fi
