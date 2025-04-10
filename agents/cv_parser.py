# agents/cv_parser.py
import ollama
import re
import json
from memory.database import Database

class CVParserAgent:
    def __init__(self, model_name, db):
        self.model_name = model_name
        self.db = db
    
    def parse(self, cv_text):
        """
        Parse a CV to extract structured information
        """
        # Define the prompt for Ollama
        prompt = f"""
        Extract the following information from this CV/resume:
        1. Name
        2. Email
        3. Phone
        4. Skills (as a list)
        5. Experience (as a list of jobs with company, title, period, and key responsibilities)
        6. Education (as a list of degrees with institution and year)
        
        Format the output as JSON.
        
        CV:
        {cv_text}
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
        
        # Try to parse JSON from the result
        try:
            # Find JSON-like content in the string using regex
            json_match = re.search(r'(\{.*\})', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                parsed_data = json.loads(json_str)
            else:
                # If no JSON found, create a simple structure
                parsed_data = {
                    "Name": self._extract_name(result),
                    "Email": self._extract_email(result),
                    "Phone": self._extract_phone(result),
                    "Skills": self._extract_skills(result),
                    "Experience": [],
                    "Education": []
                }
                
            # Store skills in the taxonomy
            for skill in parsed_data.get("Skills", []):
                self.db.insert_skill_if_not_exists(skill)
                
            return parsed_data
                
        except json.JSONDecodeError:
            # Fallback for non-JSON responses
            # Extract information using patterns
            parsed_data = {
                "Name": self._extract_name(result),
                "Email": self._extract_email(result),
                "Phone": self._extract_phone(result),
                "Skills": self._extract_skills(result),
                "Experience": [],
                "Education": []
            }
            
            # Store skills in the taxonomy
            for skill in parsed_data.get("Skills", []):
                self.db.insert_skill_if_not_exists(skill)
                
            return parsed_data
    
    def _extract_name(self, text):
        """Extract name from parsed CV text"""
        name_match = re.search(r'Name:\s*(.*)', text)
        if name_match:
            return name_match.group(1).strip()
        return ""
    
    def _extract_email(self, text):
        """Extract email from parsed CV text"""
        email_match = re.search(r'Email:\s*([\w\.-]+@[\w\.-]+)', text)
        if email_match:
            return email_match.group(1).strip()
        return ""
    
    def _extract_phone(self, text):
        """Extract phone from parsed CV text"""
        phone_match = re.search(r'Phone:\s*([0-9\(\)\s\-\+\.]+)', text)
        if phone_match:
            return phone_match.group(1).strip()
        return ""
    
    def _extract_skills(self, text):
        """Extract skills from parsed CV text"""
        skills = []
        skills_section = re.search(r'Skills:\s*(.*?)(?=\n\n|\Z)', text, re.DOTALL)
        if skills_section:
            skills_text = skills_section.group(1)
            # Extract skills as list items
            skill_items = re.findall(r'-\s*(.*?)(?=\n-|\n\n|\Z)', skills_text, re.DOTALL)
            if skill_items:
                skills = [item.strip() for item in skill_items]
            else:
                # Try comma-separated format
                skills = [item.strip() for item in skills_text.split(',') if item.strip()]
        return skills
