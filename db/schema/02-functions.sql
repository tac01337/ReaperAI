
-- Function to insert a new target
CREATE OR REPLACE FUNCTION insert_target(ip_address VARCHAR, hostname VARCHAR, operating_system VARCHAR) RETURNS VOID AS $$
BEGIN
    INSERT INTO targets(ip_address, hostname, operating_system, last_scanned) VALUES (ip_address, hostname, operating_system, NOW());
END;
$$ LANGUAGE plpgsql;

-- Function to insert a new vulnerability
CREATE OR REPLACE FUNCTION insert_vulnerability(name VARCHAR, description TEXT, cvss_score DECIMAL, cvss_vector VARCHAR) RETURNS VOID AS $$
BEGIN
    INSERT INTO vulnerabilities(name, description, cvss_score, cvss_vector) VALUES (name, description, cvss_score, cvss_vector);
END;
$$ LANGUAGE plpgsql;


-- Function to insert a new exploit
CREATE OR REPLACE FUNCTION insert_exploit(name VARCHAR, description TEXT, platform VARCHAR, type VARCHAR) RETURNS VOID AS $$
BEGIN
    INSERT INTO exploits(name, description, platform, type) VALUES (name, description, platform, type);
END;
$$ LANGUAGE plpgsql;

-- Function to insert a new scan result
CREATE OR REPLACE FUNCTION insert_scan_result(target_id INT, vulnerability_id INT, exploit_id INT) RETURNS VOID AS $$
BEGIN
    INSERT INTO scan_results(target_id, vulnerability_id, exploit_id, scan_date) VALUES (target_id, vulnerability_id, exploit_id, NOW());
END;
$$ LANGUAGE plpgsql;

-- Function to get all targets
CREATE OR REPLACE FUNCTION get_targets() RETURNS TABLE(id INT, ip_address VARCHAR, hostname VARCHAR, operating_system VARCHAR, last_scanned TIMESTAMP) AS $$
BEGIN
    RETURN QUERY SELECT * FROM targets;
END;
$$ LANGUAGE plpgsql;

-- Function to get all vulnerabilities
CREATE OR REPLACE FUNCTION get_vulnerabilities() RETURNS TABLE(id INT, name VARCHAR, description TEXT, cvss_score DECIMAL, cvss_vector VARCHAR) AS $$
BEGIN
    RETURN QUERY SELECT * FROM vulnerabilities;
END;
$$ LANGUAGE plpgsql;

-- Function to get all exploits
CREATE OR REPLACE FUNCTION get_exploits() RETURNS TABLE(id INT, name VARCHAR, description TEXT, platform VARCHAR, type VARCHAR) AS $$
BEGIN
    RETURN QUERY SELECT * FROM exploits;
END;
$$ LANGUAGE plpgsql;

-- Function to get all scan results
CREATE OR REPLACE FUNCTION get_scan_results() RETURNS TABLE(id INT, target_id INT, vulnerability_id INT, exploit_id INT, scan_date TIMESTAMP) AS $$
BEGIN
    RETURN QUERY SELECT * FROM scan_results;
END;
$$ LANGUAGE plpgsql;