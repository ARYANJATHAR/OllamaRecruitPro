# agents/communicator.py
import ollama
from datetime import datetime, timedelta

class CommunicatorAgent:
    def __init__(self, model_name, db):
        self.model_name = model_name
        self.db = db
    
    def generate_interview_request(self, jd_data, candidate_data, match_data):
        """
        Generate a personalized interview request email
        """
        # Extract relevant data
        job_title = jd_data.get('title', 'the position')
        company_name = jd_data.get('company', 'our company')
        candidate_name = candidate_data.get('name', 'Candidate')
        match_score = match_data.get('score', 0)
        match_justification = match_data.get('justification', '')
        
        # Generate interview dates (next week)
        today = datetime.now()
        interview_dates = [
            (today + timedelta(days=i+7)).strftime("%A, %B %d at %I:%M %p")
            for i in range(3)  # 3 options
        ]
        
        # Prepare prompt for Ollama
        prompt = f"""
        Generate a professional and personalized interview request email.
        
        Job Title: {job_title}
        Company: {company_name}
        Candidate Name: {candidate_name}
        Match Strength: {match_score:.2f} (on a scale of 0 to 1)
        
        Key matching points: {match_justification}
        
        Suggested interview times:
        {interview_dates[0]}
        {interview_dates[1]}
        {interview_dates[2]}
        
        The email should:
        1. Be professional and welcoming
        2. Mention why the candidate is a good fit
        3. Offer the interview times as options
        4. Request a response to confirm
        5. Thank the candidate for their application
        """
        
        # Call Ollama model
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Return the generated email
        return response["message"]["content"]
    
    def generate_rejection_email(self, jd_data, candidate_data, match_data):
        """
        Generate a personalized rejection email with constructive feedback
        """
        # Extract relevant data
        job_title = jd_data.get('title', 'the position')
        company_name = jd_data.get('company', 'our company')
        candidate_name = candidate_data.get('name', 'Candidate')
        match_justification = match_data.get('justification', '')
        
        # Prepare prompt for Ollama
        prompt = f"""
        Generate a professional, kind rejection email with constructive feedback.
        
        Job Title: {job_title}
        Company: {company_name}
        Candidate Name: {candidate_name}
        
        Matching analysis: {match_justification}
        
        The email should:
        1. Be professional and respectful
        2. Thank the candidate for their application
        3. Provide constructive feedback on where they didn't quite match
        4. Encourage them to apply for future positions if appropriate
        5. Wish them well in their job search
        """
        
        # Call Ollama model
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Return the generated email
        return response["message"]["content"]
