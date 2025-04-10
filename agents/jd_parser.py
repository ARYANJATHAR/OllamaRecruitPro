# agents/jd_parser.py
import ollama
import re
import json
from memory.database import Database

class JDParserAgent:
    def __init__(self, model_name, db):
        self.model_name = model_name
        self.db = db
    
    def parse(self, jd_text):
        """
        Parse a job description to extract structured information
        """
        # Define the prompt for Ollama
        prompt = f"""
        Extract the following information from this job description and return it as JSON:
        1. Job Title
        2. Required Skills (must-have)
        3. Preferred Skills (nice-to-have)
        4. Required Experience (years)
        5. Required Education
        6. Job Responsibilities
        7. Company Name
        
        Format the output as a valid JSON object with these exact keys:
        {{
            "Job Title": "string",
            "Required Skills": ["skill1", "skill2"],
            "Preferred Skills": ["skill1", "skill2"],
            "Required Experience": number,
            "Required Education": "string",
            "Job Responsibilities": ["resp1", "resp2"],
            "Company Name": "string"
        }}
        
        Job Description:
        {jd_text}
        """
        
        # Call Ollama model
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract and clean the response
        result = response["message"]["content"]
        
        try:
            # Find JSON-like content in the string using regex
            json_match = re.search(r'(\{.*\})', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                parsed_data = json.loads(json_str)
            else:
                # Fallback structure if no JSON found
                parsed_data = {
                    "Job Title": "",
                    "Required Skills": [],
                    "Preferred Skills": [],
                    "Required Experience": 0,
                    "Required Education": "",
                    "Job Responsibilities": [],
                    "Company Name": ""
                }
                
            # Store in skill taxonomy
            extracted_skills = self._extract_skills(parsed_data)
            for skill in extracted_skills:
                self.db.insert_skill_if_not_exists(skill)
            
            return parsed_data
            
        except json.JSONDecodeError:
            # Return default structure if JSON parsing fails
            return {
                "Job Title": "",
                "Required Skills": [],
                "Preferred Skills": [],
                "Required Experience": 0,
                "Required Education": "",
                "Job Responsibilities": [],
                "Company Name": ""
            }
    
    def _extract_skills(self, parsed_jd):
        """Extract skills from parsed JD for the skill taxonomy"""
        skills = []
        
        # Extract skills from the parsed JD
        if isinstance(parsed_jd, dict):
            if 'Required Skills' in parsed_jd:
                skills.extend(parsed_jd['Required Skills'])
            if 'Preferred Skills' in parsed_jd:
                skills.extend(parsed_jd['Preferred Skills'])
        
        return skills
