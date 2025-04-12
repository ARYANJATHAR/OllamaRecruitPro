import sqlite3

def init_db():
    conn = sqlite3.connect('ollamarecruitpro.db')
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS job_descriptions')
    cursor.execute('DROP TABLE IF EXISTS candidates')
    cursor.execute('DROP TABLE IF EXISTS matches')
    cursor.execute('DROP TABLE IF EXISTS skills')
    
    # Create job descriptions table without content column
    cursor.execute('''
    CREATE TABLE job_descriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        company TEXT,
        required_skills TEXT,
        preferred_skills TEXT,
        required_experience INTEGER,
        required_education TEXT,
        responsibilities TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create candidates table
    cursor.execute('''
    CREATE TABLE candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        candidate_id TEXT UNIQUE,
        skills TEXT,
        experience TEXT,
        education TEXT,
        certifications TEXT,
        languages TEXT,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create matches table
    cursor.execute('''
    CREATE TABLE matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jd_id INTEGER,
        candidate_id INTEGER,
        score REAL,
        analysis TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (jd_id) REFERENCES job_descriptions (id),
        FOREIGN KEY (candidate_id) REFERENCES candidates (id)
    )
    ''')
    
    # Create skills table
    cursor.execute('''
    CREATE TABLE skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()