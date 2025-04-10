# agents/rank_score.py
import ollama
import re

class RankScoreAgent:
    def __init__(self, model_name, db):
        self.model_name = model_name
        self.db = db
    
    def calculate(self, base_match_score, jd_data, candidate_data):
        """
        Calculate a refined score based on additional factors beyond skills
        """
        # Extract relevant data
        required_experience = jd_data.get('required_experience', 0)
        required_education = jd_data.get('required_education', '')
        
        candidate_experience = self._calculate_total_experience(candidate_data.get('experience', []))
        candidate_education = self._get_highest_education(candidate_data.get('education', []))
        
        # Prepare prompt for Ollama
        prompt = f"""
        Analyze the candidate's fit for the job beyond skills matching.
        
        Job Required Experience: {required_experience} years
        Candidate Experience: {candidate_experience} years
        
        Job Required Education: {required_education}
        Candidate Education: {candidate_education}
        
        Current Skills Match Score: {base_match_score:.2f} (on a scale of 0 to 1)
        
        Based on the above factors, adjust the match score by considering:
        1. If the candidate exceeds the required experience, this is positive
        2. If the candidate meets the education requirements, this is positive
        3. If the candidate lacks required experience or education, this is negative
        
        Provide a final adjusted score between 0 and 1.
        Format the output as: Final Score: [score]
        """
        
        # Call Ollama model
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and process the response
        result = response["message"]["content"]
        
        # Extract the final score
        final_score = self._extract_final_score(result, base_match_score)
        
        return final_score
    
    def _calculate_total_experience(self, experience_list):
        """Calculate total years of experience from experience list"""
        # This is a simplified implementation
        # In a real system, we'd do more sophisticated calculation
        total_years = 0
        
        # Just a dummy calculation for hackathon purposes
        # In reality, we'd parse the experience periods properly
        total_years = len(experience_list) * 2  # Assuming 2 years per position
        
        return total_years
    
    def _get_highest_education(self, education_list):
        """Get the highest education level from education list"""
        # This is a simplified implementation
        # In a real system, we'd do more sophisticated analysis
        if not education_list:
            return "No formal education listed"
        
        # Just return the first education entry for hackathon purposes
        return str(education_list[0])
    
    def _extract_final_score(self, result, default_score):
        """Extract final score from result text"""
        # Try to extract the final score
        final_score_match = re.search(r'Final Score:\s*(0\.\d+|1\.0|1)', result)
        if final_score_match:
            try:
                return float(final_score_match.group(1))
            except ValueError:
                return default_score
        
        return default_score
