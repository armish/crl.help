"""
Database schema definitions for FDA CRL Explorer.
Contains all SQL table creation statements for DuckDB.
"""

# Table: crls - Stores raw CRL data from FDA API
CREATE_CRLS_TABLE = """
CREATE TABLE IF NOT EXISTS crls (
    id VARCHAR PRIMARY KEY,
    application_number VARCHAR[],
    letter_date DATE,
    letter_year VARCHAR,
    letter_type VARCHAR,
    application_type VARCHAR,
    approval_status VARCHAR,
    company_name VARCHAR,
    company_address VARCHAR,
    company_rep VARCHAR,
    approver_name VARCHAR,
    approver_center VARCHAR[],
    approver_title VARCHAR,
    file_name VARCHAR,
    text TEXT,
    therapeutic_category VARCHAR,
    product_name VARCHAR,
    indications TEXT,
    deficiency_reason VARCHAR,
    raw_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Table: crl_summaries - Stores AI-generated summaries
CREATE_SUMMARIES_TABLE = """
CREATE TABLE IF NOT EXISTS crl_summaries (
    id VARCHAR PRIMARY KEY,
    crl_id VARCHAR,
    summary TEXT,
    model VARCHAR,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER
);
"""

# Table: crl_embeddings - Stores vector embeddings for RAG
CREATE_EMBEDDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS crl_embeddings (
    id VARCHAR PRIMARY KEY,
    crl_id VARCHAR,
    embedding_type VARCHAR,
    embedding FLOAT[],
    model VARCHAR,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Table: qa_annotations - Stores user questions and AI answers
CREATE_QA_TABLE = """
CREATE TABLE IF NOT EXISTS qa_annotations (
    id VARCHAR PRIMARY KEY,
    question TEXT,
    answer TEXT,
    relevant_crl_ids VARCHAR[],
    model VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INTEGER
);
"""

# Table: processing_metadata - Tracks processing status
CREATE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS processing_metadata (
    key VARCHAR PRIMARY KEY,
    value VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Indexes for common queries
CREATE_INDEXES = [
    # CRLs table indexes
    "CREATE INDEX IF NOT EXISTS idx_crls_approval_status ON crls(approval_status);",
    "CREATE INDEX IF NOT EXISTS idx_crls_letter_year ON crls(letter_year);",
    "CREATE INDEX IF NOT EXISTS idx_crls_company_name ON crls(company_name);",
    "CREATE INDEX IF NOT EXISTS idx_crls_letter_date ON crls(letter_date);",
    "CREATE INDEX IF NOT EXISTS idx_crls_therapeutic_category ON crls(therapeutic_category);",
    "CREATE INDEX IF NOT EXISTS idx_crls_created_at ON crls(created_at);",

    # Summaries table indexes
    "CREATE INDEX IF NOT EXISTS idx_summaries_crl_id ON crl_summaries(crl_id);",
    "CREATE INDEX IF NOT EXISTS idx_summaries_generated_at ON crl_summaries(generated_at);",

    # Embeddings table indexes
    "CREATE INDEX IF NOT EXISTS idx_embeddings_crl_id ON crl_embeddings(crl_id);",
    "CREATE INDEX IF NOT EXISTS idx_embeddings_type ON crl_embeddings(embedding_type);",

    # Q&A table indexes
    "CREATE INDEX IF NOT EXISTS idx_qa_created_at ON qa_annotations(created_at);",
]

# All table creation statements
ALL_TABLES = [
    CREATE_CRLS_TABLE,
    CREATE_SUMMARIES_TABLE,
    CREATE_EMBEDDINGS_TABLE,
    CREATE_QA_TABLE,
    CREATE_METADATA_TABLE,
]


def get_init_schema_sql() -> str:
    """
    Get complete SQL for database initialization.

    Returns:
        str: Combined SQL statements for creating all tables and indexes
    """
    sql_statements = ALL_TABLES + CREATE_INDEXES
    return "\n\n".join(sql_statements)
