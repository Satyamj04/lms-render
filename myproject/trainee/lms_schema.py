
# lms_bootstrap_schema.py
import os
import sys
import psycopg2

DB_NAME = os.getenv("DB_NAME", "your_db_name")
DB_USER = os.getenv("DB_USER", "your_db_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_db_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

DDL = r"""
-- ============================================================
-- Enterprise LMS - PostgreSQL Schema
-- Additions: Quiz Confidence + Assignment Rubrics (no duplicate assessments table)
-- FINALIZED: Includes missing tables from Admin, Trainer, Trainee modules
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================
-- MODULE 1: USER & TEAM MGMT
-- =========================

CREATE TABLE IF NOT EXISTS roles (
    role_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name     VARCHAR(50) NOT NULL UNIQUE CHECK (role_name IN ('admin','trainer','manager','trainee')),
    description   TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name         VARCHAR(100) NOT NULL,
    last_name          VARCHAR(100) NOT NULL,
    email              VARCHAR(255) NOT NULL UNIQUE,
    password_hash      VARCHAR(255) NOT NULL,
    primary_role       VARCHAR(50) NOT NULL CHECK (primary_role IN ('admin','trainer','manager','trainee')),
    status             VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','inactive','archived')),
    profile_image_url  TEXT,
    last_login         TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at         TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_role   ON users (primary_role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);
CREATE INDEX IF NOT EXISTS idx_users_email  ON users (email);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES users(user_id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS teams (
    team_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_name   VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    status      VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','inactive','archived')),
    manager_id  UUID REFERENCES users(user_id) ON DELETE SET NULL,
    created_by  UUID REFERENCES users(user_id),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_teams_manager ON teams (manager_id);

CREATE TABLE IF NOT EXISTS team_members (
    team_id         UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    is_primary_team BOOLEAN DEFAULT TRUE,
    assigned_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by     UUID REFERENCES users(user_id),
    PRIMARY KEY (team_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members (user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members (team_id);

-- =========================
-- MODULE 2: COURSES & MODULES
-- =========================

CREATE TABLE IF NOT EXISTS courses (
    course_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title                    VARCHAR(500) NOT NULL,
    description              TEXT,
    about                    TEXT,
    outcomes                 TEXT,
    course_type              VARCHAR(30) DEFAULT 'self_paced' CHECK (course_type IN ('self_paced','instructor_led','blended')),
    status                   VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    is_mandatory             BOOLEAN DEFAULT FALSE,
    estimated_duration_hours INTEGER,
    passing_criteria         INTEGER DEFAULT 70 CHECK (passing_criteria >= 0 AND passing_criteria <= 100),
    created_by               UUID NOT NULL REFERENCES users(user_id),
    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at               TIMESTAMP,
    version                  INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_courses_created_by ON courses (created_by);
CREATE INDEX IF NOT EXISTS idx_courses_status     ON courses (status);

CREATE TABLE IF NOT EXISTS modules (
    module_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id                  UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    title                      VARCHAR(500) NOT NULL,
    description                TEXT,
    module_type                VARCHAR(30) CHECK (module_type IN ('video','pdf','ppt','document','quiz','mixed','text','audio','presentation','page','assignment','survey')),
    sequence_order             INTEGER NOT NULL,
    is_mandatory               BOOLEAN DEFAULT TRUE,
    estimated_duration_minutes INTEGER,
    video_count                INTEGER DEFAULT 0,
    has_quizzes                BOOLEAN DEFAULT FALSE,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at                 TIMESTAMP,
    version                    INTEGER DEFAULT 1,
    CONSTRAINT uq_module_sequence UNIQUE (course_id, sequence_order)
);
CREATE INDEX IF NOT EXISTS idx_modules_course   ON modules (course_id);
CREATE INDEX IF NOT EXISTS idx_modules_sequence ON modules (course_id, sequence_order);

CREATE TABLE IF NOT EXISTS module_sequencing (
    sequence_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id              UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    module_id              UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    preceding_module_id    UUID REFERENCES modules(module_id) ON DELETE CASCADE,
    drip_feed_rule         VARCHAR(30) DEFAULT 'none' CHECK (drip_feed_rule IN ('none','time_based','completion_based')),
    drip_feed_delay_days   INTEGER DEFAULT 0,
    prerequisite_completed BOOLEAN DEFAULT FALSE,
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_module_seq UNIQUE (course_id, module_id)
);

-- =========================
-- MODULE 3: ASSIGNMENTS & TESTS
-- =========================

CREATE TABLE IF NOT EXISTS assignments (
    assignment_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID REFERENCES courses(course_id) ON DELETE CASCADE,
    module_id       UUID REFERENCES modules(module_id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    assignment_type VARCHAR(30) CHECK (assignment_type IN ('task','role_play','written','project','other')),
    due_date        TIMESTAMP,
    max_attempts    INTEGER DEFAULT 1 CHECK (max_attempts > 0),
    points_possible INTEGER DEFAULT 100,
    is_mandatory    BOOLEAN DEFAULT TRUE,
    created_by      UUID NOT NULL REFERENCES users(user_id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at      TIMESTAMP,
    version         INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_assignments_course ON assignments (course_id);

-- NEW (non-breaking): Make it easy to mark an assignment as descriptive/oral/etc without changing existing CHECK
ALTER TABLE assignments
    ADD COLUMN IF NOT EXISTS evaluation_method VARCHAR(30)
        CHECK (evaluation_method IN ('descriptive','practical','oral','rubric','peer','survey'));

CREATE TABLE IF NOT EXISTS assignment_submissions (
    submission_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id       UUID NOT NULL REFERENCES assignments(assignment_id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    attempt_number      INTEGER NOT NULL DEFAULT 1,
    submission_text     TEXT,
    submission_file_url TEXT,
    score               INTEGER CHECK (score >= 0),
    feedback            TEXT,
    status              VARCHAR(30) DEFAULT 'submitted' CHECK (status IN ('draft','submitted','graded','returned')),
    submitted_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graded_by           UUID REFERENCES users(user_id),
    graded_at           TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_assignment_submission UNIQUE (assignment_id, user_id, attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_assignment_submissions_user       ON assignment_submissions (user_id);
CREATE INDEX IF NOT EXISTS idx_assignment_submissions_assignment ON assignment_submissions (assignment_id);

CREATE TABLE IF NOT EXISTS assignment_submission_reviews (
    review_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id     UUID NOT NULL REFERENCES assignment_submissions(submission_id) ON DELETE CASCADE,
    reviewer_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    review_note       TEXT,
    score             INTEGER CHECK (score >= 0),
    status            VARCHAR(30) DEFAULT 'reviewed' CHECK (status IN ('reviewed', 'pending', 'needs_revision')),
    reviewed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_submission_reviewer UNIQUE(submission_id, reviewer_id)
);

CREATE INDEX IF NOT EXISTS idx_assignment_submission_reviews_submission ON assignment_submission_reviews(submission_id);
CREATE INDEX IF NOT EXISTS idx_assignment_submission_reviews_reviewer   ON assignment_submission_reviews(reviewer_id);

CREATE TABLE IF NOT EXISTS tests (
    test_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id           UUID REFERENCES courses(course_id) ON DELETE CASCADE,
    module_id           UUID REFERENCES modules(module_id) ON DELETE CASCADE,
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    test_type           VARCHAR(30) CHECK (test_type IN ('quiz','test','exam','assessment')),
    time_limit_minutes  INTEGER,
    passing_score       INTEGER DEFAULT 70 CHECK (passing_score >= 0 AND passing_score <= 100),
    max_attempts        INTEGER DEFAULT 1 CHECK (max_attempts > 0),
    randomize_questions BOOLEAN DEFAULT FALSE,
    show_correct_answers BOOLEAN DEFAULT FALSE,
    points_possible     INTEGER DEFAULT 100,
    is_mandatory        BOOLEAN DEFAULT TRUE,
    created_by          UUID NOT NULL REFERENCES users(user_id),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at          TIMESTAMP,
    version             INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_tests_course ON tests (course_id);

-- NEW: confidence toggles
ALTER TABLE tests
    ADD COLUMN IF NOT EXISTS record_confidence BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS confidence_scale VARCHAR(20) DEFAULT '0_to_100'
        CHECK (confidence_scale IN ('0_to_100','1_to_5','1_to_7','low_med_high'));

CREATE TABLE IF NOT EXISTS test_questions (
    question_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id        UUID REFERENCES tests(test_id) ON DELETE CASCADE,
    question_text  TEXT NOT NULL,
    question_type  VARCHAR(30) NOT NULL CHECK (question_type IN ('mcq','true_false','short_answer','essay','fill_blank')),
    options        JSONB,
    correct_answer TEXT,
    points         INTEGER DEFAULT 1,
    difficulty     VARCHAR(20) CHECK (difficulty IN ('easy','medium','hard')),
    explanation    TEXT,
    sequence_order INTEGER,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_attempts (
    attempt_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id            UUID NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
    user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    attempt_number     INTEGER NOT NULL,
    started_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at       TIMESTAMP,
    time_spent_minutes INTEGER,
    status             VARCHAR(30) DEFAULT 'in_progress' CHECK (status IN ('in_progress','completed','abandoned','timed_out')),
    score              INTEGER CHECK (score >= 0 AND score <= 100),
    points_earned      INTEGER DEFAULT 0,
    passed             BOOLEAN,
    graded_by          UUID REFERENCES users(user_id),
    graded_at          TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_test_attempt UNIQUE (test_id, user_id, attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_test_attempts_user ON test_attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_test_attempts_test ON test_attempts (test_id);

-- NEW: Per-question responses with confidence
CREATE TABLE IF NOT EXISTS test_responses (
    response_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id         UUID NOT NULL REFERENCES test_attempts(attempt_id) ON DELETE CASCADE,
    test_id            UUID NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
    question_id        UUID NOT NULL REFERENCES test_questions(question_id) ON DELETE CASCADE,
    user_id            UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    selected_options   JSONB,
    answer_text        TEXT,
    is_correct         BOOLEAN,
    score              INTEGER DEFAULT 0 CHECK (score >= 0),
    confidence_score   INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
    confidence_scale   VARCHAR(20) DEFAULT '0_to_100'
        CHECK (confidence_scale IN ('0_to_100','1_to_5','1_to_7','low_med_high')),
    time_spent_seconds INTEGER,
    answered_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_test_response UNIQUE (attempt_id, question_id)
);
CREATE INDEX IF NOT EXISTS idx_test_responses_attempt  ON test_responses (attempt_id);
CREATE INDEX IF NOT EXISTS idx_test_responses_question ON test_responses (question_id);
CREATE INDEX IF NOT EXISTS idx_test_responses_user     ON test_responses (user_id);
CREATE INDEX IF NOT EXISTS idx_test_responses_test     ON test_responses (test_id);

-- =========================
-- MODULE 4: PROGRESS & GAMIFICATION
-- =========================

CREATE TABLE IF NOT EXISTS module_completions (
    completion_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id             UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    user_id               UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    completion_percentage INTEGER DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    is_completed          BOOLEAN DEFAULT FALSE,
    time_spent_minutes    INTEGER DEFAULT 0,
    completed_at          TIMESTAMP,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_module_completion UNIQUE (module_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_module_completions_user ON module_completions (user_id);

CREATE TABLE IF NOT EXISTS user_progress (
    progress_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id             UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    completion_percentage INTEGER DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    total_points_earned   INTEGER DEFAULT 0,
    average_score         INTEGER DEFAULT 0,
    time_spent_minutes    INTEGER DEFAULT 0,
    modules_completed     INTEGER DEFAULT 0,
    total_modules         INTEGER DEFAULT 0,
    tests_passed          INTEGER DEFAULT 0,
    tests_attempted       INTEGER DEFAULT 0,
    assignments_submitted INTEGER DEFAULT 0,
    assignments_graded    INTEGER DEFAULT 0,
    started_at            TIMESTAMP,
    completed_at          TIMESTAMP,
    last_activity         TIMESTAMP,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_progress UNIQUE (user_id, course_id)
);
CREATE INDEX IF NOT EXISTS idx_user_progress_user   ON user_progress (user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_course ON user_progress (course_id);

-- =========================
-- MODULE 5: CERTIFICATES
-- =========================

CREATE TABLE IF NOT EXISTS certificates (
    certificate_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(user_id),
    course_id         UUID REFERENCES courses(course_id),
    title             VARCHAR(255) NOT NULL,
    issued_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until       TIMESTAMP,
    issued_by         UUID REFERENCES users(user_id),
    file_url          TEXT,
    status            VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','revoked','expired')),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- MODULE 6: MEDIA & GRIDFS METADATA
-- =========================

CREATE TABLE IF NOT EXISTS media_metadata (
    media_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id         UUID REFERENCES modules(module_id),
    uploaded_by     UUID NOT NULL REFERENCES users(user_id),
    file_name       VARCHAR(255) NOT NULL,
    file_type       VARCHAR(50),
    file_size       BIGINT,
    mime_type       VARCHAR(100),
    duration        INTEGER,
    width           INTEGER,
    height          INTEGER,
    storage_path    TEXT,
    gridfs_id       UUID,
    storage_type    VARCHAR(10) DEFAULT 'gridfs' CHECK (storage_type IN ('gridfs','local','s3')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_media_unit_filetype ON media_metadata (unit_id, file_type);
CREATE INDEX IF NOT EXISTS idx_media_uploadedby    ON media_metadata (uploaded_by, uploaded_at);

-- =========================
-- MODULE 7: NOTES, FEEDBACK & NOTIFICATIONS
-- =========================

CREATE TABLE IF NOT EXISTS notes (
    note_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(user_id),
    module_id  UUID NOT NULL REFERENCES modules(module_id),
    content    TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES users(user_id),
    notification_type VARCHAR(50) CHECK (notification_type IN ('assignment','test','badge','deadline','course','grade','system','reminder')),
    title             VARCHAR(500),
    message           TEXT NOT NULL,
    link_url          TEXT,
    priority          VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
    status            VARCHAR(20) DEFAULT 'unread' CHECK (status IN ('unread','read','archived')),
    sent_via          VARCHAR(30) DEFAULT 'in_app' CHECK (sent_via IN ('in_app','email','both')),
    read_at           TIMESTAMP,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notifications_user    ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status  ON notifications (status);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications (created_at DESC);

-- =========================
-- MODULE 8: BADGES & LEADERBOARD
-- =========================

CREATE TABLE IF NOT EXISTS badges (
    badge_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    badge_name       VARCHAR(255) NOT NULL,
    description      TEXT,
    badge_type       VARCHAR(30) CHECK (badge_type IN ('gold','silver','bronze','positive','negative','custom')),
    badge_icon_url   TEXT,
    points_threshold INTEGER DEFAULT 0,
    visibility       VARCHAR(20) DEFAULT 'public' CHECK (visibility IN ('public','private')),
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS badge_assignments (
    badge_assignment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    badge_id            UUID NOT NULL REFERENCES badges(badge_id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_id           UUID REFERENCES courses(course_id),
    assigned_by         UUID REFERENCES users(user_id),
    reason              TEXT,
    earned_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_badge_assignments_user  ON badge_assignments (user_id);
CREATE INDEX IF NOT EXISTS idx_badge_assignments_badge ON badge_assignments (badge_id);

CREATE TABLE IF NOT EXISTS leaderboard (
    leaderboard_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope          VARCHAR(30) NOT NULL CHECK (scope IN ('global','team','course','batch','module')),
    scope_id       UUID,
    user_id        UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    points         INTEGER DEFAULT 0,
    rank           INTEGER,
    calculated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_leaderboard_scope ON leaderboard (scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_user  ON leaderboard (user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_rank  ON leaderboard (scope, rank);

-- =========================
-- MODULE 9: ASSIGNMENT RUBRICS (Optional granular scoring)
-- =========================

CREATE TABLE IF NOT EXISTS assignment_rubric_items (
    item_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id  UUID NOT NULL REFERENCES assignments(assignment_id) ON DELETE CASCADE,
    criterion      VARCHAR(255) NOT NULL,
    description    TEXT,
    max_points     INTEGER DEFAULT 0 CHECK (max_points >= 0),
    weight         NUMERIC(5,2) DEFAULT 0 CHECK (weight >= 0 AND weight <= 100),
    sequence_order INTEGER
);
CREATE INDEX IF NOT EXISTS idx_assignment_rubric_items_assignment ON assignment_rubric_items (assignment_id);

CREATE TABLE IF NOT EXISTS assignment_rubric_item_scores (
    item_score_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id  UUID NOT NULL REFERENCES assignment_submissions(submission_id) ON DELETE CASCADE,
    item_id        UUID NOT NULL REFERENCES assignment_rubric_items(item_id) ON DELETE CASCADE,
    points_awarded INTEGER DEFAULT 0 CHECK (points_awarded >= 0),
    feedback       TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_assignment_rubric_item_score UNIQUE (submission_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_assignment_rubric_item_scores_submission ON assignment_rubric_item_scores (submission_id);
CREATE INDEX IF NOT EXISTS idx_assignment_rubric_item_scores_item       ON assignment_rubric_item_scores (item_id);

-- ============================================================
-- ADD-ONS FROM ADMIN MODULE (Missing in Main)
-- ============================================================

-- 1) AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(user_id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id   VARCHAR(255),
    details     JSONB,
    ip_address  VARCHAR(45),
    user_agent  TEXT,
    "timestamp" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id     ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs (action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type ON audit_logs (entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp   ON audit_logs ("timestamp" DESC);

-- 2) COURSE ASSIGNMENTS (course -> team)
CREATE TABLE IF NOT EXISTS course_assignments (
    assignment_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id            UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    assigned_to_team_id  UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    assigned_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_course_assignments_course_id          ON course_assignments (course_id);
CREATE INDEX IF NOT EXISTS idx_course_assignments_assigned_to_team  ON course_assignments (assigned_to_team_id);

-- ============================================================
-- ADD-ONS FROM TRAINER MODULE (Missing in Main)
-- ============================================================

-- Content subtype tables for Units/Modules
CREATE TABLE IF NOT EXISTS video_units (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id                UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    video_url              TEXT,
    video_storage_path     VARCHAR(500),
    duration               INTEGER DEFAULT 0,
    completion_type        VARCHAR(20) DEFAULT 'full' CHECK (completion_type IN ('full','percentage')),
    required_watch_percentage INTEGER DEFAULT 100,
    allow_skip             BOOLEAN DEFAULT FALSE,
    allow_rewind           BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_video_units_unit ON video_units (unit_id);

CREATE TABLE IF NOT EXISTS audio_units (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id            UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    audio_url          TEXT,
    audio_storage_path VARCHAR(500),
    duration           INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_audio_units_unit ON audio_units (unit_id);

CREATE TABLE IF NOT EXISTS presentation_units (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id            UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    file_url           TEXT,
    file_storage_path  VARCHAR(500),
    slide_count        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_presentation_units_unit ON presentation_units (unit_id);

CREATE TABLE IF NOT EXISTS text_units (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    content TEXT
);
CREATE INDEX IF NOT EXISTS idx_text_units_unit ON text_units (unit_id);

CREATE TABLE IF NOT EXISTS page_units (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    content JSONB,
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_page_units_unit ON page_units (unit_id);

-- Quizzes (trainer-specific, separate from tests)
CREATE TABLE IF NOT EXISTS quizzes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id              UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    time_limit           INTEGER,
    passing_score        INTEGER DEFAULT 70,
    attempts_allowed     INTEGER DEFAULT 1,
    show_answers         BOOLEAN DEFAULT FALSE,
    randomize_questions  BOOLEAN DEFAULT FALSE,
    mandatory_completion BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_quizzes_unit ON quizzes (unit_id);

CREATE TABLE IF NOT EXISTS questions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id        UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    type           VARCHAR(20),
    text           TEXT,
    options        JSONB,
    correct_answer JSONB,
    points         INTEGER DEFAULT 1,
    "order"        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_questions_quiz      ON questions (quiz_id);
CREATE INDEX IF NOT EXISTS idx_questions_quiz_order ON questions (quiz_id, "order");

CREATE TABLE IF NOT EXISTS scorm_packages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id           UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    package_type      VARCHAR(20),
    file_url          TEXT,
    file_storage_path VARCHAR(500),
    version           VARCHAR(50),
    completion_tracking BOOLEAN DEFAULT TRUE,
    score_tracking      BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_scorm_packages_unit ON scorm_packages (unit_id);

CREATE TABLE IF NOT EXISTS surveys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id         UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    questions       JSONB,
    allow_anonymous BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_surveys_unit ON surveys (unit_id);

CREATE TABLE IF NOT EXISTS enrollments (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id            UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assigned_by          UUID REFERENCES users(user_id) ON DELETE SET NULL,
    status               VARCHAR(20) DEFAULT 'assigned' CHECK (status IN ('assigned','in_progress','completed')),
    progress_percentage  INTEGER DEFAULT 0,
    assigned_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at           TIMESTAMP,
    completed_at         TIMESTAMP,
    CONSTRAINT uq_enrollment UNIQUE (course_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments (course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user   ON enrollments (user_id);

CREATE TABLE IF NOT EXISTS unit_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id   UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    unit_id         UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started','in_progress','completed')),
    watch_percentage INTEGER DEFAULT 0,
    score           INTEGER,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    CONSTRAINT uq_unit_progress UNIQUE (enrollment_id, unit_id)
);
CREATE INDEX IF NOT EXISTS idx_unit_progress_enrollment ON unit_progress (enrollment_id);
CREATE INDEX IF NOT EXISTS idx_unit_progress_unit       ON unit_progress (unit_id);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id      UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    score        INTEGER DEFAULT 0,
    passed       BOOLEAN DEFAULT FALSE,
    answers      JSONB,
    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON quiz_attempts (quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts (user_id);

CREATE TABLE IF NOT EXISTS team_leaderboard (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id          UUID NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    course_id        UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    total_points     INTEGER DEFAULT 0,
    average_points   DOUBLE PRECISION DEFAULT 0.0,
    completed_units  INTEGER DEFAULT 0,
    total_members    INTEGER DEFAULT 0,
    active_members   INTEGER DEFAULT 0,
    quiz_score_total INTEGER DEFAULT 0,
    rank             INTEGER DEFAULT 0,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_team_leaderboard UNIQUE (team_id, course_id)
);
CREATE INDEX IF NOT EXISTS idx_team_leaderboard_team   ON team_leaderboard (team_id);
CREATE INDEX IF NOT EXISTS idx_team_leaderboard_course ON team_leaderboard (course_id);
CREATE INDEX IF NOT EXISTS idx_team_leaderboard_rank   ON team_leaderboard (rank);

-- ============================================================
-- ADD-ONS FROM TRAINEE MODULE - ASSESSMENTS (Missing in Main)
-- ============================================================

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id        UUID REFERENCES courses(course_id) ON DELETE CASCADE,
    module_id        UUID REFERENCES modules(module_id) ON DELETE CASCADE,
    title            VARCHAR(500) NOT NULL,
    description      TEXT,
    assessment_type  VARCHAR(30) CHECK (assessment_type IN ('descriptive','practical','oral','rubric','peer','survey','other')),
    due_date         TIMESTAMP,
    max_attempts     INTEGER DEFAULT 1 CHECK (max_attempts > 0),
    points_possible  INTEGER DEFAULT 100,
    is_mandatory     BOOLEAN DEFAULT TRUE,
    status           VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
    created_by       UUID NOT NULL REFERENCES users(user_id),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at       TIMESTAMP,
    version          INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_assessments_course ON assessments (course_id);
CREATE INDEX IF NOT EXISTS idx_assessments_module ON assessments (module_id);
CREATE INDEX IF NOT EXISTS idx_assessments_status ON assessments (status);

CREATE TABLE IF NOT EXISTS assessment_submissions (
    submission_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id     UUID NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    attempt_number    INTEGER NOT NULL DEFAULT 1,
    response_text     TEXT,
    response_file_url TEXT,
    score             INTEGER CHECK (score >= 0),
    feedback          TEXT,
    status            VARCHAR(30) DEFAULT 'submitted' CHECK (status IN ('draft','submitted','graded','returned')),
    submitted_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graded_by         UUID REFERENCES users(user_id),
    graded_at         TIMESTAMP,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_assessment_submission UNIQUE (assessment_id, user_id, attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_assessment_submissions_user       ON assessment_submissions (user_id);
CREATE INDEX IF NOT EXISTS idx_assessment_submissions_assessment ON assessment_submissions (assessment_id);

CREATE TABLE IF NOT EXISTS assessment_items (
    item_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id  UUID NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
    criterion      VARCHAR(255) NOT NULL,
    description    TEXT,
    max_points     INTEGER DEFAULT 0 CHECK (max_points >= 0),
    weight         NUMERIC(5,2) DEFAULT 0 CHECK (weight >= 0 AND weight <= 100),
    sequence_order INTEGER
);
CREATE INDEX IF NOT EXISTS idx_assessment_items_assessment ON assessment_items (assessment_id);

CREATE TABLE IF NOT EXISTS assessment_item_scores (
    item_score_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id  UUID NOT NULL REFERENCES assessment_submissions(submission_id) ON DELETE CASCADE,
    item_id        UUID NOT NULL REFERENCES assessment_items(item_id) ON DELETE CASCADE,
    points_awarded INTEGER DEFAULT 0 CHECK (points_awarded >= 0),
    feedback       TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_assessment_item_score UNIQUE (submission_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_assessment_item_scores_submission ON assessment_item_scores (submission_id);
CREATE INDEX IF NOT EXISTS idx_assessment_item_scores_item       ON assessment_item_scores (item_id);

-- =========================
-- END
-- =========================
"""

def main():
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        print("✅ LMS schema created/updated successfully (finalized with admin/trainer/trainee add-ons).")
    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Error applying schema:", e)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
