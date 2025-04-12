# ollamarecruitpro/__init__.py
import ollama
import sqlite3
from agents.jd_parser import JDParserAgent
from agents.cv_parser import CVParserAgent
from agents.skill_matcher import SkillMatcherAgent
from agents.rank_score import RankScoreAgent
from agents.feedback_learner import FeedbackLearnerAgent
from agents.communicator import CommunicatorAgent
from agents.dashboard import DashboardAgent
from memory.database import Database
from memory.vector_store import VectorStore
import json

class OllamaRecruitPro:
    def __init__(self):
        # Initialize database
        self.db = Database("ollamarecruitpro.db")
        self.vector_store = VectorStore()
        
        # Modified models to use available ones
        self.models = {
            'general': "mistral",     # Keep this as is
            'reasoning': "llama2",    # Replace phi-2 with llama2
            'structured': "mistral"   # Replace tinyllama with mistral if tinyllama isn't available
        }
        
        # Initialize agents
        self.jd_parser = JDParserAgent(self.models['general'], self.db)
        self.cv_parser = CVParserAgent(self.models['general'], self.db)
        self.skill_matcher = SkillMatcherAgent(self.models['reasoning'], self.vector_store)
        self.rank_score = RankScoreAgent(self.models['reasoning'], self.db)
        self.feedback_learner = FeedbackLearnerAgent(self.models['structured'], self.db)
        self.communicator = CommunicatorAgent(self.models['general'], self.db)
        self.dashboard = DashboardAgent(self.db)
    
    def process_job_description(self, jd_text):
        """Process a job description and store it in the database"""
        try:
            # Check if input is JSON format
            try:
                if jd_text.strip().startswith('{'):
                    jd_data = json.loads(jd_text)
                    print(f"Successfully parsed job description JSON: {jd_data.get('title', 'No title')}")
                else:
                    # Plain text, parse with jd_parser
                    print("Parsing plain text job description")
                    jd_data = self.jd_parser.parse(jd_text)
            except json.JSONDecodeError:
                # Not valid JSON, parse with jd_parser
                print("Failed to parse as JSON, parsing with jd_parser")
                jd_data = self.jd_parser.parse(jd_text)
                
            if not jd_data:
                print("Error: JD parser returned empty data")
                # Provide minimal structure to prevent errors
                jd_data = {
                    "title": "Untitled Position",
                    "company": "Unknown Company",
                    "required_skills": [],
                    "preferred_skills": [],
                    "required_experience": 0,
                    "required_education": "",
                    "responsibilities": []
                }
                
            # Ensure all required fields exist
            if 'title' not in jd_data:
                jd_data['title'] = "Untitled Position"
            if 'company' not in jd_data:
                jd_data['company'] = "Unknown Company"
            if 'required_skills' not in jd_data:
                jd_data['required_skills'] = []
            if 'preferred_skills' not in jd_data:
                jd_data['preferred_skills'] = []
                
            jd_id = self.db.insert_job_description(jd_data)
            print(f"Inserted job description with ID: {jd_id}")
            return jd_id
        except Exception as e:
            print(f"Error processing job description: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Create a minimal job description to prevent further errors
            basic_jd = {
                "title": "Untitled Position",
                "company": "Unknown Company",
                "required_skills": [],
                "preferred_skills": [],
                "required_experience": 0,
                "required_education": "",
                "responsibilities": []
            }
            
            try:
                jd_id = self.db.insert_job_description(basic_jd)
                return jd_id
            except:
                # If all else fails, return 1 to prevent null references
                return 1
    
    def process_cv(self, cv_text):
        """Process a CV and store it in the database"""
        try:
            if not cv_text or len(cv_text.strip()) < 10:
                print("CV text is too short or empty")
                return None
            
            # Remove any 'undefined' text in the input
            cv_text = cv_text.replace("undefined", "")
            
            # Parse the CV
            cv_data = self.cv_parser.parse(cv_text)
            
            if not cv_data:
                print("CV parser returned None or empty data")
                return None
            
            # Check for 'undefined' in the entire data structure
            try:
                cv_data_str = json.dumps(cv_data)
                if "undefined" in cv_data_str:
                    print("Found 'undefined' in CV data, cleaning...")
                    # Clean all string fields
                    for key, value in cv_data.items():
                        if isinstance(value, str) and value == "undefined":
                            cv_data[key] = ""
                        elif isinstance(value, list):
                            cv_data[key] = [item for item in value if item != "undefined"]
            except:
                print("Error converting CV data to JSON")
            
            # Validate required fields
            required_fields = ["Name", "Email", "Phone", "Candidate_ID", "Skills", "Experience", "Education"]
            for field in required_fields:
                if field not in cv_data:
                    print(f"Missing required field: {field}")
                    if field in ["Skills", "Experience", "Education"]:
                        cv_data[field] = []
                    else:
                        cv_data[field] = ""
                elif cv_data[field] == "undefined":
                    print(f"Found 'undefined' in field: {field}")
                    if field in ["Skills", "Experience", "Education"]:
                        cv_data[field] = []
                    else:
                        cv_data[field] = ""
            
            # Ensure list fields are lists
            list_fields = ["Skills", "Experience", "Education", "Certifications", "Languages"]
            for field in list_fields:
                if field not in cv_data:
                    cv_data[field] = []
                elif cv_data[field] == "undefined":
                    cv_data[field] = []
                elif not isinstance(cv_data[field], list):
                    if cv_data[field]:
                        cv_data[field] = [cv_data[field]]
                    else:
                        cv_data[field] = []
                    
                # Final cleanup of list items
                if isinstance(cv_data[field], list):
                    cv_data[field] = [item for item in cv_data[field] 
                                    if item and item != "undefined" and item != "None"]
            
            # Ensure Candidate_ID is properly formatted
            if not cv_data.get("Candidate_ID") or cv_data.get("Candidate_ID") == "undefined":
                import time
                cv_data["Candidate_ID"] = f"C{int(time.time()) % 10000}"
            elif not str(cv_data["Candidate_ID"]).startswith("C"):
                cv_data["Candidate_ID"] = "C" + str(cv_data["Candidate_ID"])
            
            # Insert into database
            try:
                candidate_id = self.db.insert_candidate(cv_data)
                return candidate_id
            except Exception as db_error:
                print(f"Database error inserting candidate: {str(db_error)}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            print(f"Error in process_cv: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def match_candidates(self, jd_id, candidate_ids=None):
        """Match candidates to a job description"""
        print(f"Starting matching process for JD ID: {jd_id}")
        jd_data = self.db.get_job_description(jd_id)
        if not jd_data:
            print(f"No job description found for ID: {jd_id}")
            return []
            
        print(f"Found job description: {jd_data.get('title', 'Unknown Title')}")
        
        # Get all candidates if not specified
        if not candidate_ids:
            candidates = self.db.get_all_candidates()
            print(f"No specific candidates provided, using all {len(candidates)} candidates from database")
        else:
            candidates = []
            for cid in candidate_ids:
                candidate = self.db.get_candidate(cid)
                if candidate:
                    candidates.append(candidate)
                    print(f"Found candidate {candidate.get('Candidate_ID', 'Unknown ID')}: {candidate.get('Name', 'Unknown')}")
                else:
                    print(f"Could not find candidate with ID {cid}")
        
        print(f"Processing {len(candidates)} candidates")
        
        matches = []
        for candidate in candidates:
            friendly_id = candidate.get('Candidate_ID', 'Unknown ID')
            print(f"Processing candidate {friendly_id} - {candidate.get('Name', 'Unknown')}")
            
            # Extract detailed candidate information from CV for better matching
            candidate_skills = candidate.get('Skills', [])
            candidate_experience = candidate.get('Experience', [])
            candidate_education = candidate.get('Education', [])
            candidate_certifications = candidate.get('Certifications', [])
            
            # Extract job requirements
            required_skills = jd_data.get('Required Skills', [])
            preferred_skills = jd_data.get('Preferred Skills', [])
            required_experience = jd_data.get('required_experience', 0)
            required_education = jd_data.get('required_education', '')
            
            # Generate comprehensive match analysis based on actual CV content
            match_score, analysis = self.skill_matcher.match(jd_data, candidate)
            print(f"Raw match score: {match_score}")
            
            # Calculate ranked score using explicit criteria and weights from CV content
            ranked_score = self.rank_score.calculate(match_score, jd_data, candidate)
            print(f"Ranked score: {ranked_score}")
            
            # Store complete candidate information for better output
            candidate_info = {
                'id': candidate.get('id'),
                'candidate_id': friendly_id,
                'name': candidate.get('Name', 'Unknown'),
                'email': candidate.get('Email', 'Unknown'),
                'phone': candidate.get('Phone', 'Unknown'),
                'skills': candidate_skills,
                'experience': candidate_experience,
                'education': candidate_education,
                'certifications': candidate_certifications,
                'languages': candidate.get('Languages', []),
                'summary': candidate.get('Summary', '')
            }
            
            # Enhanced match information
            match_details = {
                'candidate_id': candidate.get('id'),  # Keep the database ID for internal use
                'friendly_id': friendly_id,  # Add the friendly ID for display
                'candidate_info': candidate_info,
                'score': ranked_score,
                'raw_score': match_score,
                'analysis': analysis,
                'jd_title': jd_data.get('title', 'Job Position'),
                'jd_company': jd_data.get('company', 'Company'),
                'match_date': 'Today'  # Would use actual timestamp in production
            }
            
            # Apply threshold filter (adjustable)
            threshold = 0.5  # 50% threshold for shortlisting
            if ranked_score >= threshold:
                matches.append(match_details)
                print(f"Added candidate {friendly_id} to matches with score {ranked_score}")
                
                # Store match in database with the comprehensive analysis
                self.db.insert_match(jd_id, candidate['id'], ranked_score, analysis)
        
        print(f"Completed matching. Found {len(matches)} matches above threshold")
        # Sort by score descending
        return sorted(matches, key=lambda x: x['score'], reverse=True)
    
    def get_candidate_details(self, candidate_id):
        """Get detailed information about a candidate"""
        candidate = self.db.get_candidate(candidate_id)
        if candidate:
            return {
                'id': candidate['id'],
                'candidate_id': candidate.get('Candidate_ID', ''),  # Include the friendly Candidate_ID
                'name': candidate.get('Name', 'Unknown'),
                'email': candidate.get('Email', 'Unknown'),
                'phone': candidate.get('Phone', 'Unknown'), 
                'skills': candidate.get('Skills', []),
                'experience': candidate.get('Experience', []),
                'education': candidate.get('Education', []),
                'certifications': candidate.get('Certifications', []),
                'languages': candidate.get('Languages', []),
                'summary': candidate.get('Summary', '')
            }
        return None
        
    def send_interview_requests(self, jd_id, candidate_ids):
        """Send interview requests to selected candidates"""
        jd_data = self.db.get_job_description(jd_id)
        
        for candidate_id in candidate_ids:
            candidate_data = self.db.get_candidate(candidate_id)
            
            # Generate email from template
            email = self.communicator.generate_interview_email(
                jd_data, candidate_data
            )
            
            # In a real system, we would send the email here
            # For the hackathon, we'll just log it
            print(f"Interview request sent to {candidate_data.get('Name', 'candidate')} ({candidate_id})")
    
    def send_rejection_emails(self, jd_id, candidate_ids):
        """Send rejection emails to candidates"""
        jd_data = self.db.get_job_description(jd_id)
        
        for candidate_id in candidate_ids:
            candidate_data = self.db.get_candidate(candidate_id)
            match_data = None  # In a real system, we would retrieve the match data
            
            # Generate email from template
            email = self.communicator.generate_rejection_email(
                jd_data, candidate_data, match_data
            )
            
            # In a real system, we would send the email here
            # For the hackathon, we'll just log it
            print(f"Rejection email sent to {candidate_data.get('Name', 'candidate')} ({candidate_id})")
    
    def process_feedback(self, match_id, feedback_text, rating):
        """Process feedback for a match"""
        self.db.insert_feedback(match_id, feedback_text, rating)
        self.feedback_learner.process_feedback(match_id, feedback_text, rating)
    
    def get_dashboard_data(self, jd_id, session_candidates=None):
        """Get dashboard data for a job description"""
        if session_candidates is not None:
            print(f"Using {len(session_candidates)} session-uploaded candidates for dashboard")
            return self.dashboard.generate_dashboard(jd_id, session_candidates)
        else:
            return self.dashboard.generate_dashboard(jd_id)
