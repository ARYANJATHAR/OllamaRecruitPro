# main.py
from __init__ import OllamaRecruitPro
import os
import PyPDF2
import pandas as pd
from pathlib import Path

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def process_cv_directory(cv_directory):
    """Process all PDF CVs in the specified directory."""
    cv_texts = []
    cv_files = []
    for file in os.listdir(cv_directory):
        if file.lower().endswith('.pdf'):
            pdf_path = os.path.join(cv_directory, file)
            cv_text = extract_text_from_pdf(pdf_path)
            cv_texts.append(cv_text)
            cv_files.append(file)
    return cv_texts, cv_files

def process_job_descriptions_csv(csv_path):
    """Process job descriptions from a CSV file."""
    df = pd.read_csv(csv_path)
    return df.to_dict('records')

def main():
    # Initialize the system
    system = OllamaRecruitPro()
    
    # Directory containing PDF CVs (using test directory)
    cv_directory = "cv_data_test"  # Using test directory with 10 CVs
    job_descriptions_csv = "job_description.csv"
    
    # Process all CVs from the directory
    cv_texts, cv_files = process_cv_directory(cv_directory)
    candidate_info = []
    
    print(f"\nProcessing {len(cv_texts)} CVs from {cv_directory}...")
    print("-" * 50)
    
    for i, (cv_text, cv_file) in enumerate(zip(cv_texts, cv_files)):
        # Process CV and get candidate ID
        candidate_id = system.process_cv(cv_text)
        
        # Get detailed candidate information from the database
        candidate_data = system.db.get_candidate(candidate_id)
        
        # Extract relevant information
        candidate_name = candidate_data.get('Name', 'Unknown')
        candidate_email = candidate_data.get('Email', 'Not provided')
        candidate_phone = candidate_data.get('Phone', 'Not provided')
        candidate_skills = candidate_data.get('Skills', [])
        candidate_experience = candidate_data.get('Experience', [])
        candidate_education = candidate_data.get('Education', [])
        
        # Store candidate information
        candidate_info.append({
            'id': candidate_id,
            'name': candidate_name,
            'file': cv_file,
            'email': candidate_email,
            'phone': candidate_phone,
            'skills': candidate_skills,
            'experience': candidate_experience,
            'education': candidate_education
        })
        
        # Print processing status
        print(f"\nProcessed CV {i+1}/{len(cv_texts)}: {cv_file}")
        print(f"Candidate ID: {candidate_id}")
        print(f"Name: {candidate_name}")
        print(f"Email: {candidate_email}")
        print(f"Phone: {candidate_phone}")
        print(f"Number of Skills: {len(candidate_skills)}")
        print("-" * 50)
    
    print("\nDetailed Candidate Information Summary:")
    print("=" * 50)
    for info in candidate_info:
        print(f"\nCV File: {info['file']}")
        print(f"Candidate ID: {info['id']}")
        print(f"Name: {info['name']}")
        print(f"Email: {info['email']}")
        print(f"Phone: {info['phone']}")
        print("\nSkills:")
        for skill in info['skills']:
            print(f"- {skill}")
        print("\nExperience:")
        for exp in info['experience']:
            print(f"- {exp}")
        print("\nEducation:")
        for edu in info['education']:
            print(f"- {edu}")
        print("-" * 50)
    
    # Process job descriptions from CSV
    print("\nProcessing Job Descriptions...")
    print("=" * 50)
    job_descriptions = process_job_descriptions_csv(job_descriptions_csv)
    
    for job in job_descriptions:
        job_title = job.get('Job Title', '')
        job_description = job.get('Job Description', '')
        
        # Process the job description
        jd_id = system.process_job_description(job_description)
        print(f"\nProcessing job: {job_title}")
        print(f"Job Description ID: {jd_id}")
        
        # Match candidates to the job description
        matches = system.match_candidates(jd_id)
        print(f"\nFound {len(matches)} potential matches for {job_title}")
        
        # Display top 5 matches with detailed information
        print("\nTop 5 Matches:")
        print("-" * 50)
        for i, match in enumerate(matches[:5]):
            candidate_id = match['candidate_id']
            candidate_data = next((c for c in candidate_info if c['id'] == candidate_id), None)
            
            print(f"\nMatch #{i+1}:")
            if candidate_data:
                print(f"Name: {candidate_data['name']}")
                print(f"Candidate ID: {candidate_id}")
                print(f"Match Score: {match['score']:.2f}")
                print("Skills Match:")
                print(match['justification'])
            print("-" * 30)
        
        # Get and display dashboard data
        dashboard_data = system.get_dashboard_data(jd_id)
        print(f"\nDashboard data generated for {job_title}")
        print("=" * 50)

if __name__ == "__main__":
    main()
