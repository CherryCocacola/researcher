-- Create base schema
CREATE SCHEMA IF NOT EXISTS researcher;

-- Researchers
CREATE TABLE IF NOT EXISTS researcher.researcher (
    researcher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT,
    rank TEXT,
    phone TEXT,
    email TEXT,
    major TEXT,
    office_location TEXT,
    lab_name TEXT,
    website TEXT,
    biography TEXT,
    career TEXT,
    research_area TEXT
);

-- Papers
CREATE TABLE IF NOT EXISTS researcher.paper (
    paper_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    grade TEXT,
    publisher TEXT,
    issn TEXT,
    country TEXT,
    jcr NUMERIC,
    impact_factor NUMERIC,
    notion_flag BOOLEAN,
    online_issn_flag BOOLEAN
);

-- Paper Authors (many-to-many)
CREATE TABLE IF NOT EXISTS researcher.paper_author (
    paper_id INTEGER REFERENCES researcher.paper(paper_id) ON DELETE CASCADE,
    researcher_id INTEGER REFERENCES researcher.researcher(researcher_id) ON DELETE CASCADE,
    is_corresponding BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (paper_id, researcher_id)
);

-- Paper Keywords (simple normalization)
CREATE TABLE IF NOT EXISTS researcher.paper_keyword (
    paper_id INTEGER REFERENCES researcher.paper(paper_id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    PRIMARY KEY (paper_id, keyword)
);

-- Patents
CREATE TABLE IF NOT EXISTS researcher.patent (
    patent_id INTEGER PRIMARY KEY,
    tech_type TEXT,
    title TEXT,
    category TEXT,
    lead_inventor_name TEXT,
    lead_inventor_id INTEGER,
    keywords TEXT
);

-- Pseudonym mapping (if provided)
CREATE TABLE IF NOT EXISTS researcher.pseudonym (
    researcher_id INTEGER PRIMARY KEY REFERENCES researcher.researcher(researcher_id) ON DELETE CASCADE,
    pseudonym TEXT
);

-- Vector tables compatible with current VectorUtils
CREATE TABLE IF NOT EXISTS researcher.researcher_profile_vector (
    researcher_id INTEGER PRIMARY KEY REFERENCES researcher.researcher(researcher_id) ON DELETE CASCADE,
    embedding TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS researcher.researcher_keyword_vector (
    researcher_id INTEGER REFERENCES researcher.researcher(researcher_id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    PRIMARY KEY (researcher_id, keyword)
);

CREATE TABLE IF NOT EXISTS researcher.research_paper_keyword_vector (
    researcher_id INTEGER REFERENCES researcher.researcher(researcher_id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    PRIMARY KEY (researcher_id, keyword)
);


