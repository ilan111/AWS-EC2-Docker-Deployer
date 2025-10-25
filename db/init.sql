-- Simple database schema for lean API-Worker messaging system
CREATE TABLE IF NOT EXISTS requests_status (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) NOT NULL CHECK (status IN ('in_progress', 'done', 'deployed', 'deploying', 'failed')),
    result TEXT
);