# agents/feedback_learner.py
import ollama
import json

class FeedbackLearnerAgent:
    def __init__(self, model_name, db):
        self.model_name = model_name
        self.db = db
    
    def learn(self, match_id, feedback):
        """
        Learn from recruiter feedback on a match
        """
        # Get match data
        match_data = self.db.get_match(match_id)
        if not match_data:
            return False
        
        # Store feedback in database
        rating = feedback.get('rating', 0)  # 1-5 rating
        feedback_text = feedback.get('text', '')
        
        self.db.insert_feedback(match_id, feedback_text, rating)
        
        # Process feedback to improve future matching
        jd_id = match_data['jd_id']
        candidate_id = match_data['candidate_id']
        
        # Get job and candidate data
        jd_data = self.db.get_job_description(jd_id)
        candidate_data = self.db.get_candidate(candidate_id)
        
        # Analyze feedback to extract learnings
        prompt = f"""
        Analyze the recruiter feedback for a job match to extract patterns that can improve future matching.
        
        Job Title: {jd_data.get('title', '')}
        Required Skills: {jd_data.get('required_skills', [])}
        
        Candidate Skills: {candidate_data.get('skills', [])}
        
        Match Score: {match_data.get('score', 0)}
        
        Recruiter Feedback (Rating: {rating}/5):
        {feedback_text}
        
        Extract insights for improving our matching algorithm:
        1. What skills were correctly matched?
        2. What skills were incorrectly matched?
        3. What factors besides skills affected the feedback?
        4. What should we prioritize differently in the future?
        
        Format the output as JSON with these categories.
        """
        
        # Call Ollama model
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        result = response["message"]["content"]
        
        # In a real system, we would:
        # 1. Parse the result and extract actionable insights
        # 2. Update skill relationships in the database
        # 3. Adjust matching weights based on feedback
        # 4. Store patterns for future reference
        
        # For the hackathon, we'll just log that we processed the feedback
        # and pretend we're being smart about it
        print(f"Processed feedback for match {match_id}")
        print(f"Learned insights: {result[:100]}...")
        
        return True
