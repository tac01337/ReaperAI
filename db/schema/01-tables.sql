

-- Table for storing information about targets
CREATE TABLE targets (
    id INT PRIMARY KEY,
    ip_address VARCHAR(15),
    hostname VARCHAR(255),
    operating_system VARCHAR(255),
    last_scanned TIMESTAMP
);

-- Table for storing information about vulnerabilities
CREATE TABLE vulnerabilities (
    id INT PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    cvss_score DECIMAL(3, 1),
    cvss_vector VARCHAR(255)
);

-- Table for storing information about exploits
CREATE TABLE exploits (
    id INT PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    platform VARCHAR(255),
    type VARCHAR(255)
);

CREATE TABLE ports (
    id SERIAL PRIMARY KEY,
    target_id INT,
    port_number INTEGER,
    service VARCHAR(255),
    state VARCHAR(255),
    protocol VARCHAR(255),
    FOREIGN KEY (target_id) REFERENCES targets(id)
);

CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    port_id INT,
    name VARCHAR(255),
    product VARCHAR(255),
    version VARCHAR(255),
    extra_info TEXT,
    FOREIGN KEY (port_id) REFERENCES ports(id)
);

-- Table for storing scan results
CREATE TABLE scan_results (
    id INT PRIMARY KEY,
    target_id INT,
    vulnerability_id INT,
    exploit_id INT,
    scan_date TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES targets(id),
    FOREIGN KEY (vulnerability_id) REFERENCES vulnerabilities(id),
    FOREIGN KEY (exploit_id) REFERENCES exploits(id)
);

-- Runs
CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    model TEXT,
    context_size INTEGER,
    state TEXT,
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    configuration TEXT,
    host TEXT
);

-- Commands
CREATE TABLE commands (
    id SERIAL PRIMARY KEY, 
    run_id INTEGER,
    name TEXT,
    stdout TEXT
);

-- Queries
CREATE TABLE queries (
    id SERIAL PRIMARY KEY,
    run_id INTEGER,
    round INTEGER,
    cmd_id INTEGER,
    query TEXT,
    response TEXT,
    duration REAL,
    tokens_query INTEGER,
    tokens_response INTEGER,
    prompt TEXT,
    answer TEXT
);

-- State

-- Analzations