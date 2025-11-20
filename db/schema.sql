CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    subscription_tier TEXT CHECK(subscription_tier IN ('free', 'basic', 'pro')) NOT NULL,
    renewal_date TEXT,
    active INTEGER DEFAULT 1,
    balance REAL DEFAULT 0.0,
    last_change TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    issued TEXT NOT NULL,
    paid INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    agent_name TEXT,
    action TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT UNIQUE NOT NULL,
    value REAL,
    updated TEXT DEFAULT CURRENT_TIMESTAMP
);
