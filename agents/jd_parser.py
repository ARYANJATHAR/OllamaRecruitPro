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
        try:
            print("Starting job description parsing...")
            # Initialize default structure matching database schema
            parsed_data = {
                "title": "",
                "company": "",
                "required_skills": [],
                "preferred_skills": [],
                "required_experience": 0,
                "required_education": "",
                "responsibilities": []
            }
            
            # Handle JSON input
            if jd_text.strip().startswith('{') and jd_text.strip().endswith('}'):
                try:
                    json_data = json.loads(jd_text)
                    print("Detected and parsed JSON format job description")
                    
                    # Map common JSON keys to our schema
                    if 'title' in json_data:
                        parsed_data['title'] = json_data['title']
                    elif 'position' in json_data:
                        parsed_data['title'] = json_data['position']
                    elif 'job_title' in json_data:
                        parsed_data['title'] = json_data['job_title']
                        
                    if 'company' in json_data:
                        parsed_data['company'] = json_data['company']
                    elif 'company_name' in json_data:
                        parsed_data['company'] = json_data['company_name']
                        
                    # Handle various ways skills might be represented
                    if 'required_skills' in json_data:
                        parsed_data['required_skills'] = json_data['required_skills']
                    elif 'skills' in json_data:
                        parsed_data['required_skills'] = json_data['skills']
                    elif 'requirements' in json_data:
                        parsed_data['required_skills'] = json_data['requirements']
                        
                    if 'preferred_skills' in json_data:
                        parsed_data['preferred_skills'] = json_data['preferred_skills']
                    elif 'preferred' in json_data:
                        parsed_data['preferred_skills'] = json_data['preferred']
                        
                    if 'required_experience' in json_data:
                        parsed_data['required_experience'] = json_data['required_experience']
                    elif 'experience' in json_data:
                        parsed_data['required_experience'] = json_data['experience']
                        
                    if 'required_education' in json_data:
                        parsed_data['required_education'] = json_data['required_education']
                    elif 'education' in json_data:
                        parsed_data['required_education'] = json_data['education']
                        
                    if 'responsibilities' in json_data:
                        parsed_data['responsibilities'] = json_data['responsibilities']
                    elif 'duties' in json_data:
                        parsed_data['responsibilities'] = json_data['duties']
                        
                    # Clean the parsed data
                    return self._clean_parsed_data(parsed_data)
                except json.JSONDecodeError:
                    print("Failed to parse as JSON despite the format appearing to be JSON")
                    # Continue with other parsing methods
            
            # Check if this is CSV content
            if ',' in jd_text and (jd_text.startswith("Job Title") or 
                                  jd_text.startswith("Title") or
                                  jd_text.startswith("Position")):
                print("Detected potential CSV format")
                # Split the CSV content into lines
                lines = jd_text.strip().split('\n')
                if len(lines) >= 2:  # At least header + content
                    # Try to parse CSV
                    try:
                        header = lines[0].split(',')
                        
                        # Find the line with actual content (skip empty lines)
                        content_line = None
                        for line in lines[1:]:
                            if line.strip():
                                # Need to handle the case where commas exist within quoted fields
                                content_fields = []
                                in_quotes = False
                                current_field = ""
                                
                                for char in line:
                                    if char == '"':
                                        in_quotes = not in_quotes
                                        current_field += char
                                    elif char == ',' and not in_quotes:
                                        content_fields.append(current_field)
                                        current_field = ""
                                    else:
                                        current_field += char
                                        
                                # Add the last field
                                if current_field:
                                    content_fields.append(current_field)
                                    
                                content = content_fields
                                content_line = line
                                break
                        
                        if not content_line:
                            print("No content line found in CSV")
                            return parsed_data
                            
                        # Process fields
                        for i, field in enumerate(header):
                            if i < len(content):
                                field_clean = field.strip().lower()
                                field_value = content[i].strip().strip('"')
                                
                                if "title" in field_clean:
                                    parsed_data["title"] = field_value
                                elif "company" in field_clean:
                                    parsed_data["company"] = field_value
                                elif "description" in field_clean:
                                    # Store full description for display
                                    parsed_data["description"] = field_value
                                    
                                    # Process the description to extract more information
                                    sections = self._extract_sections(field_value)
                                    
                                    # Get responsibilities
                                    if "Responsibilities" in sections:
                                        resp_text = sections["Responsibilities"].strip()
                                        # First try to split by bullet points or newlines with dashes
                                        resp_items = re.split(r'\n\s*[-•]\s*|\n\s*\d+\.\s*', resp_text)
                                        if len(resp_items) <= 1:  # If no structured bullets found
                                            resp_items = resp_text.split('\n')
                                        
                                        responsibilities = [r.strip() for r in resp_items if r.strip()]
                                        parsed_data["responsibilities"] = responsibilities
                                    
                                    # Get skills from qualifications
                                    if "Qualifications" in sections:
                                        qual_text = sections["Qualifications"].strip()
                                        # First try to split by bullet points or newlines with dashes
                                        qual_items = re.split(r'\n\s*[-•]\s*|\n\s*\d+\.\s*', qual_text)
                                        if len(qual_items) <= 1:  # If no structured bullets found
                                            qual_items = qual_text.split('\n')
                                        
                                        qualifications = [q.strip() for q in qual_items if q.strip()]
                                        parsed_data["required_skills"] = qualifications
                                        
                                    # Try to extract education requirement
                                    for section_name, section_text in sections.items():
                                        if any(edu in section_text.lower() for edu in ["degree", "bachelor", "master", "phd", "education"]):
                                            education_lines = [line for line in section_text.split('\n') 
                                                              if any(edu in line.lower() for edu in ["degree", "bachelor", "master", "phd", "education"])]
                                            if education_lines:
                                                parsed_data["required_education"] = education_lines[0].strip()
                                                break
                                                
                                elif "skills" in field_clean:
                                    skills_text = field_value
                                    skills = [s.strip() for s in skills_text.split(';') if s.strip()]
                                    if skills:
                                        if "required" in field_clean:
                                            parsed_data["required_skills"] = skills
                                        elif "preferred" in field_clean:
                                            parsed_data["preferred_skills"] = skills
                                        else:
                                            parsed_data["required_skills"] = skills
                                            
                                elif "experience" in field_clean:
                                    exp_text = field_value
                                    # Try to extract number
                                    match = re.search(r'(\d+)', exp_text)
                                    if match:
                                        parsed_data["required_experience"] = int(match.group(1))
                                    else:
                                        parsed_data["required_experience"] = exp_text
                                        
                                elif "education" in field_clean:
                                    parsed_data["required_education"] = field_value
                                    
                                # Store the full description for display purposes
                                parsed_data["description"] = content_line
                    except Exception as csv_error:
                        print(f"Error parsing CSV format: {str(csv_error)}")
                        import traceback
                        traceback.print_exc()
            
            # If we haven't found any structured data yet, try analyzing as plain text
            if not parsed_data["title"] and not parsed_data["required_skills"]:
                print("Attempting to parse plain text job description")
                # Try to find a title at the beginning of text
                title_match = re.search(r'^(.*?)\n', jd_text)
                if title_match:
                    parsed_data["title"] = title_match.group(1).strip()
                
                # Try to find common section headers and extract skills
                skills_section = re.search(r'(?:Required Skills|Skills Required|Qualifications|Requirements)[\s:]+(.+?)(?:\n\n|\Z)', 
                                          jd_text, re.DOTALL | re.IGNORECASE)
                if skills_section:
                    skills_text = skills_section.group(1)
                    # Split by common list markers
                    skills = re.split(r'[•\-*]\s*|\d+\.\s*', skills_text)
                    # Clean up and remove empty items
                    parsed_data["required_skills"] = [s.strip() for s in skills if s.strip()]
                
                # Try to find experience requirements
                exp_match = re.search(r'(\d+)[\+]?\s*(?:years?|yrs)[\s\w]*experience', jd_text, re.IGNORECASE)
                if exp_match:
                    parsed_data["required_experience"] = int(exp_match.group(1))
                
                # Try to find education requirements
                edu_match = re.search(r'(?:Bachelor|Master|PhD|Degree|Diploma)[\s\w]*(?:in|of)[\s\w]+', 
                                     jd_text, re.IGNORECASE)
                if edu_match:
                    parsed_data["required_education"] = edu_match.group(0).strip()
            
            # Ensure we have non-empty data
            if not parsed_data["title"]:
                parsed_data["title"] = "Untitled Position"
                
            if not parsed_data["required_skills"]:
                # Try to extract any potential skills by looking for technical terms
                skill_terms = ["python", "javascript", "java", "c\\+\\+", "sql", "database", 
                              "react", "angular", "api", "aws", "cloud", "docker", "kubernetes",
                              "machine learning", "ai", "data"]
                for term in skill_terms:
                    if re.search(r'\b' + term + r'\b', jd_text, re.IGNORECASE):
                        parsed_data["required_skills"].append(term.replace("\\", ""))
            
            # Clean the data before returning
            cleaned_data = self._clean_parsed_data(parsed_data)
            print(f"Parsed job description with title: {cleaned_data.get('title', 'Unknown')}")
            return cleaned_data
            
        except Exception as e:
            print(f"Error parsing job description: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return a minimal valid structure
            return {
                "title": "Untitled Position",
                "company": "Unknown Company",
                "required_skills": [],
                "preferred_skills": [],
                "required_experience": 0,
                "required_education": "",
                "responsibilities": []
            }
    
    def _extract_sections(self, text):
        """Extract different sections from the job description text"""
        sections = {}
        
        # Define the sections we want to extract
        section_markers = [
            "Description:", 
            "Responsibilities:", 
            "Qualifications:", 
            "Requirements:", 
            "Skills Required:",
            "Preferred Skills:",
            "Education Requirements:",
            "Experience Requirements:"
        ]
        
        # Handle job descriptions with no explicit section markers
        if not any(marker in text for marker in section_markers):
            # Try to infer sections based on line breaks and content
            lines = text.split('\n')
            current_section = "Description"
            sections[current_section] = ""
            
            for line in lines:
                clean_line = line.strip()
                # Skip empty lines
                if not clean_line:
                    continue
                    
                # Check if this line might be a section header
                if (clean_line.endswith(':') and 
                    len(clean_line) < 30 and 
                    clean_line[0].isupper()):
                    current_section = clean_line.rstrip(':')
                    sections[current_section] = ""
                else:
                    # Append to current section
                    sections[current_section] += line + '\n'
            
            # Clean up sections
            for section, content in sections.items():
                sections[section] = content.strip()
                
            return sections
        
        # Find the positions of each section
        positions = []
        for marker in section_markers:
            pos = text.find(marker)
            if pos != -1:
                positions.append((pos, marker))
        
        # Sort positions by their location in the text
        positions.sort()
        
        # Extract each section
        for i, (pos, marker) in enumerate(positions):
            section_name = marker.replace(":", "")
            start = pos + len(marker)
            if i < len(positions) - 1:
                end = positions[i + 1][0]
                section_text = text[start:end]
            else:
                section_text = text[start:]
            
            # Clean up the section text
            section_text = section_text.strip()
            sections[section_name] = section_text
        
        # If no Responsibilities section was found but we have text before any section markers
        if "Responsibilities" not in sections and positions:
            first_marker_pos = positions[0][0]
            if first_marker_pos > 0:
                # Text before first section might be description
                sections["Description"] = text[:first_marker_pos].strip()
        
        return sections

    def _clean_parsed_data(self, data):
        """Clean and validate parsed job description data"""
        # Define expected keys and their default values
        expected_keys = {
            "title": "",
            "required_skills": [],
            "preferred_skills": [],
            "required_experience": 0,
            "required_education": "",
            "responsibilities": [],
            "company": ""
        }
        
        # Initialize cleaned data with default values
        cleaned = expected_keys.copy()
        
        # Map old keys to new keys
        key_mapping = {
            "Job Title": "title",
            "Required Skills": "required_skills",
            "Preferred Skills": "preferred_skills",
            "Required Experience": "required_experience",
            "Required Education": "required_education",
            "Job Responsibilities": "responsibilities",
            "Company Name": "company"
        }
        
        # Process each field
        for old_key, new_key in key_mapping.items():
            # Try both old and new key names
            value = data.get(old_key, data.get(new_key, expected_keys[new_key]))
            
            # Clean and validate based on field type
            if new_key in ["required_skills", "preferred_skills", "responsibilities"]:
                # Ensure lists contain strings and are not empty
                if isinstance(value, str):
                    value = [value] if value else []
                elif not isinstance(value, list):
                    value = []
                # Clean each item in the list
                value = [str(item).strip() for item in value if item and str(item).strip()]
                
            elif new_key == "required_experience":
                # Convert to integer, handle various formats
                try:
                    if isinstance(value, str):
                        # Extract first number from string
                        match = re.search(r'(\d+)', value)
                        value = int(match.group(1)) if match else 0
                    else:
                        value = int(value)
                except (ValueError, TypeError, AttributeError):
                    value = 0
                    
            else:  # String fields
                value = str(value).strip() if value else ""
            
            cleaned[new_key] = value
        
        return cleaned
    
    def _extract_skills(self, parsed_jd):
        """Extract skills from parsed JD for the skill taxonomy"""
        skills = set()  # Use set to avoid duplicates
        
        # Extract skills from the parsed JD
        if isinstance(parsed_jd, dict):
            if 'required_skills' in parsed_jd:
                skills.update(parsed_jd['required_skills'])
            if 'preferred_skills' in parsed_jd:
                skills.update(parsed_jd['preferred_skills'])
        
        return list(skills)
