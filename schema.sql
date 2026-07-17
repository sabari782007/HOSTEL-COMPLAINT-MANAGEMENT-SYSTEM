-- =====================================================
-- Hostel Complaint Management System (HCMS)
-- Database Schema (SQLite)
-- =====================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------
-- Table: users
-- Stores students, wardens/admins, and staff accounts
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('student', 'admin', 'staff')),
    room_number   TEXT,               -- applicable for students
    block         TEXT,               -- applicable for students
    phone         TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------
-- Table: categories
-- Predefined complaint categories
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO categories (name) VALUES
    ('Electrical'),
    ('Plumbing'),
    ('Furniture'),
    ('Internet'),
    ('Food/Mess'),
    ('Cleanliness'),
    ('Security'),
    ('Others');

-- ---------------------------------------------------
-- Table: complaints
-- Core complaint records raised by students
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     INTEGER NOT NULL,
    category_id    INTEGER NOT NULL,
    title          TEXT NOT NULL,
    description    TEXT NOT NULL,
    block          TEXT,
    room_number    TEXT,
    priority       TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High')),
    status         TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Assigned', 'In Progress', 'Resolved', 'Rejected')),
    assigned_staff INTEGER,
    admin_remarks  TEXT,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at    DATETIME,
    FOREIGN KEY (student_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    FOREIGN KEY (assigned_staff) REFERENCES users(user_id)
);

-- ---------------------------------------------------
-- Table: complaint_logs
-- Status change history for each complaint (audit trail)
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS complaint_logs (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id  INTEGER NOT NULL,
    changed_by    INTEGER NOT NULL,
    old_status    TEXT,
    new_status    TEXT NOT NULL,
    remarks       TEXT,
    changed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(user_id)
);

-- ---------------------------------------------------
-- Table: feedback
-- Student feedback/rating after complaint resolution
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id  INTEGER NOT NULL UNIQUE,
    rating        INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments      TEXT,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE
);

-- ---------------------------------------------------
-- Table: notifications
-- In-app notification log for status updates
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    complaint_id     INTEGER,
    message          TEXT NOT NULL,
    is_read          INTEGER NOT NULL DEFAULT 0,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id) ON DELETE CASCADE
);

-- ---------------------------------------------------
-- Helpful indexes
-- ---------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_complaints_student ON complaints(student_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category_id);

-- ---------------------------------------------------
-- Seed default admin account (email: admin@hcms.com / password: admin123)
-- Password hash below corresponds to 'admin123' using werkzeug's
-- generate_password_hash (pbkdf2:sha256) — regenerate in production.
-- ---------------------------------------------------
-- INSERT INTO users (full_name, email, password_hash, role)
-- VALUES ('System Admin', 'admin@hcms.com', '<generate_and_paste_hash_here>', 'admin');
