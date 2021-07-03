DROP TABLE IF EXISTS activities;

CREATE TABLE activities (
    name TEXT NOT NULL,
    sport TEXT NOT NULL,
    flags DICT NOT NULL,
    effort_level INT,
    start_time TIMESTAMP NOT NULL,
    distance REAL,
    duration TIMEDELTA NOT NULL,
    climb REAL,
    activity_id UUID PRIMARY KEY,
    username TEXT NOT NULL
);
