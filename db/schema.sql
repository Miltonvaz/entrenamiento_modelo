-- ENUM Types
CREATE TYPE user_role AS ENUM (
    'student', 'teacher', 'coordinator', 'report_viewer'
);

CREATE TYPE sync_status AS ENUM (
    'local_only', 'pending', 'synced', 'conflict'
);

-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    role          user_role NOT NULL,
    display_name  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Courses
CREATE TABLE courses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          TEXT,
    name          TEXT NOT NULL,
    career        TEXT,
    term          TEXT,
    teacher_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Topics
CREATE TABLE topics (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id     UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    sort_order    INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Class Sessions
CREATE TABLE class_sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    local_id          UUID,
    course_id         UUID REFERENCES courses(id) ON DELETE SET NULL,
    teacher_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    student_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    captor_device_id  UUID,
    session_title     TEXT,
    status            TEXT NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL,
    ended_at          TIMESTAMPTZ,
    duration_sec      INTEGER,
    sync_status       sync_status NOT NULL DEFAULT 'pending',
    synced_at         TIMESTAMPTZ,
    version           INTEGER NOT NULL DEFAULT 1
);

-- Session Topics (many-to-many relationship)
CREATE TABLE session_topics (
    session_id    UUID NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    topic_id      UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    source        TEXT NOT NULL CHECK (source IN ('manual', 'nlp_suggested')),
    PRIMARY KEY (session_id, topic_id)
);

-- Transcript Segments
CREATE TABLE transcript_segments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    local_id      UUID,
    session_id    UUID NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    sequence      INTEGER NOT NULL,
    raw_text      TEXT NOT NULL,
    text          TEXT NOT NULL,
    status        TEXT NOT NULL,
    offset_ms     INTEGER NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    sync_status   sync_status NOT NULL DEFAULT 'pending',
    version       INTEGER NOT NULL DEFAULT 1
);

-- PLN Annotations
CREATE TABLE segment_pln_annotations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_id    UUID NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
    type          TEXT NOT NULL CHECK (type IN ('term', 'normalization', 'punctuation')),
    payload       JSONB NOT NULL,
    start_offset  INTEGER,
    end_offset    INTEGER
);

-- Formula Blocks
CREATE TABLE formula_blocks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    segment_id    UUID REFERENCES transcript_segments(id) ON DELETE SET NULL,
    latex         TEXT NOT NULL,
    offset_ms     INTEGER NOT NULL,
    sync_status   sync_status NOT NULL DEFAULT 'pending'
);

-- Notes
CREATE TABLE notes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    segment_id    UUID REFERENCES transcript_segments(id) ON DELETE SET NULL,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content       TEXT NOT NULL,
    offset_ms     INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    sync_status   sync_status NOT NULL DEFAULT 'pending'
);

-- Hand Raise Events (Interaction)
CREATE TABLE hand_raise_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action        TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chat Messages
CREATE TABLE chat_messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID NOT NULL REFERENCES class_sessions(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'sent',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Teacher Voice Profiles
CREATE TABLE teacher_voice_profiles (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id         UUID REFERENCES courses(id) ON DELETE SET NULL,
    status            TEXT NOT NULL DEFAULT 'draft',
    sample_count_sec  INTEGER NOT NULL DEFAULT 0,
    enrolled_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Training Jobs
CREATE TABLE training_jobs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id    UUID NOT NULL REFERENCES teacher_voice_profiles(id) ON DELETE CASCADE,
    job_type      TEXT NOT NULL,  -- lexicon_only | fine_tune
    status        TEXT NOT NULL DEFAULT 'queued',
    error_message TEXT,
    queued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ
);

-- Model Versions (OTA)
CREATE TABLE model_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag     TEXT NOT NULL,
    teacher_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    course_id       UUID REFERENCES courses(id) ON DELETE SET NULL,
    artifact_type   TEXT NOT NULL,
    artifact_url    TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    size_bytes      BIGINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'draft',
    published_at    TIMESTAMPTZ,
    training_job_id UUID REFERENCES training_jobs(id) ON DELETE SET NULL
);

-- Sync Logs (audit/diagnostic)
CREATE TABLE sync_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id     UUID,
    direction     TEXT NOT NULL,
    records_count INTEGER NOT NULL,
    result        TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Devices
CREATE TABLE devices (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_role   TEXT NOT NULL,
    platform      TEXT NOT NULL,
    app_version   TEXT NOT NULL,
    last_seen     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit Trail
CREATE TABLE audit_trail (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    UUID REFERENCES class_sessions(id) ON DELETE SET NULL,
    reviewer_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    action        TEXT NOT NULL,
    metadata      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_segments_session ON transcript_segments(session_id, sequence);
CREATE INDEX idx_sessions_student ON class_sessions(student_id, started_at DESC);
CREATE INDEX idx_sessions_course ON class_sessions(course_id, started_at DESC);
CREATE INDEX idx_sessions_teacher ON class_sessions(teacher_id, started_at DESC);
CREATE INDEX idx_topics_course ON topics(course_id, sort_order);
CREATE INDEX idx_session_topics ON session_topics(topic_id);
CREATE INDEX idx_pln_segment ON segment_pln_annotations(segment_id);
CREATE INDEX idx_notes_session ON notes(session_id);
CREATE INDEX idx_hand_raise_session ON hand_raise_events(session_id);
CREATE INDEX idx_chat_session ON chat_messages(session_id);
CREATE INDEX idx_audit_session ON audit_trail(session_id);

-- View: Teacher session interaction summary
CREATE VIEW session_interaction_summary AS
SELECT
    s.id              AS session_id,
    s.course_id,
    s.teacher_id,
    s.session_title,
    s.started_at,
    s.ended_at,
    s.duration_sec,
    COUNT(DISTINCT h.id)       AS hand_raise_count,
    COUNT(DISTINCT c.id)       AS chat_message_count,
    COUNT(DISTINCT h.user_id)  AS students_hand_raise,
    COUNT(DISTINCT c.user_id)  AS students_chat
FROM class_sessions s
LEFT JOIN hand_raise_events h ON h.session_id = s.id
LEFT JOIN chat_messages c ON c.session_id = s.id
GROUP BY s.id, s.course_id, s.teacher_id, s.session_title,
         s.started_at, s.ended_at, s.duration_sec;
