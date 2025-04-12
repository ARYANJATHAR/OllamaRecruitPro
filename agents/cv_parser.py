# agents/cv_parser.py
import ollama
import re
import json
from memory.database import Database
import time

class CVParserAgent:
    def __init__(self, model_name, db):
        self.model_name = model_name
        self.db = db
    
    def parse(self, cv_text):
        """
        Parse a CV to extract structured information
        """
        try:
            # First try to parse the CV using direct pattern matching since we know the structure
            direct_parsed = self._direct_parse(cv_text)
            if direct_parsed and self._is_valid_parsed_data(direct_parsed):
                # Store skills in the taxonomy
                for skill in direct_parsed.get("Skills", []):
                    if skill:  # Check for non-empty skills
                        self.db.insert_skill_if_not_exists(skill)
                
                # Validate and ensure all required fields exist
                direct_parsed = self._ensure_valid_data_format(direct_parsed)
                return direct_parsed
            
            # If direct parsing doesn't yield good results, fallback to LLM-based parsing
            # Define the prompt for Ollama
            prompt = f'''
            Extract ONLY the following information from this CV/resume:
            1. Name (extract exactly as written in the CV)
            2. Email (extract the exact email address)
            3. Phone (extract the exact phone number)
            4. Candidate ID (extract any ID number mentioned, like 'ID: C1234')
            5. Skills (list all technical and soft skills mentioned)
            6. Experience (list all work experience with company, title, and period)
            7. Education (list all education with degree, institution, and years)
            8. Certifications (list all professional certifications)
            
            DO NOT generate or invent any information not explicitly mentioned in the CV.
            If information is not present, leave it blank or empty list.
            Format the output as clean JSON with these exact field names: "Name", "Email", "Phone", "Candidate_ID", "Skills", "Experience", "Education", "Certifications".
            
            CV:
            {cv_text}
            '''
            
            try:
                # Call Ollama model
                response = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Extract and clean the response
                result = response["message"]["content"]
                
            except Exception as e:
                print(f"Error calling Ollama model: {str(e)}")
                # Fall back to direct extraction
                parsed_data = {
                    "Name": self._extract_name(cv_text),
                    "Email": self._extract_email(cv_text),
                    "Phone": self._extract_phone(cv_text),
                    "Candidate_ID": self._extract_candidate_id(cv_text),
                    "Skills": self._extract_skills(cv_text),
                    "Experience": self._extract_experience(cv_text),
                    "Education": self._extract_education(cv_text),
                    "Certifications": self._extract_certifications(cv_text),
                    "Languages": self._extract_languages(cv_text),
                    "Summary": self._extract_summary(cv_text)
                }
                
                # Ensure data format is valid
                parsed_data = self._ensure_valid_data_format(parsed_data)
                
                # Store skills in the taxonomy
                for skill in parsed_data.get("Skills", []):
                    if skill:  # Check for non-empty skills
                        self.db.insert_skill_if_not_exists(skill)
                
                return parsed_data
            
            # Try to parse JSON from the result
            try:
                # Find JSON-like content in the string using regex
                json_match = re.search(r'(\{.*\})', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    parsed_data = json.loads(json_str)
                else:
                    # If no JSON found, create a structure based on direct extraction
                    parsed_data = {
                        "Name": self._extract_name(cv_text),
                        "Email": self._extract_email(cv_text),
                        "Phone": self._extract_phone(cv_text),
                        "Candidate_ID": self._extract_candidate_id(cv_text),
                        "Skills": self._extract_skills(cv_text),
                        "Experience": self._extract_experience(cv_text),
                        "Education": self._extract_education(cv_text),
                        "Certifications": self._extract_certifications(cv_text),
                        "Languages": self._extract_languages(cv_text),
                        "Summary": self._extract_summary(cv_text)
                    }
                    
                    # Ensure data format is valid
                    parsed_data = self._ensure_valid_data_format(parsed_data)
                
                # Store skills in the taxonomy
                for skill in parsed_data.get("Skills", []):
                    if skill:  # Check for non-empty skills
                        self.db.insert_skill_if_not_exists(skill)
                
                return parsed_data
                
            except json.JSONDecodeError:
                # Fallback for non-JSON responses - use direct extraction
                parsed_data = {
                    "Name": self._extract_name(cv_text),
                    "Email": self._extract_email(cv_text),
                    "Phone": self._extract_phone(cv_text),
                    "Candidate_ID": self._extract_candidate_id(cv_text),
                    "Skills": self._extract_skills(cv_text),
                    "Experience": self._extract_experience(cv_text),
                    "Education": self._extract_education(cv_text),
                    "Certifications": self._extract_certifications(cv_text),
                    "Languages": self._extract_languages(cv_text),
                    "Summary": self._extract_summary(cv_text)
                }
                
                # Ensure data format is valid
                parsed_data = self._ensure_valid_data_format(parsed_data)
                
                # Store skills in the taxonomy
                for skill in parsed_data.get("Skills", []):
                    if skill:  # Check for non-empty skills
                        self.db.insert_skill_if_not_exists(skill)
                
                return parsed_data
                
        except Exception as e:
            print(f"Error in CV parser: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return minimal valid data that won't cause errors
            return {
                "Name": "Unknown Candidate",
                "Email": "",
                "Phone": "",
                "Candidate_ID": f"C{int(time.time()) % 10000}",
                "Skills": [],
                "Experience": [],
                "Education": [],
                "Certifications": [],
                "Languages": [],
                "Summary": ""
            }
    
    def _direct_parse(self, cv_text):
        """Parse CV directly using regex patterns for known CV structure"""
        try:
            result = {}
            
            # Extract Candidate ID
            id_match = re.search(r'ID:\s*([A-Za-z0-9]+)', cv_text, re.IGNORECASE)
            if id_match:
                result["Candidate_ID"] = id_match.group(1).strip()
            else:
                # Try other ID patterns
                id_match = re.search(r'Candidate(?:\s+ID)?[:\s]+([A-Za-z]?\d+)', cv_text, re.IGNORECASE)
                if id_match:
                    candidate_id = id_match.group(1).strip()
                    if not candidate_id.startswith("C"):
                        candidate_id = "C" + candidate_id
                    result["Candidate_ID"] = candidate_id
            
            # Extract Name
            name_match = re.search(r'Name:\s*(.*?)(?=\n|\s*Email|\s*Phone|$)', cv_text, re.IGNORECASE)
            if name_match:
                result["Name"] = name_match.group(1).strip()
            
            # Extract Email
            email_match = re.search(r'Email:\s*([\w\.-]+@[\w\.-]+)', cv_text, re.IGNORECASE)
            if email_match:
                result["Email"] = email_match.group(1).strip()
            else:
                # Try to find email without the label
                email_match = re.search(r'([\w\.-]+@[\w\.-]+)', cv_text)
                if email_match:
                    result["Email"] = email_match.group(1).strip()
            
            # Extract Phone
            phone_match = re.search(r'Phone:\s*([0-9\(\)\s\-\+\.]+)', cv_text, re.IGNORECASE)
            if phone_match:
                result["Phone"] = phone_match.group(1).strip()
            else:
                # Try to find phone without the label
                phone_match = re.search(r'(?<!\w)(\+?[0-9]{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4})', cv_text)
                if phone_match:
                    result["Phone"] = phone_match.group(0).strip()
            
            # Extract Education
            edu_section = self._extract_section(cv_text, "Education", "Work Experience|Experience|Skills|Certifications|Achievements|Tech Stack")
            if edu_section:
                # Split education entries by pattern
                education_entries = []
                
                # Check for degree and year pattern
                degree_year_pattern = r'(?:Bachelor|Master|Diploma|PhD|BSc|MSc|B\.E\.|M\.E\.|B\.Tech|M\.Tech)[^(]*(?:\((\d{4}[-–]\d{4})\))'
                degrees = re.finditer(degree_year_pattern, edu_section, re.IGNORECASE)
                
                for degree_match in degrees:
                    degree_text = edu_section[degree_match.start():].split("\n\n")[0].strip()
                    if degree_text and len(degree_text) > 10:  # Avoid too short matches
                        education_entries.append(degree_text)
                
                # If no entries found with degree pattern, try by lines
                if not education_entries:
                    edu_lines = edu_section.split("\n")
                    for line in edu_lines:
                        if re.search(r'\b(20\d\d[-–]20\d\d|20\d\d)\b', line) and len(line) > 15:
                            education_entries.append(line.strip())
                
                if education_entries:
                    result["Education"] = education_entries
                else:
                    # Use the whole section if no specific entries found
                    result["Education"] = [edu_section.strip()] if edu_section.strip() else []
            else:
                result["Education"] = []
            
            # Extract Work Experience
            exp_section = self._extract_section(cv_text, "Work Experience|Experience", "Skills|Certifications|Achievements|Tech Stack")
            if exp_section:
                # Look for company/position patterns
                experience_entries = []
                
                # Pattern: Position at Company (YYYY-YYYY)
                position_pattern = r'([A-Za-z\s]+)\s+at\s+([A-Za-z0-9\s]+)\s*\((\d{4}[-–]\d{4}|\d{4}[-–]present|\d{4}[-–]Present)\)'
                positions = re.finditer(position_pattern, exp_section, re.IGNORECASE)
                
                for pos_match in positions:
                    pos_text = exp_section[pos_match.start():].split("\n\n")[0].strip()
                    if pos_text and len(pos_text) > 10:
                        experience_entries.append(pos_text)
                
                # If no entries found, try to split by years
                if not experience_entries:
                    exp_lines = exp_section.split("\n")
                    for i, line in enumerate(exp_lines):
                        if re.search(r'\b(20\d\d[-–]20\d\d|20\d\d[-–]present|20\d\d[-–]Present)\b', line) and len(line) > 15:
                            # Include description lines if available
                            if i+1 < len(exp_lines) and exp_lines[i+1].strip() and not re.search(r'\b20\d\d\b', exp_lines[i+1]):
                                experience_entries.append(f"{line.strip()} - {exp_lines[i+1].strip()}")
                            else:
                                experience_entries.append(line.strip())
                
                if experience_entries:
                    result["Experience"] = experience_entries
                else:
                    # Use the whole section if no specific entries found
                    result["Experience"] = [exp_section.strip()] if exp_section.strip() else []
            else:
                result["Experience"] = []
            
            # Extract Skills
            skills_section = self._extract_section(cv_text, "Skills", "Certifications|Achievements|Tech Stack|Languages")
            tech_stack_section = self._extract_section(cv_text, "Tech Stack", "$")
            
            skills = []
            
            # Process Skills section
            if skills_section:
                # Try different patterns to extract skills
                
                # Pattern 1: Skills with descriptions (Skill - Description)
                skill_desc_pattern = re.findall(r'([A-Za-z0-9 ]+)\s*-\s*([^\n]+)', skills_section)
                if skill_desc_pattern:
                    for skill, _ in skill_desc_pattern:
                        skills.append(skill.strip())
                
                # Pattern 2: List with bullet points
                if not skills:
                    skill_bullets = re.findall(r'(?:^|\n)\s*[-•]\s*([^\n]+)', skills_section)
                    skills.extend([s.strip() for s in skill_bullets])
                
                # Pattern 3: Comma separated list
                if not skills:
                    skill_list = re.split(r',\s*', skills_section)
                    skills.extend([s.strip() for s in skill_list if s.strip()])
                
                # Pattern 4: Line by line
                if not skills:
                    skill_lines = re.split(r'\n\s*[-•]?\s*', skills_section)
                    for line in skill_lines:
                        line = line.strip()
                        if not line or len(line) < 3:
                            continue
                            
                        if " - " in line:
                            # For pattern "Skill - Description"
                            skill_parts = line.split(" - ", 1)
                            skill = skill_parts[0].strip()
                            if skill and len(skill) > 2:
                                skills.append(skill)
                        else:
                            # Complete line as a skill
                            skills.append(line)
            
            # Process Tech Stack section
            if tech_stack_section:
                if "," in tech_stack_section:
                    tech_skills = re.split(r',\s*', tech_stack_section)
                else:
                    tech_skills = re.split(r'\s+', tech_stack_section)
                
                skills.extend([s.strip() for s in tech_skills if s.strip() and len(s.strip()) > 2])
            
            # Clean and deduplicate skills
            skills = [s for s in skills if s and not s.lower().startswith(("skill", "tech stack"))]
            skills = list(set(skills))  # Remove duplicates
            
            result["Skills"] = skills
            
            # Extract Certifications
            cert_section = self._extract_section(cv_text, "Certifications", "Achievements|Tech Stack|Languages")
            if cert_section:
                certifications = []
                
                # Pattern 1: Certifications with dash/hyphen
                cert_entries = re.findall(r'([^.\n]+\s+-\s+[^.\n]+\.?(?:\n|$)(?:[^.\n]+\.(?:\n|$))?)', cert_section)
                if cert_entries:
                    certifications.extend([entry.strip() for entry in cert_entries if entry.strip()])
                else:
                    # Pattern 2: Line by line
                    cert_lines = cert_section.split("\n")
                    for line in cert_lines:
                        line = line.strip()
                        if line and not line.lower().startswith("certification"):
                            certifications.append(line)
                
                result["Certifications"] = certifications
            else:
                    result["Certifications"] = []
            
            # Extract Languages
            lang_section = self._extract_section(cv_text, "Languages", "Achievements|Tech Stack")
            if lang_section:
                languages = []
                
                if "," in lang_section:
                    lang_parts = re.split(r',\s*', lang_section)
                    languages.extend([l.strip() for l in lang_parts if l.strip()])
                else:
                    lang_lines = lang_section.split("\n")
                    for line in lang_lines:
                        line = line.strip()
                        if line and not line.lower().startswith("language"):
                            languages.append(line)
                
                result["Languages"] = languages
            else:
                result["Languages"] = []
            
            # Extract Achievements
            achievement_section = self._extract_section(cv_text, "Achievements", "$")
            if achievement_section:
                achievements = []
                
                achievement_lines = achievement_section.split("\n")
                for line in achievement_lines:
                    line = line.strip()
                    if line and not line.lower().startswith("achievement") and len(line) > 10:
                        achievements.append(line)
                
                result["Achievements"] = achievements
            else:
                result["Achievements"] = []
            
            # Ensure all required fields exist
            for field in ["Name", "Email", "Phone", "Candidate_ID", "Skills", "Experience", "Education", "Certifications", "Languages", "Achievements"]:
                if field not in result:
                    if field in ["Skills", "Experience", "Education", "Certifications", "Languages", "Achievements"]:
                        result[field] = []
                    else:
                        result[field] = ""
            
            return result
        except Exception as e:
            print(f"Error in direct parsing: {str(e)}")
            return None
    
    def _extract_section(self, text, section_name, next_sections):
        """Extract a section from the CV text"""
        if "|" in section_name:
            for name in section_name.split("|"):
                pattern = fr'{name}\s*:?\s*(.*?)(?:(?:{next_sections})\s*:|\s*$)'
                section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if section_match:
                    return section_match.group(1).strip()
            return ""
        else:
            pattern = fr'{section_name}\s*:?\s*(.*?)(?:(?:{next_sections})\s*:|\s*$)'
        section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if section_match:
            return section_match.group(1).strip()
        return ""
    
    def _is_valid_parsed_data(self, data):
        """Check if the parsed data is valid"""
        # Must have at least name and one other field with content
        if not data.get("Name"):
            return False
        
        other_fields = ["Email", "Phone", "Skills", "Experience", "Education"]
        has_other_content = any(bool(data.get(field)) for field in other_fields)
        
        return has_other_content
    
    def _extract_name(self, text):
        """Extract name from parsed CV text"""
        name_match = re.search(r'Name:\s*(.*?)(?=\n|$)', text, re.IGNORECASE)
        if name_match:
            return name_match.group(1).strip()
        return ""
    
    def _extract_email(self, text):
        """Extract email from parsed CV text"""
        email_match = re.search(r'Email:\s*([\w\.-]+@[\w\.-]+)', text, re.IGNORECASE)
        if email_match:
            return email_match.group(1).strip()
        # Try to find email without the label
        email_match = re.search(r'([\w\.-]+@[\w\.-]+)', text)
        if email_match:
            return email_match.group(1).strip()
        return ""
    
    def _extract_phone(self, text):
        """Extract phone from parsed CV text"""
        phone_match = re.search(r'Phone:\s*([0-9\(\)\s\-\+\.]+)', text, re.IGNORECASE)
        if phone_match:
            return phone_match.group(1).strip()
        # Try to find phone without the label
        phone_match = re.search(r'(?<!\w)(\+?[0-9]{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4})', text)
        if phone_match:
            return phone_match.group(0).strip()
        return ""
    
    def _extract_candidate_id(self, text):
        """Extract candidate ID from parsed CV text or generate one"""
        id_match = re.search(r'(?:Candidate|ID):\s*([A-Za-z][A-Za-z0-9]*\d+)', text, re.IGNORECASE)
        if id_match:
            return id_match.group(1).strip()
        
        # Look for ID in the format (ID: C1234)
        id_match = re.search(r'\(ID:\s*([A-Za-z][A-Za-z0-9]*\d+)\)', text, re.IGNORECASE)
        if id_match:
            return id_match.group(1).strip()
        
        # If no ID found, generate one based on name and first 3 chars of email
        name = self._extract_name(text)
        email = self._extract_email(text)
        if name and email:
            name_part = name.split()[0].lower() if ' ' in name else name.lower()
            email_part = email[:3].lower() if len(email) >= 3 else email.lower()
            return f"{name_part}_{email_part}"
        return "candidate_unknown"
    
    def _extract_skills(self, text):
        """Extract skills from parsed CV text"""
        skills = []
        
        # Try to find a Skills section
        skills_section = re.search(r'Skills\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if skills_section:
            skills_text = skills_section.group(1)
            
            # Try different patterns to extract skills
            
            # Pattern 1: Skills with descriptions (Skill - Description)
            skill_desc_pattern = re.findall(r'([A-Za-z0-9 ]+)\s*-\s*([^\n]+)', skills_text)
            if skill_desc_pattern:
                for skill, _ in skill_desc_pattern:
                    skills.append(skill.strip())
            
            # Pattern 2: List with bullet points
            if not skills:
                skill_bullets = re.findall(r'(?:^|\n)\s*[-•]\s*([^\n]+)', skills_text)
                skills.extend([s.strip() for s in skill_bullets])
            
            # Pattern 3: Comma separated list
            if not skills:
                skill_list = re.split(r',\s*', skills_text)
                skills.extend([s.strip() for s in skill_list if s.strip()])
            
            # Pattern 4: Line by line
            if not skills:
                skill_lines = re.split(r'\n\s*[-•]?\s*', skills_text)
                for line in skill_lines:
                    line = line.strip()
                    if not line or len(line) < 3:
                        continue
                        
                    if " - " in line:
                        # For pattern "Skill - Description"
                        skill_parts = line.split(" - ", 1)
                        skill = skill_parts[0].strip()
                        if skill and len(skill) > 2:
                            skills.append(skill)
                    else:
                        # Complete line as a skill
                        skills.append(line)
        
        # Check for Tech Stack section
        tech_stack = re.search(r'Tech\s+Stack\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if tech_stack:
            tech_text = tech_stack.group(1)
            tech_items = re.split(r',\s*|\n', tech_text)
            skills.extend([t.strip() for t in tech_items if t.strip()])
        
        return [s for s in skills if s]
    
    def _extract_experience(self, text):
        """Extract experience from parsed CV text"""
        experience = []
        
        # Try to find Work Experience section
        exp_section = re.search(r'(?:Work\s*Experience|Experience)\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if exp_section:
            exp_text = exp_section.group(1)
            
            # Try different patterns to extract experience entries
            
            # Pattern 1: Job title at Company (period)
            job_entries = re.findall(r'([^.\n]+\s+at\s+[^.\n]+(?:\([^)]+\))?[^.\n]*\.?(?:\n|$)(?:[^.\n]+\.(?:\n|$))?)', exp_text, re.DOTALL)
            if job_entries:
                experience.extend([entry.strip() for entry in job_entries if entry.strip()])
            
            # Pattern 2: Job entries separated by blank lines
            if not experience:
                job_blocks = re.split(r'\n\s*\n', exp_text)
                experience.extend([block.strip() for block in job_blocks if block.strip()])
            
            # Pattern 3: Job entries starting with company or title
            if not experience:
                job_lines = re.findall(r'(?:^|\n)([A-Z][^.\n]+(?:Ltd|Inc|Corp|Company|Engineer|Developer|Manager)[^.\n]*)', exp_text)
                if job_lines:
                    current_entry = ""
                    for line in exp_text.split('\n'):
                        line = line.strip()
                        if any(job in line for job in job_lines):
                            if current_entry:
                                experience.append(current_entry)
                            current_entry = line
                        elif line and current_entry:
                            current_entry += " " + line
                    if current_entry:
                        experience.append(current_entry)
        
        return experience
    
    def _extract_education(self, text):
        """Extract education from parsed CV text"""
        education = []
        
        # Try to find Education section
        edu_section = re.search(r'Education\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if edu_section:
            edu_text = edu_section.group(1)
            
            # Pattern 1: Degree (period) - multi-line entries
            degree_entries = re.findall(r'([^.\n]+(?:\([^)]+\)|20\d\d-20\d\d)[^.\n]*\.?(?:\n|$)(?:[^.\n]+\.(?:\n|$))?)', edu_text, re.DOTALL)
            if degree_entries:
                for entry in degree_entries:
                    entry = entry.strip()
                    if entry:
                        education.append(entry)
            
            # Pattern 2: Simple line by line if no structured entries found
            if not education:
                edu_lines = [line.strip() for line in edu_text.split('\n') if line.strip()]
                edu_groups = []
                current_group = []
                
                for line in edu_lines:
                    # If this line looks like a degree title (has year or Bachelor/Master/PhD)
                    if re.search(r'(Bachelor|Master|PhD|Diploma|Degree|20\d\d)', line):
                        if current_group:
                            edu_groups.append(' '.join(current_group))
                            current_group = []
                        current_group.append(line)
                    elif current_group:
                        current_group.append(line)
                    else:
                        current_group.append(line)
                
                if current_group:
                    edu_groups.append(' '.join(current_group))
                
                education.extend(edu_groups)
        
        return education
    
    def _extract_certifications(self, text):
        """Extract certifications from parsed CV text"""
        certifications = []
        
        # Try to find Certifications section
        cert_section = re.search(r'Certifications?\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if cert_section:
            cert_text = cert_section.group(1)
            
            # Pattern 1: Certification - Description format
            cert_entries = re.findall(r'([^-\n]+)\s*-\s*([^\n]+)', cert_text)
            if cert_entries:
                certifications.extend([cert.strip() for cert, _ in cert_entries])
            
            # Pattern 2: Simple line by line if no structured entries found
            if not certifications:
                cert_lines = [line.strip() for line in cert_text.split('\n') if line.strip()]
                certifications.extend(cert_lines)
        
        return certifications
    
    def _extract_languages(self, text):
        """Extract languages from parsed CV text"""
        languages = []
        
        # Try to find Languages section
        lang_section = re.search(r'Languages?\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if lang_section:
            lang_text = lang_section.group(1)
            
            # Try to split by commas first
            lang_entries = [lang.strip() for lang in lang_text.split(',') if lang.strip()]
            if lang_entries:
                languages.extend(lang_entries)
            else:
                # Try line by line
                lang_lines = [line.strip() for line in lang_text.split('\n') if line.strip()]
                languages.extend(lang_lines)
        
        return languages
    
    def _extract_summary(self, text):
        """Extract summary from parsed CV text"""
        # Try to find Summary or Profile section
        summary_match = re.search(r'(?:Summary|Profile|About Me|Professional Summary)\s*:?\s*(.*?)(?=\n\n\w|\n[A-Z][a-z]+|\Z)', text, re.DOTALL | re.IGNORECASE)
        if summary_match:
            return summary_match.group(1).strip()
        
        # Try to find the first paragraph after the header info
        first_para = re.search(r'(?:Name|Email|Phone|ID).*?\n\n(.*?)(?=\n\n)', text, re.DOTALL)
        if first_para:
            return first_para.group(1).strip()
        
        return ""

    def _ensure_valid_data_format(self, data):
        """Ensure the data has all required fields and valid formats"""
        if not data or not isinstance(data, dict):
            # Return a completely fresh object if data is invalid
            return {
                "Name": "Unknown Candidate",
                "Email": "",
                "Phone": "",
                "Candidate_ID": f"C{int(time.time()) % 10000}",
                "Skills": [],
                "Experience": [],
                "Education": [],
                "Certifications": [],
                "Languages": [],
                "Summary": ""
            }
        
        # Add missing fields with defaults
        required_fields = {
            "Name": "Unknown Candidate",
            "Email": "",
            "Phone": "",
            "Candidate_ID": f"C{int(time.time()) % 10000}",
            "Skills": [],
            "Experience": [],
            "Education": [],
            "Certifications": [],
            "Languages": [],
            "Summary": ""
        }
        
        # Create a new data dictionary to avoid modifying the original one
        cleaned_data = {}
        
        # Process each field with proper validation
        for field, default in required_fields.items():
            # Get value, handle undefined
            value = data.get(field)
            
            # String fields
            if field in ["Name", "Email", "Phone", "Candidate_ID", "Summary"]:
                if value is None or value == "None" or value == "undefined" or not isinstance(value, str):
                    cleaned_data[field] = default
                else:
                    cleaned_data[field] = value
            
            # List fields
            elif field in ["Skills", "Experience", "Education", "Certifications", "Languages"]:
                # Handle various error cases
                if value is None or value == "None" or value == "undefined":
                    cleaned_data[field] = default
                elif isinstance(value, str):
                    # Try to parse if it's a JSON string
                    if value.startswith('[') and value.endswith(']'):
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                cleaned_data[field] = parsed
                            else:
                                cleaned_data[field] = [value]
                        except:
                            cleaned_data[field] = [value]
                    else:
                        cleaned_data[field] = [value]
                elif isinstance(value, list):
                    # Filter out any invalid items
                    valid_items = []
                    for item in value:
                        if item is None or item == "None" or item == "undefined" or item == "":
                            continue
                        if isinstance(item, str):
                            valid_items.append(item)
                        else:
                            try:
                                valid_items.append(str(item))
                            except:
                                pass
                    cleaned_data[field] = valid_items
                else:
                    # Any other type, try to make it a list
                    try:
                        cleaned_data[field] = [str(value)]
                    except:
                        cleaned_data[field] = []
        
        # Special handling for Candidate_ID - ensure it starts with C and is valid
        if not cleaned_data["Candidate_ID"] or cleaned_data["Candidate_ID"] == "undefined":
            cleaned_data["Candidate_ID"] = f"C{int(time.time()) % 10000}"
        elif not cleaned_data["Candidate_ID"].startswith("C"):
            cleaned_data["Candidate_ID"] = "C" + cleaned_data["Candidate_ID"]
        
        # Extra safety: ensure Skills is a list (this is often the problem field)
        if not isinstance(cleaned_data["Skills"], list):
            cleaned_data["Skills"] = []
        
        # Copy any Achievements field if it exists
        if "Achievements" in data and data["Achievements"]:
            if isinstance(data["Achievements"], list):
                cleaned_data["Achievements"] = [item for item in data["Achievements"] 
                                              if item and item != "undefined" and item != "None"]
            elif isinstance(data["Achievements"], str) and data["Achievements"] != "undefined":
                cleaned_data["Achievements"] = [data["Achievements"]]
            else:
                cleaned_data["Achievements"] = []
        
        return cleaned_data
