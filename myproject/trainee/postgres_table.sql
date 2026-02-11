
-- ============================================================
-- LMS Database (PostgreSQL) - Full DDL from LMS-Schema.docx
-- ============================================================
-- Create database
CREATE DATABASE LMS;

-- Use pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================
-- MODULE 1: USER & TEAM MGMT
-- =========================

-- 1. roles
CREATE TABLE IF NOT EXISTS roles (
  role_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_name     VARCHAR(50) NOT NULL UNIQUE CHECK (role_name IN ('admin','trainer','manager','trainee')),
  description   TEXT,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. users
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
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_role   ON users (primary_role);
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);
CREATE INDEX IF NOT EXISTS idx_users_email  ON users (email);

-- 3. user_roles (M:N users <-> roles)
CREATE TABLE IF NOT EXISTS user_roles (
  user_id     UUID NOT NULL,
  role_id     UUID NOT NULL,
  assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  assigned_by UUID,
  PRIMARY KEY (user_id, role_id),
  CONSTRAINT fk_ur_user  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_ur_role  FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE CASCADE,
  CONSTRAINT fk_ur_by    FOREIGN KEY (assigned_by) REFERENCES users(user_id)
);

-- 4. teams
CREATE TABLE IF NOT EXISTS teams (
  team_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_name   VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  status      VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active','inactive','archived')),
  manager_id  UUID REFERENCES users(user_id) ON DELETE SET NULL,
  created_by  UUID REFERENCES users(user_id),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_teams_manager ON teams (manager_id);

-- 5. team_members (M:N teams <-> users)
CREATE TABLE IF NOT EXISTS team_members (
  team_id         UUID NOT NULL,
  user_id         UUID NOT NULL,
  is_primary_team BOOLEAN DEFAULT TRUE,
  assigned_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  assigned_by     UUID REFERENCES users(user_id),
  PRIMARY KEY (team_id, user_id),
  CONSTRAINT fk_tm_team FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE,
  CONSTRAINT fk_tm_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members (user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members (team_id);

-- =========================
-- MODULE 2: COURSES & MODULES
-- =========================

-- 6. courses
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
  updated_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_courses_created_by ON courses (created_by);
CREATE INDEX IF NOT EXISTS idx_courses_status     ON courses (status);

-- 7. course_prerequisites
CREATE TABLE IF NOT EXISTS course_prerequisites (
  course_id               UUID NOT NULL,
  prerequisite_course_id  UUID NOT NULL,
  created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (course_id, prerequisite_course_id),
  CONSTRAINT chk_course_prereq_self CHECK (course_id <> prerequisite_course_id),
  CONSTRAINT fk_cp_course    FOREIGN KEY (course_id)              REFERENCES courses(course_id) ON DELETE CASCADE,
  CONSTRAINT fk_cp_prereq    FOREIGN KEY (prerequisite_course_id) REFERENCES courses(course_id) ON DELETE CASCADE
);

-- 8. course_assignments (assign course to user OR team)
CREATE TABLE IF NOT EXISTS course_assignments (
  assignment_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id              UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  assigned_to_user_id    UUID REFERENCES users(user_id) ON DELETE CASCADE,
  assigned_to_team_id    UUID REFERENCES teams(team_id) ON DELETE CASCADE,
  assigned_by            UUID NOT NULL REFERENCES users(user_id),
  due_date               TIMESTAMP,
  assigned_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  -- Either user OR team (not both)
  CONSTRAINT chk_course_assign_target
    CHECK (
      (assigned_to_user_id IS NOT NULL AND assigned_to_team_id IS NULL)
      OR
      (assigned_to_user_id IS NULL AND assigned_to_team_id IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_course_assignments_user ON course_assignments (assigned_to_user_id);
CREATE INDEX IF NOT EXISTS idx_course_assignments_team ON course_assignments (assigned_to_team_id);

-- 9. modules
CREATE TABLE IF NOT EXISTS modules (
  module_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id                 UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  title                     VARCHAR(500) NOT NULL,
  description               TEXT,
  module_type               VARCHAR(30) CHECK (module_type IN ('video','pdf','ppt','document','quiz','mixed')),
  sequence_order            INTEGER NOT NULL,
  is_mandatory              BOOLEAN DEFAULT TRUE,
  estimated_duration_minutes INTEGER,
  video_count               INTEGER DEFAULT 0,
  has_quizzes               BOOLEAN DEFAULT FALSE,
  created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_module_sequence UNIQUE (course_id, sequence_order)
);
CREATE INDEX IF NOT EXISTS idx_modules_course   ON modules (course_id);
CREATE INDEX IF NOT EXISTS idx_modules_sequence ON modules (course_id, sequence_order);

-- 10. module_sequencing
CREATE TABLE IF NOT EXISTS module_sequencing (
  sequence_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id             UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  module_id             UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
  preceding_module_id   UUID REFERENCES modules(module_id) ON DELETE CASCADE,
  drip_feed_rule        VARCHAR(30) DEFAULT 'none' CHECK (drip_feed_rule IN ('none','time_based','completion_based')),
  drip_feed_delay_days  INTEGER DEFAULT 0,
  prerequisite_completed BOOLEAN DEFAULT FALSE,
  created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_module_seq UNIQUE (course_id, module_id)
);

-- 11. module_completions
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

-- 12. notes
CREATE TABLE IF NOT EXISTS notes (
  note_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  module_id   UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
  content     TEXT NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- MODULE 3: ASSIGNMENTS & TESTS
-- =========================

-- 13. assignments
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
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_assignments_course ON assignments (course_id);

-- 14. assignment_targeting
CREATE TABLE IF NOT EXISTS assignment_targeting (
  assignment_target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id        UUID NOT NULL REFERENCES assignments(assignment_id) ON DELETE CASCADE,
  assigned_to_user_id  UUID REFERENCES users(user_id) ON DELETE CASCADE,
  assigned_to_team_id  UUID REFERENCES teams(team_id) ON DELETE CASCADE,
  assigned_by          UUID NOT NULL REFERENCES users(user_id),
  assigned_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_assignment_target
    CHECK (
      (assigned_to_user_id IS NOT NULL AND assigned_to_team_id IS NULL)
      OR
      (assigned_to_user_id IS NULL AND assigned_to_team_id IS NOT NULL)
    )
);

-- 15. assignment_submissions
CREATE TABLE IF NOT EXISTS assignment_submissions (
  submission_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id    UUID NOT NULL REFERENCES assignments(assignment_id) ON DELETE CASCADE,
  user_id          UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  attempt_number   INTEGER NOT NULL DEFAULT 1,
  submission_text  TEXT,
  submission_files JSONB,
  submitted_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status           VARCHAR(30) DEFAULT 'submitted' CHECK (status IN ('draft','submitted','graded','returned')),
  score            INTEGER CHECK (score >= 0),
  points_earned    INTEGER DEFAULT 0,
  feedback         TEXT,
  graded_by        UUID REFERENCES users(user_id),
  graded_at        TIMESTAMP,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_assignment_submissions_user      ON assignment_submissions (user_id);
CREATE INDEX IF NOT EXISTS idx_assignment_submissions_assignment ON assignment_submissions (assignment_id);

-- 16. test_bank
CREATE TABLE IF NOT EXISTS test_bank (
  test_bank_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          VARCHAR(255) NOT NULL,
  description   TEXT,
  category      VARCHAR(100),
  created_by    UUID NOT NULL REFERENCES users(user_id),
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. tests
CREATE TABLE IF NOT EXISTS tests (
  test_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id           UUID REFERENCES courses(course_id) ON DELETE CASCADE,
  module_id           UUID REFERENCES modules(module_id) ON DELETE CASCADE,
  test_bank_id        UUID REFERENCES test_bank(test_bank_id),
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
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tests_course ON tests (course_id);

-- 18. test_questions
CREATE TABLE IF NOT EXISTS test_questions (
  question_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  test_id        UUID REFERENCES tests(test_id) ON DELETE CASCADE,
  test_bank_id   UUID REFERENCES test_bank(test_bank_id),
  question_text  TEXT NOT NULL,
  question_type  VARCHAR(30) NOT NULL CHECK (question_type IN ('mcq','true_false','short_answer','essay','fill_blank')),
  options        JSONB,
  correct_answer TEXT,
  points         INTEGER DEFAULT 1,
  difficulty     VARCHAR(20) CHECK (difficulty IN ('easy','medium','hard')),
  explanation   TEXT,
  sequence_order INTEGER,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 19. test_attempts
CREATE TABLE IF NOT EXISTS test_attempts (
  attempt_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  test_id          UUID NOT NULL REFERENCES tests(test_id) ON DELETE CASCADE,
  user_id          UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  attempt_number   INTEGER NOT NULL,
  started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  submitted_at     TIMESTAMP,
  time_spent_minutes INTEGER,
  status           VARCHAR(30) DEFAULT 'in_progress' CHECK (status IN ('in_progress','completed','abandoned','timed_out')),
  score            INTEGER CHECK (score >= 0 AND score <= 100),
  points_earned    INTEGER DEFAULT 0,
  passed           BOOLEAN,
  graded_by        UUID REFERENCES users(user_id),
  graded_at        TIMESTAMP,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_test_attempt UNIQUE (test_id, user_id, attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_test_attempts_user ON test_attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_test_attempts_test ON test_attempts (test_id);

-- 20. test_answers
CREATE TABLE IF NOT EXISTS test_answers (
  answer_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id     UUID NOT NULL REFERENCES test_attempts(attempt_id) ON DELETE CASCADE,
  question_id    UUID NOT NULL REFERENCES test_questions(question_id) ON DELETE CASCADE,
  answer_text    TEXT,
  selected_options JSONB,
  is_correct     BOOLEAN,
  points_earned  INTEGER DEFAULT 0,
  feedback       TEXT,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_test_answer UNIQUE (attempt_id, question_id)
);

-- =========================
-- MODULE 4: PROGRESS & GAMIFICATION
-- =========================

-- 21. user_progress
CREATE TABLE IF NOT EXISTS user_progress (
  progress_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  course_id            UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  completion_percentage INTEGER DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
  total_points_earned  INTEGER DEFAULT 0,
  average_score        INTEGER DEFAULT 0,
  time_spent_minutes   INTEGER DEFAULT 0,
  modules_completed    INTEGER DEFAULT 0,
  total_modules        INTEGER DEFAULT 0,
  tests_passed         INTEGER DEFAULT 0,
  tests_attempted      INTEGER DEFAULT 0,
  assignments_submitted INTEGER DEFAULT 0,
  assignments_graded   INTEGER DEFAULT 0,
  started_at           TIMESTAMP,
  completed_at         TIMESTAMP,
  last_activity        TIMESTAMP,
  created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_user_progress UNIQUE (user_id, course_id)
);
CREATE INDEX IF NOT EXISTS idx_user_progress_user   ON user_progress (user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_course ON user_progress (course_id);

-- 22. badge_rules
CREATE TABLE IF NOT EXISTS badge_rules (
  rule_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name   VARCHAR(255) NOT NULL,
  rule_type   VARCHAR(50) CHECK (rule_type IN ('points_threshold','completion','score','streak','deadline','custom')),
  description TEXT,
  criteria    JSONB NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 23. badges
CREATE TABLE IF NOT EXISTS badges (
  badge_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  badge_name       VARCHAR(255) NOT NULL,
  description      TEXT,
  badge_type       VARCHAR(30) CHECK (badge_type IN ('gold','silver','bronze','positive','negative','custom')),
  badge_icon_url   TEXT,
  rule_id          UUID REFERENCES badge_rules(rule_id),
  points_threshold INTEGER DEFAULT 0,
  visibility       VARCHAR(20) DEFAULT 'public' CHECK (visibility IN ('public','private')),
  is_active        BOOLEAN DEFAULT TRUE,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 24. badge_assignments
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

-- 25. leaderboard
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
-- MODULE 5: NOTIFICATIONS & AUDIT
-- =========================

-- 26. notifications
CREATE TABLE IF NOT EXISTS notifications (
  notification_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  notification_type VARCHAR(50) CHECK (notification_type IN ('assignment','test','badge','deadline','course','grade','system','reminder')),
  title            VARCHAR(500),
  message          TEXT NOT NULL,
  link_url         TEXT,
  priority         VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
  status           VARCHAR(20) DEFAULT 'unread' CHECK (status IN ('unread','read','archived')),
  sent_via         VARCHAR(30) DEFAULT 'in_app' CHECK (sent_via IN ('in_app','email','both')),
  read_at          TIMESTAMP,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notifications_user    ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status  ON notifications (status);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications (created_at DESC);

-- 27. audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
  log_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(user_id),
  action_type VARCHAR(100) NOT NULL,
  entity_type VARCHAR(100),
  entity_id   UUID,
  details     JSONB,
  ip_address  INET,
  user_agent  TEXT,
  timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user      ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity    ON audit_logs (entity_type, entity_id);

-- =========================
-- MODULE 6: FEEDBACK & COMMUNICATION
-- =========================

-- 28. feedback
CREATE TABLE IF NOT EXISTS feedback (
  feedback_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  course_id     UUID REFERENCES courses(course_id),
  module_id     UUID REFERENCES modules(module_id),
  feedback_type VARCHAR(30) CHECK (feedback_type IN ('course','module','trainer','system','general')),
  rating        INTEGER CHECK (rating >= 1 AND rating <= 5),
  content       TEXT NOT NULL,
  is_anonymous  BOOLEAN DEFAULT FALSE,
  status        VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','reviewed','resolved')),
  reviewed_by   UUID REFERENCES users(user_id),
  reviewed_at   TIMESTAMP,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

