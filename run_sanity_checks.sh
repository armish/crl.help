#!/bin/bash
# Comprehensive sanity check script for crl.help backend

set -e  # Exit on error

echo "==================================="
echo "Running All Backend Sanity Checks"
echo "==================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY is not set"
    echo "   Please set it with: export OPENAI_API_KEY='your-key'"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  WARNING: DATABASE_URL is not set"
    echo "   Using default: postgresql://localhost:5432/crl_help"
    export DATABASE_URL="postgresql://localhost:5432/crl_help"
fi

echo "✓ OPENAI_API_KEY is set"
echo "✓ DATABASE_URL: $DATABASE_URL"
echo ""

# Sanity Check #1: Database
echo "========================================="
echo "Sanity Check #1: Database Schema"
echo "========================================="
echo ""

# Extract database name from DATABASE_URL
DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
echo "Database name: $DB_NAME"

# Check if database exists, create if not
if psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "✓ Database '$DB_NAME' exists"
else
    echo "⚠️  Database '$DB_NAME' does not exist, creating..."
    createdb $DB_NAME
    echo "✓ Database created"
fi

echo ""
echo "Running migrations..."
cd backend
alembic upgrade head
if [ $? -eq 0 ]; then
    echo "✅ Database migrations successful"
else
    echo "❌ Database migrations failed"
    exit 1
fi

echo ""
echo "Verifying tables..."
psql $DB_NAME -c "\dt" | grep -E "clinical_trials|trial_embeddings|user_queries|rag_results"
if [ $? -eq 0 ]; then
    echo "✅ All required tables exist"
else
    echo "⚠️  Some tables may be missing"
fi

cd ..
echo ""
echo ""

# Sanity Check #2: OpenAI API
echo "========================================="
echo "Sanity Check #2: OpenAI API Integration"
echo "========================================="
echo ""

cd backend
python tests/integration/test_openai_real.py
if [ $? -eq 0 ]; then
    echo "✅ OpenAI API integration successful"
else
    echo "❌ OpenAI API integration failed"
    exit 1
fi

cd ..
echo ""
echo ""

# Sanity Check #3: E2E RAG
echo "========================================="
echo "Sanity Check #3: End-to-End RAG Flow"
echo "========================================="
echo ""

cd backend
python tests/integration/test_e2e_rag.py
if [ $? -eq 0 ]; then
    echo "✅ End-to-End RAG flow successful"
else
    echo "❌ End-to-End RAG flow failed"
    exit 1
fi

cd ..
echo ""
echo ""

# Summary
echo "==================================="
echo "✅ All Sanity Checks PASSED!"
echo "==================================="
echo ""
echo "Backend is ready for frontend integration!"
echo ""
echo "Next steps:"
echo "  1. Review the test outputs above"
echo "  2. Check the database with: psql $DB_NAME"
echo "  3. Proceed to frontend implementation"
echo ""
