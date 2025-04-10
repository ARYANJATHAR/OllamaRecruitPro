# memory/database.py
import sqlite3
import json
import threading

class Database:
    _local = threading.local()
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._setup_connection()
    
    def _setup_connection(self):
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
    
    @property
    def connection(self):
        self._setup_connection()
        return self._local.connection
    
    def create_tables(self):
        """Create the necessary database tables if they don't exist"""
        cursor = self.connection.cursor()
        
        # Job Descriptions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id INTEGER PRIMARY KEY,
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
        
        # Candidates table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            skills TEXT,
            experience TEXT,
            education TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Matches table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            jd_id INTEGER,
            candidate_id INTEGER,
            score REAL,
            justification TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (jd_id) REFERENCES job_descriptions(id),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
        ''')
        
        # Skills taxonomy table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            category TEXT,
            aliases TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Feedback table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY,
            match_id INTEGER,
            feedback_text TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches (id)
        )
        ''')
        
        self.connection.commit()
    
    def insert_job_description(self, jd_data):
        """Insert a job description into the database"""
        cursor = self.connection.cursor()
        
        # Convert lists to JSON strings for storage
        required_skills = json.dumps(jd_data.get('Required Skills', []))
        preferred_skills = json.dumps(jd_data.get('Preferred Skills', []))
        responsibilities = json.dumps(jd_data.get('Job Responsibilities', []))
        
        cursor.execute('''
        INSERT INTO job_descriptions (
            title, company, required_skills, preferred_skills,
            required_experience, required_education, responsibilities
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            jd_data.get('Job Title', ''),
            jd_data.get('Company Name', ''),
            required_skills,
            preferred_skills,
            jd_data.get('Required Experience', 0),
            jd_data.get('Required Education', ''),
            responsibilities
        ))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def insert_candidate(self, cv_data):
        """Insert a candidate into the database"""
        cursor = self.connection.cursor()
        
        # Convert lists to JSON strings for storage
        skills = json.dumps(cv_data.get('Skills', []))
        experience = json.dumps(cv_data.get('Experience', []))
        education = json.dumps(cv_data.get('Education', []))
        
        cursor.execute('''
        INSERT INTO candidates (
            name, email, phone, skills, experience, education
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            cv_data.get('Name', ''),
            cv_data.get('Email', ''),
            cv_data.get('Phone', ''),
            skills,
            experience,
            education
        ))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def insert_match(self, jd_id, candidate_id, score, justification):
        """Insert a match into the database"""
        cursor = self.connection.cursor()
        
        cursor.execute('''
        INSERT INTO matches (
            jd_id, candidate_id, score, justification
        ) VALUES (?, ?, ?, ?)
        ''', (jd_id, candidate_id, score, justification))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def insert_skill_if_not_exists(self, skill_name, category=None, aliases=None):
        """Insert a skill into the taxonomy if it doesn't exist"""
        cursor = self.connection.cursor()
        
        # Check if skill exists
        cursor.execute('SELECT id FROM skills WHERE name = ?', (skill_name,))
        result = cursor.fetchone()
        
        if result is None:
            # Skill doesn't exist, insert it
            aliases_json = json.dumps(aliases or [])
            
            cursor.execute('''
            INSERT INTO skills (name, category, aliases)
            VALUES (?, ?, ?)
            ''', (skill_name, category or 'Uncategorized', aliases_json))
            
            self.connection.commit()
            return cursor.lastrowid
        
        return result['id']
    
    def get_job_description(self, jd_id):
        """Get a job description by ID"""
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT * FROM job_descriptions WHERE id = ?', (jd_id,))
        row = cursor.fetchone()
        
        if row:
            result = dict(row)
            # Parse JSON strings back to lists
            result['required_skills'] = json.loads(result['required_skills'])
            result['preferred_skills'] = json.loads(result['preferred_skills'])
            result['responsibilities'] = json.loads(result['responsibilities'])
            return result
        
        return None
    
    def get_candidate(self, candidate_id):
        """Get a candidate by ID"""
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
        row = cursor.fetchone()
        
        if row:
            result = dict(row)
            # Parse JSON strings back to lists
            result['skills'] = json.loads(result['skills'])
            result['experience'] = json.loads(result['experience'])
            result['education'] = json.loads(result['education'])
            return result
        
        return None
    
    def get_all_candidates(self):
        """Get all candidates"""
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT * FROM candidates')
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON strings back to lists
            result['skills'] = json.loads(result['skills'])
            result['experience'] = json.loads(result['experience'])
            result['education'] = json.loads(result['education'])
            results.append(result)
        
        return results
    
    def get_match(self, match_id):
        """Get a match by ID"""
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT * FROM matches WHERE id = ?', (match_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        
        return None
    
    def update_match_status(self, match_id, status):
        """Update a match status"""
        cursor = self.connection.cursor()
        
        cursor.execute('''
        UPDATE matches SET status = ? WHERE id = ?
        ''', (status, match_id))
        
        self.connection.commit()
        
    def insert_feedback(self, match_id, feedback_text, rating):
        """Insert feedback for a match"""
        cursor = self.connection.cursor()
        
        cursor.execute('''
        INSERT INTO feedback (match_id, feedback_text, rating)
        VALUES (?, ?, ?)
        ''', (match_id, feedback_text, rating))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def __del__(self):
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection
