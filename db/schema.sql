-- Users table with enhanced fields
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    subscription_tier TEXT CHECK(subscription_tier IN ('platinum', 'gold', 'silver', 'standard', 'free', 'basic', 'pro')) NOT NULL,
    renewal_date TEXT,
    active INTEGER DEFAULT 1,
    balance REAL DEFAULT 0.0,
    last_change TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    issued TEXT NOT NULL,
    paid INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Activity log table
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    agent_name TEXT,
    action TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT UNIQUE NOT NULL,
    value REAL,
    updated TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Known issues table for knowledge base
CREATE TABLE IF NOT EXISTS known_issues (
    issue_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT,
    fix TEXT,
    confidence_boost REAL DEFAULT 0.0,
    customer_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id)
);

-- Feedback loop table for learning mechanism
CREATE TABLE IF NOT EXISTS feedback_loop (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    customer_id INTEGER,
    intent TEXT,
    confidence_score REAL,
    diagnostic_reasoning TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id)
);

-- Audit logs table for compliance
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    agent_name TEXT,
    action_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    old_value TEXT,
    new_value TEXT,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Triggers for automatic timestamp updates
CREATE TRIGGER IF NOT EXISTS update_users_timestamp
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS update_invoices_timestamp
AFTER UPDATE ON invoices
FOR EACH ROW
BEGIN
    UPDATE invoices SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS update_known_issues_timestamp
AFTER UPDATE ON known_issues
FOR EACH ROW
BEGIN
    UPDATE known_issues SET updated_at = CURRENT_TIMESTAMP WHERE issue_key = OLD.issue_key;
END;

CREATE TRIGGER IF NOT EXISTS update_feedback_loop_timestamp
AFTER UPDATE ON feedback_loop
FOR EACH ROW
BEGIN
    UPDATE feedback_loop SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_customer ON feedback_loop(customer_id);
CREATE INDEX IF NOT EXISTS idx_feedback_ticket ON feedback_loop(ticket_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);

