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
        jd_data = self.jd_parser.parse(jd_text)
        jd_id = self.db.insert_job_description(jd_data)
        return jd_id
    
    def process_cv(self, cv_text):
        """Process a CV and store it in the database"""
        cv_data = self.cv_parser.parse(cv_text)
        candidate_id = self.db.insert_candidate(cv_data)
        return candidate_id
    
    def match_candidates(self, jd_id):
        """Match candidates to a job description"""
        jd_data = self.db.get_job_description(jd_id)
        candidates = self.db.get_all_candidates()
        
        matches = []
        for candidate in candidates:
            match_score, justification = self.skill_matcher.match(jd_data, candidate)
            ranked_score = self.rank_score.calculate(match_score, jd_data, candidate)
            
            if ranked_score >= 0.8:  # 80% threshold for shortlisting
                matches.append({
                    'candidate_id': candidate['id'],
                    'score': ranked_score,
                    'justification': justification
                })
                
                # Store match in database
                self.db.insert_match(jd_id, candidate['id'], ranked_score, justification)
        
        return sorted(matches, key=lambda x: x['score'], reverse=True)
    
    def send_interview_requests(self, jd_id, match_ids):
        """Send interview requests to matched candidates"""
        jd_data = self.db.get_job_description(jd_id)
        
        for match_id in match_ids:
            match_data = self.db.get_match(match_id)
            candidate = self.db.get_candidate(match_data['candidate_id'])
            
            email_content = self.communicator.generate_interview_request(
                jd_data, candidate, match_data
            )
            
            # In a real system, this would send an email
            # For the hackathon, we'll simulate this
            print(f"Email sent to {candidate['email']}")
            print(email_content)
            
            self.db.update_match_status(match_id, "interview_requested")
    
    def get_dashboard_data(self, jd_id):
        """Get dashboard data for a job description"""
        return self.dashboard.generate_dashboard(jd_id)
    
    def incorporate_feedback(self, match_id, feedback):
        """Incorporate recruiter feedback to improve future matches"""
        self.feedback_learner.learn(match_id, feedback)
