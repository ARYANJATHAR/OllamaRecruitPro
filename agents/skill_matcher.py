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
        job_responsibilities = jd_data.get('responsibilities', [])
        job_title = jd_data.get('title', 'Job Position')
        company_name = jd_data.get('company', 'Company')
        # Convert required_experience to int or default to 0 if None or invalid
        try:
            required_experience = int(jd_data.get('required_experience', 0))
        except (ValueError, TypeError):
            required_experience = 0
        required_education = jd_data.get('required_education', '')
        
        # Get candidate data
        candidate_skills = candidate_data.get('Skills', [])
        candidate_name = candidate_data.get('Name', 'Candidate')
        candidate_id = candidate_data.get('Candidate_ID', candidate_data.get('id', 'Unknown ID'))
        candidate_experience = candidate_data.get('Experience', [])
        candidate_education = candidate_data.get('Education', [])
        candidate_certifications = candidate_data.get('Certifications', [])
        candidate_languages = candidate_data.get('Languages', [])
        candidate_summary = candidate_data.get('Summary', '')
        
        # Calculate direct skill matches
        direct_skill_matches = 0
        skill_match_details = []
        
        # Check direct matches for required skills
        for skill in required_skills:
            if any(self._skill_match(skill, candidate_skill) for candidate_skill in candidate_skills):
                direct_skill_matches += 1
                skill_match_details.append(f"✅ Required skill match: {skill}")
            else:
                skill_match_details.append(f"❌ Missing required skill: {skill}")
        
        # Check direct matches for preferred skills
        preferred_matches = 0
        for skill in preferred_skills:
            if any(self._skill_match(skill, candidate_skill) for candidate_skill in candidate_skills):
                preferred_matches += 1
                skill_match_details.append(f"✅ Preferred skill match: {skill}")
            else:
                skill_match_details.append(f"⚠️ Missing preferred skill: {skill}")
        
        # Calculate experience match
        experience_years = self._extract_experience_years(candidate_experience)
        # Handle experience matching with safe integer comparison
        if required_experience > 0:
            experience_match = min(1.0, experience_years / required_experience)
        else:
            experience_match = 1.0  # If no experience required, consider it a full match
        
        # Calculate education match
        education_match = self._calculate_education_match(candidate_education, required_education)
        
        # Combined skills match score - required skills are weighted more heavily
        required_skills_score = direct_skill_matches / max(1, len(required_skills))
        preferred_skills_score = preferred_matches / max(1, len(preferred_skills))
        
        # Weight calculations - prioritize required skills
        skills_weight = 0.5  # 50% for skills
        experience_weight = 0.3  # 30% for experience
        education_weight = 0.2  # 20% for education
        
        # Calculate weighted score
        weighted_score = (
            (required_skills_score * 0.7 + preferred_skills_score * 0.3) * skills_weight +
            experience_match * experience_weight +
            education_match * education_weight
        )
        
        # Format the score as a percentage
        score_percentage = weighted_score * 100
        
        prompt = f"""
        Analyze how well candidate {candidate_name} (ID: {candidate_id}) matches the job requirements for the position of {job_title} at {company_name}.
        
        JOB DETAILS:
        - Job Title: {job_title}
        - Company: {company_name}
        - Required Experience: {required_experience} years
        - Required Education: {required_education}
        - Required Skills: {required_skills}
        - Preferred Skills: {preferred_skills}
        - Job Responsibilities: {job_responsibilities}
        
        CANDIDATE DETAILS:
        - Name: {candidate_name}
        - ID: {candidate_id}
        - Skills: {candidate_skills}
        - Experience: {candidate_experience}
        - Education: {candidate_education}
        - Certifications: {candidate_certifications}
        - Languages: {candidate_languages}
        - Summary: {candidate_summary}
        
        PRELIMINARY ASSESSMENT:
        - Required Skills Match: {direct_skill_matches}/{len(required_skills)} ({required_skills_score*100:.1f}%)
        - Preferred Skills Match: {preferred_matches}/{len(preferred_skills)} ({preferred_skills_score*100:.1f}%)
        - Experience Match: {experience_years} years vs required {required_experience} years ({experience_match*100:.1f}%)
        - Education Match: {education_match*100:.1f}%
        - Overall Match Score (Preliminary): {score_percentage:.1f}%
        
        ANALYSIS REQUIREMENTS:
        1. Use ONLY the provided information about the candidate from the CANDIDATE DETAILS section.
        2. For each required skill, determine if the candidate has it or a closely related skill.
        3. For each preferred skill, do the same.
        4. Check if the candidate's experience matches or exceeds the required experience.
        5. Check if the candidate's education meets the required education level.
        6. Evaluate how well the candidate's experience aligns with the job responsibilities.
        7. Identify the candidate's key strengths relevant to this position.
        8. Identify any gaps or areas where the candidate doesn't meet requirements.
        9. DO NOT invent or assume details not present in the provided information.
        10. Be specific about why this candidate is or isn't a good match using only the provided information.
        
        FORMAT THE OUTPUT EXACTLY AS FOLLOWS:
        Match Score: {score_percentage:.1f}%
        Key Strengths: [3-5 key strengths relevant to this position]
        Skills Match: [analysis of required and preferred skills matches]
        Experience Match: [analysis of experience relevance and duration]
        Education Match: [analysis of education requirements]
        Gaps: [any identified gaps in requirements]
        Detailed Justification: [comprehensive explanation of why this candidate is or isn't a good fit]
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
        
        # Extract data from the response
        match_score = self._extract_match_score(result)
        key_strengths = self._extract_key_strengths(result)
        skills_match = self._extract_skills_match(result)
        
        # Extract experience and education match text sections, not the numeric values
        experience_match_text = self._extract_experience_match(result)
        education_match_text = self._extract_education_match(result)
        
        gaps = self._extract_gaps(result)
        justification = self._extract_justification(result)
        
        # Enhance matching with vector similarity for skills
        enhanced_score = self._enhance_with_embeddings(
            required_skills, candidate_skills, weighted_score
        )
        
        # Create comprehensive justification including all sections
        comprehensive_justification = f"""
        ## Match Analysis for {candidate_name} (ID: {candidate_id})

        **Overall Match Score: {enhanced_score:.0%}**

        ### Key Strengths:
        {key_strengths}

        ### Skills Match:
        {skills_match}
        
        #### Skill Match Details:
        {chr(10).join(skill_match_details)}

        ### Experience Match:
        {experience_match_text}
        
        #### Experience Details:
        - Estimated Years: {experience_years}
        - Required Years: {required_experience}
        - Match Rate: {experience_match*100:.1f}%

        ### Education Match:
        {education_match_text}
        
        #### Education Details:
        - Candidate Education: {chr(10).join(candidate_education)}
        - Required Education: {required_education}
        - Match Rate: {education_match*100:.1f}%
        
        ### Gaps:
        {gaps}

        ### Detailed Justification:
        {justification}
        """
        
        return enhanced_score, comprehensive_justification
    
    def _extract_match_score(self, result):
        """Extract match score from result text"""
        # Try percentage format (e.g., 85%)
        match = re.search(r'Match Score:\s*(\d+)%', result)
        if match:
            return int(match.group(1)) / 100
        
        # Try decimal format (e.g., 0.85)
        match = re.search(r'Match Score:\s*(0\.\d+)', result)
        if match:
            return float(match.group(1))
            
        # Try x/10 format
        match = re.search(r'Match Score:\s*(\d+(?:\.\d+)?)/10', result)
        if match:
            return float(match.group(1)) / 10
            
        return 0.5  # Default if parsing fails
    
    def _extract_key_strengths(self, result):
        """Extract key strengths from result text"""
        match = re.search(r'Key Strengths:\s*(.*?)(?=\n\w|\Z)', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No key strengths identified."
    
    def _extract_skills_match(self, result):
        """Extract skills match analysis from result text"""
        match = re.search(r'Skills Match:\s*(.*?)(?=\n\w|\Z)', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No skills match analysis provided."
    
    def _extract_experience_match(self, result):
        """Extract experience match analysis from result text"""
        match = re.search(r'Experience Match:\s*(.*?)(?=\n\w|\Z)', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No experience match analysis provided."
    
    def _extract_education_match(self, result):
        """Extract education match analysis from result text"""
        match = re.search(r'Education Match:\s*(.*?)(?=\n\w|\Z)', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No education match analysis provided."
    
    def _extract_gaps(self, result):
        """Extract gaps from result text"""
        match = re.search(r'Gaps:\s*(.*?)(?=\n\w|\Z)', result, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "No gaps identified."
    
    def _extract_justification(self, result):
        """Extract detailed justification from result text"""
        match = re.search(r'Detailed Justification:\s*(.*)', result, re.DOTALL)
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
    
    def _skill_match(self, required_skill, candidate_skill):
        """Check if skills match (case-insensitive)"""
        if not required_skill or not candidate_skill:
            return False
            
        # Direct match
        if required_skill.lower() == candidate_skill.lower():
            return True
            
        # Substring match
        if required_skill.lower() in candidate_skill.lower() or candidate_skill.lower() in required_skill.lower():
            return True
            
        # TODO: Add semantic matching via embeddings
        return False
        
    def _extract_experience_years(self, experience_entries):
        """
        Extract total years of experience from experience entries
        """
        if not experience_entries:
            return 0
            
        total_years = 0
        year_pattern = r'(\d+)(?:\s*-\s*\d+|\+)?\s*(?:year|yr)s?'
        
        for entry in experience_entries:
            if not isinstance(entry, str):
                continue
                
            # Look for explicit year mentions
            matches = re.findall(year_pattern, entry.lower())
            if matches:
                # Take the largest year number mentioned
                years = max(int(year) for year in matches)
                total_years = max(total_years, years)
                continue
            
            # Try to extract years from date ranges
            date_pattern = r'(\d{4})\s*(?:-|to)\s*(?:(\d{4})|present|current|now)'
            date_matches = re.findall(date_pattern, entry.lower())
            
            for date_match in date_matches:
                start_year = int(date_match[0])
                if date_match[1]:  # End year specified
                    end_year = int(date_match[1])
                else:  # Current/Present
                    from datetime import datetime
                    end_year = datetime.now().year
                    
                years = end_year - start_year
                if 0 <= years <= 50:  # Sanity check for reasonable range
                    total_years = max(total_years, years)
        
        return max(0, min(total_years, 50))  # Cap at 50 years for reasonableness
        
    def _calculate_education_match(self, education_entries, required_education):
        """Calculate education match score"""
        if not required_education:
            return 1.0  # Perfect match if no education required
            
        # Define education levels and their relative values
        education_levels = {
            "high school": 1,
            "diploma": 2,
            "associate": 3,
            "bachelor": 4,
            "master": 5,
            "phd": 6,
            "doctorate": 6
        }
        
        # Extract required education level
        required_level = 0
        for level, value in education_levels.items():
            if level in required_education.lower():
                required_level = value
                break
                
        # Find highest education level of candidate
        candidate_level = 0
        for entry in education_entries:
            for level, value in education_levels.items():
                if level in entry.lower():
                    candidate_level = max(candidate_level, value)
                    
        # Calculate match score
        if required_level == 0:
            return 1.0  # No specific level required
        if candidate_level >= required_level:
            return 1.0  # Meets or exceeds requirements
        else:
            return candidate_level / required_level  # Partial match
