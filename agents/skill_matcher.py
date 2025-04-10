# agents/skill_matcher.py
import ollama
import re
from memory.vector_store import VectorStore

class SkillMatcherAgent:
    def __init__(self, model_name, vector_store):
        self.model_name = model_name
        self.vector_store = vector_store
    
    def match(self, jd_data, candidate_data):
        """
        Match candidate skills to job requirements
        """
        # Prepare prompts with context
        required_skills = jd_data.get('Required Skills', [])
        preferred_skills = jd_data.get('Preferred Skills', [])
        candidate_skills = candidate_data.get('Skills', [])
        
        prompt = f"""
        Analyze how well the candidate's skills match the job requirements.
        
        Job Required Skills: {required_skills}
        Job Preferred Skills: {preferred_skills}
        Candidate Skills: {candidate_skills}
        
        For each required skill, determine if the candidate has it or a closely related skill.
        For each preferred skill, do the same.
        Calculate an overall match percentage and provide justification.
        
        Format the output as:
        Match Score: [percentage]
        Justification: [detailed explanation of matches and gaps]
        """
        
        # Call Ollama model
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response to extract match score and justification
        result = response["message"]["content"]
        
        # Simple parsing - in a real system, we'd do more robust extraction
        match_score = self._extract_match_score(result)
        justification = self._extract_justification(result)
        
        # Enhance matching with vector similarity for skills
        enhanced_score = self._enhance_with_embeddings(
            required_skills, candidate_skills, match_score
        )
        
        return enhanced_score, justification
    
    def _extract_match_score(self, result):
        """Extract match score from result text"""
        # Simple regex to extract percentage
        match = re.search(r'Match Score: (\d+)%', result)
        if match:
            return int(match.group(1)) / 100
        return 0.5  # Default if parsing fails
    
    def _extract_justification(self, result):
        """Extract justification from result text"""
        match = re.search(r'Justification: (.*)', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No detailed justification provided."
    
    def _enhance_with_embeddings(self, required_skills, candidate_skills, base_score):
        """Enhance matching with vector similarity"""
        # This would use the vector store to find semantic similarities
        # between skills that might not match exactly in text
        
        # For hackathon purposes, this is simplified
        # In a real system, we'd do proper vector similarity
        
        # Just return the base score for now
        return base_score
