# OllamaRecruitPro Project Structure

## Root Directory
- `main.py` - Main application entry point
- `app.py` - Flask application setup and routes
- `requirements.txt` - Project dependencies
- `init_db.py` - Database initialization script
- `job_description.csv` - Sample job descriptions data
- `ollamarecruitpro.db` - SQLite database file
- `recruit_pro.db` - Additional database file
- `__init__.py` - Package initialization file

## Core Components

### 1. UI Layer (`/ui`)
- **templates/** - HTML templates for the web interface
  - `index.html` - Main landing page with job description upload and CV upload forms
  - `upload.html` - File upload interface for CV documents
  - Contains frontend views and layouts

### 2. Agents Layer (`/agents`)
Core business logic components:
- `cv_parser.py` - CV parsing and extraction logic
- `jd_parser.py` - Job Description parsing and analysis
- `skill_matcher.py` - Skill matching algorithms
- `rank_score.py` - Candidate ranking and scoring
- `communicator.py` - Communication handling
- `feedback_learner.py` - Feedback processing and learning
- `dashboard.py` - Dashboard data processing

### 3. Memory Layer (`/memory`)
Data persistence and storage:
- `database.py` - Database operations and models
- `vector_store.py` - Vector storage for semantic search

### 4. Data Directories
- `cv_data/` - CV documents storage
- `cv_data_test/` - Test CV documents
- `venv/` - Python virtual environment

## Database
- SQLite database files:
  - `ollamarecruitpro.db`
  - `recruit_pro.db`

## Key Features
1. CV Processing
2. Job Description Analysis
3. Skill Matching
4. Candidate Ranking
5. Feedback Learning
6. Dashboard Analytics-
7. Vector-based Search

## Technology Stack
- Python
- Flask (Web Framework)
- SQLite (Database)
- Vector Storage
- HTML/CSS (Frontend) 