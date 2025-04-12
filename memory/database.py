# memory/database.py
import sqlite3
import json
import threading

class Database:
    _local = threading.local()
    
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_tables()
    
    @property
    def connection(self):
        """Thread-safe connection property"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            # Enable dictionary access to rows
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.connection.cursor()
        
        # Create job descriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_descriptions (
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
            CREATE TABLE IF NOT EXISTS candidates (
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
            CREATE TABLE IF NOT EXISTS matches (
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
        
        # Create skills table for taxonomy
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                category TEXT,
                aliases TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                feedback_text TEXT,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches (id)
            )
        ''')
        
        self.connection.commit()
    
    def create_tables(self):
        """Public method to create tables if they don't exist"""
        self._create_tables()
    
    def insert_job_description(self, jd_data):
        """Insert a job description into the database"""
        cursor = self.connection.cursor()
        
        try:
            # Convert lists to JSON strings
            if isinstance(jd_data.get('required_skills', []), list):
                required_skills = json.dumps(jd_data.get('required_skills', []))
            else:
                # Handle case where it's already a JSON string
                required_skills = jd_data.get('required_skills', '[]')
                if not required_skills.startswith('['):
                    required_skills = '[]'
                    
            if isinstance(jd_data.get('preferred_skills', []), list):
                preferred_skills = json.dumps(jd_data.get('preferred_skills', []))
            else:
                preferred_skills = jd_data.get('preferred_skills', '[]')
                if not preferred_skills.startswith('['):
                    preferred_skills = '[]'
                    
            if isinstance(jd_data.get('responsibilities', []), list):
                responsibilities = json.dumps(jd_data.get('responsibilities', []))
            else:
                responsibilities = jd_data.get('responsibilities', '[]')
                if not responsibilities.startswith('['):
                    responsibilities = '[]'
            
            # Ensure required_experience is an integer
            try:
                required_experience = int(jd_data.get('required_experience', 0))
            except (ValueError, TypeError):
                required_experience = 0
                
            # Ensure other fields are proper strings
            title = str(jd_data.get('title', '')) or 'Untitled Position'
            company = str(jd_data.get('company', '')) or 'Unknown Company'
            required_education = str(jd_data.get('required_education', '')) or ''
            
            cursor.execute('''
                INSERT INTO job_descriptions (
                    title,
                    company,
                    required_skills,
                    preferred_skills,
                    required_experience,
                    required_education,
                    responsibilities
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                title,
                company,
                required_skills,
                preferred_skills,
                required_experience,
                required_education,
                responsibilities
            ))
            
            jd_id = cursor.lastrowid
            self.connection.commit()
            return jd_id
        except Exception as e:
            print(f"Error inserting job description: {str(e)}")
            self.connection.rollback()
            
            # Try with minimal data on error
            try:
                cursor.execute('''
                    INSERT INTO job_descriptions (
                        title, company, required_skills, preferred_skills,
                        required_experience, required_education, responsibilities
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    "Untitled Position",
                    "Unknown Company",
                    "[]",
                    "[]",
                    0,
                    "",
                    "[]"
                ))
                
                jd_id = cursor.lastrowid
                self.connection.commit()
                return jd_id
            except Exception as backup_error:
                print(f"Backup insertion also failed: {str(backup_error)}")
                return 1  # Return a default ID to prevent errors
    
    def insert_candidate(self, cv_data):
        """Insert a candidate into the database"""
        cursor = self.connection.cursor()
        
        try:
            # Ensure the table exists and has the right columns
            self.create_tables()
            self._update_candidates_table()
            
            # Safety check for undefined values
            if not cv_data or not isinstance(cv_data, dict):
                print("Invalid cv_data received, cannot insert into database")
                return None
            
            # Clean any potentially problematic values
            for key in cv_data:
                # Fix any undefined string values
                if isinstance(cv_data[key], str) and cv_data[key] == "undefined":
                    if key in ["Skills", "Experience", "Education", "Certifications", "Languages"]:
                        cv_data[key] = []
                    else:
                        cv_data[key] = ""
                
                # Fix any None values in lists
                if isinstance(cv_data[key], list):
                    cv_data[key] = [item for item in cv_data[key] if item is not None and item != "undefined"]
            
            # Check if candidate with same ID already exists
            candidate_id = cv_data.get('Candidate_ID', '')
            if candidate_id and candidate_id != "undefined":
                cursor.execute("SELECT id FROM candidates WHERE candidate_id = ?", (candidate_id,))
                existing = cursor.fetchone()
                if existing:
                    # Update existing candidate
                    return self._update_candidate(existing['id'], cv_data)
            
            # Convert lists to JSON strings for storage
            # Use empty lists if any field is undefined or None
            skills = json.dumps(cv_data.get('Skills', []) or [])
            experience = json.dumps(cv_data.get('Experience', []) or [])
            education = json.dumps(cv_data.get('Education', []) or [])
            certifications = json.dumps(cv_data.get('Certifications', []) or [])
            languages = json.dumps(cv_data.get('Languages', []) or [])
            
            # Use empty string for text fields if undefined
            name = cv_data.get('Name', '') or ''
            email = cv_data.get('Email', '') or ''
            phone = cv_data.get('Phone', '') or ''
            summary = cv_data.get('Summary', '') or ''
            candidate_id_value = cv_data.get('Candidate_ID', '') or ''
            
            # If candidate_id is still empty or undefined, generate a new one
            if not candidate_id_value or candidate_id_value == "undefined":
                import time
                candidate_id_value = f"C{int(time.time()) % 10000}"
            
            # Add enhanced candidate data fields
            try:
                cursor.execute('''
                INSERT INTO candidates (
                    name, email, phone, skills, experience, education,
                    certifications, languages, summary, candidate_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name,
                    email,
                    phone,
                    skills,
                    experience,
                    education,
                    certifications,
                    languages,
                    summary,
                    candidate_id_value
                ))
            except sqlite3.OperationalError as e:
                print(f"Database error: {str(e)}")
                # Try to update the table schema
                self._update_candidates_table()
                
                # Try insert again
                cursor.execute('''
                INSERT INTO candidates (
                    name, email, phone, skills, experience, education,
                    certifications, languages, summary, candidate_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name,
                    email,
                    phone,
                    skills,
                    experience,
                    education,
                    certifications,
                    languages,
                    summary,
                    candidate_id_value
                ))
            
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting candidate: {str(e)}")
            import traceback
            traceback.print_exc()
            self.connection.rollback()
            raise

    def _update_candidate(self, candidate_id, cv_data):
        """Update an existing candidate record"""
        cursor = self.connection.cursor()
        
        # Convert lists to JSON strings for storage
        skills = json.dumps(cv_data.get('Skills', []) or [])
        experience = json.dumps(cv_data.get('Experience', []) or [])
        education = json.dumps(cv_data.get('Education', []) or [])
        certifications = json.dumps(cv_data.get('Certifications', []) or [])
        languages = json.dumps(cv_data.get('Languages', []) or [])
        
        cursor.execute('''
        UPDATE candidates SET
            name = ?, email = ?, phone = ?, skills = ?,
            experience = ?, education = ?, certifications = ?,
            languages = ?, summary = ?
        WHERE id = ?
        ''', (
            cv_data.get('Name', ''),
            cv_data.get('Email', ''),
            cv_data.get('Phone', ''),
            skills,
            experience,
            education,
            certifications,
            languages,
            cv_data.get('Summary', ''),
            candidate_id
        ))
        
        self.connection.commit()
        return candidate_id
    
    def _update_candidates_table(self):
        """Add missing columns to candidates table if they don't exist"""
        cursor = self.connection.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(candidates)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'certifications' not in columns:
            cursor.execute("ALTER TABLE candidates ADD COLUMN certifications TEXT")
        
        if 'languages' not in columns:
            cursor.execute("ALTER TABLE candidates ADD COLUMN languages TEXT")
            
        if 'summary' not in columns:
            cursor.execute("ALTER TABLE candidates ADD COLUMN summary TEXT")
            
        if 'candidate_id' not in columns:
            cursor.execute("ALTER TABLE candidates ADD COLUMN candidate_id TEXT")
            
        self.connection.commit()
    
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
        
        cursor.execute('''
            SELECT 
                id,
                title,
                company,
                required_skills,
                preferred_skills,
                required_experience,
                required_education,
                responsibilities,
                created_at
            FROM job_descriptions
            WHERE id = ?
        ''', (jd_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        jd_dict = {
            'id': row[0],
            'title': row[1],
            'company': row[2],
            'required_skills': json.loads(row[3]) if row[3] else [],
            'preferred_skills': json.loads(row[4]) if row[4] else [],
            'required_experience': row[5],
            'required_education': row[6],
            'responsibilities': json.loads(row[7]) if row[7] else [],
            'created_at': row[8]
        }
        
        return jd_dict
    
    def get_candidate(self, candidate_id):
        """Get a candidate by ID"""
        cursor = self.connection.cursor()
        
        # Try to get by internal ID first
        try:
            candidate_id_int = int(candidate_id)
            is_internal_id = True
        except (ValueError, TypeError):
            is_internal_id = False
        
        if is_internal_id:
            cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id_int,))
        else:
            # Handle string IDs (candidate_id field)
            cursor.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        # Convert database row to dictionary
        candidate = dict(row)
        
        # Parse JSON fields
        try:
            candidate['Skills'] = json.loads(candidate.get('skills', '[]'))
            candidate['Experience'] = json.loads(candidate.get('experience', '[]'))
            candidate['Education'] = json.loads(candidate.get('education', '[]'))
            candidate['Certifications'] = json.loads(candidate.get('certifications', '[]') or '[]')
            candidate['Languages'] = json.loads(candidate.get('languages', '[]') or '[]')
            
            # Map database field names to expected output names
            candidate['Name'] = candidate.get('name', '')
            candidate['Email'] = candidate.get('email', '')
            candidate['Phone'] = candidate.get('phone', '')
            candidate['Summary'] = candidate.get('summary', '')
            candidate['Candidate_ID'] = candidate.get('candidate_id', '')
            
            # Remove lowercase duplicates if we have the uppercase versions
            for field in ['name', 'email', 'phone', 'skills', 'experience', 'education', 
                         'certifications', 'languages', 'summary', 'candidate_id']:
                if field in candidate and field.capitalize() in candidate:
                    candidate.pop(field, None)
                    
            # Ensure we have the raw CV text if available (for reference)
            if 'cv_text' in candidate and candidate['cv_text']:
                candidate['raw_cv_text'] = candidate['cv_text']
                    
            # For debugging
            print(f"Candidate {candidate_id} has {len(candidate.get('Skills', []))} skills, {len(candidate.get('Experience', []))} experience entries")
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for candidate {candidate_id}: {str(e)}")
            # Provide empty lists instead of failing
            candidate['Skills'] = []
            candidate['Experience'] = []
            candidate['Education'] = []
            candidate['Certifications'] = []
            candidate['Languages'] = []
            
        # Ensure all necessary fields exist - empty lists or strings are better than missing fields 
        for field in ['Skills', 'Experience', 'Education', 'Certifications', 'Languages']:
            if field not in candidate or not candidate[field]:
                candidate[field] = []
                
        for field in ['Name', 'Email', 'Phone', 'Summary', 'Candidate_ID']:
            if field not in candidate or not candidate[field]:
                candidate[field] = ''
                
        return candidate

    def get_all_candidates(self):
        """Get all candidates"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM candidates")
        rows = cursor.fetchall()
        
        candidates = []
        for row in rows:
            candidate = dict(row)
            
            # Parse JSON fields
            try:
                candidate['Skills'] = json.loads(candidate.get('skills', '[]'))
                candidate['Experience'] = json.loads(candidate.get('experience', '[]'))
                candidate['Education'] = json.loads(candidate.get('education', '[]'))
                candidate['Certifications'] = json.loads(candidate.get('certifications', '[]') or '[]')
                candidate['Languages'] = json.loads(candidate.get('languages', '[]') or '[]')
                
                # Map database field names to expected output names
                candidate['Name'] = candidate.get('name', '')
                candidate['Email'] = candidate.get('email', '')
                candidate['Phone'] = candidate.get('phone', '')
                candidate['Summary'] = candidate.get('summary', '')
                candidate['Candidate_ID'] = candidate.get('candidate_id', '')
                
                # Remove lowercase duplicates if we have the uppercase versions
                for field in ['name', 'email', 'phone', 'skills', 'experience', 'education', 
                             'certifications', 'languages', 'summary', 'candidate_id']:
                    if field in candidate and field.capitalize() in candidate:
                        candidate.pop(field, None)
                
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON for candidate {candidate.get('id')}: {str(e)}")
                # Provide empty lists instead of failing
                candidate['Skills'] = []
                candidate['Experience'] = []
                candidate['Education'] = []
                candidate['Certifications'] = []
                candidate['Languages'] = []
            
            # Ensure all necessary fields exist - empty lists or strings are better than missing fields
            for field in ['Skills', 'Experience', 'Education', 'Certifications', 'Languages']:
                if field not in candidate or not candidate[field]:
                    candidate[field] = []
                    
            for field in ['Name', 'Email', 'Phone', 'Summary', 'Candidate_ID']:
                if field not in candidate or not candidate[field]:
                    candidate[field] = ''
                
            candidates.append(candidate)
            
        return candidates
    
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
