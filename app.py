# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from __init__ import OllamaRecruitPro
import os
import time
import pandas as pd
from werkzeug.utils import secure_filename
import csv
import re
import traceback
from PyPDF2 import PdfReader
import json
import sqlite3

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui', 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.urandom(24)  # Required for session
recruit_system = OllamaRecruitPro()

# Configure upload folders
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'csv', 'txt', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folders if they don't exist
os.makedirs(os.path.join(UPLOAD_FOLDER, 'job_descriptions'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'cvs'), exist_ok=True)

# Track real-time uploaded candidates for the current session
@app.before_request
def initialize_session():
    if 'uploaded_candidate_ids' not in session:
        session['uploaded_candidate_ids'] = []
    if 'current_jd_id' not in session:
        session['current_jd_id'] = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_file_content(file_path):
    """Read content from CSV and PDF files."""
    print(f"Reading file content from: {file_path}")
    try:
        if file_path.endswith(".csv"):
            try:
                # First try to read as a simple CSV file
                with open(file_path, "r", encoding="utf-8") as f:
                    csv_content = f.read()
                    
                # Check if it's a simple CSV with just text
                if len(csv_content.split(",")) <= 2 and len(csv_content.split("\n")) <= 3:
                        print(f"Simple CSV detected, treating as text")
                        return csv_content
                        
                # Otherwise try to parse as a structured CSV
                data = []
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Clean up the data
                            cleaned_row = {k.strip(): v.strip() if isinstance(v, str) else v 
                                         for k, v in row.items() if k is not None}
                            if cleaned_row:  # Only append non-empty rows
                                data.append(cleaned_row)
                    except Exception as csv_error:
                        print(f"CSV parsing error: {str(csv_error)}")
                        # If DictReader fails, try reading as plain text
                        f.seek(0)
                        return f.read()
                
                # If we have data, format it properly
                if data:
                    job_data = data[0]  # Take the first row as our job description
                    
                    # Extract skills from the description
                    description = job_data.get('Job Description', '')
                    
                    # If we don't have a job description field, try to use the first large text field
                    if not description:
                        for key, value in job_data.items():
                            if isinstance(value, str) and len(value) > 100:
                                description = value
                                break
                    
                    required_skills = []
                    preferred_skills = []
                    
                    # Look for skills sections in the description
                    if description and 'Required Skills:' in description:
                        skills_text = description.split('Required Skills:')[1]
                        if 'Preferred Skills:' in skills_text:
                            required_part = skills_text.split('Preferred Skills:')[0]
                            preferred_part = skills_text.split('Preferred Skills:')[1]
                            required_skills = [s.strip() for s in required_part.split('\n') if s.strip()]
                            preferred_skills = [s.strip() for s in preferred_part.split('\n') if s.strip()]
                        else:
                            required_skills = [s.strip() for s in skills_text.split('\n') if s.strip()]
                    
                    # Try to extract skills from a dedicated skills field
                    if 'Required Skills' in job_data:
                        skills_text = job_data.get('Required Skills', '')
                        if skills_text:
                            # Try to split by common delimiters
                            if ',' in skills_text:
                                required_skills = [s.strip() for s in skills_text.split(',') if s.strip()]
                            elif ';' in skills_text:
                                required_skills = [s.strip() for s in skills_text.split(';') if s.strip()]
                            elif '\n' in skills_text:
                                required_skills = [s.strip() for s in skills_text.split('\n') if s.strip()]
                            else:
                                required_skills = [skills_text.strip()]
                    
                    # Format the data for processing
                    formatted_data = {
                        'title': job_data.get('Job Title', job_data.get('Position', 'Not specified')),
                        'company': job_data.get('Company', 'Not specified'),
                        'description': description,
                        'required_skills': required_skills,
                        'preferred_skills': preferred_skills,
                        'required_experience': job_data.get('Required Experience', job_data.get('Experience', 'Not specified')),
                        'required_education': job_data.get('Required Education', job_data.get('Education', 'Not specified'))
                    }
                    
                    # Return JSON data but also allow for raw text to be processed
                    return json.dumps(formatted_data)
                
                # If all else fails, return the raw CSV content
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
                    
            except Exception as e:
                print(f"Error reading CSV file: {str(e)}")
                # Try reading as plain text as a fallback
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return f.read()
                except:
                    return ""
                    
        elif file_path.endswith(".pdf"):
            try:
                # Enhanced PDF reading with PyPDF2
                text = ""
                with open(file_path, "rb") as file:
                    pdf_reader = PdfReader(file)
                    if len(pdf_reader.pages) == 0:
                        print(f"Warning: PDF file has no pages: {file_path}")
                        return ""
                        
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n\n"  # Add space between pages
                        except Exception as page_error:
                            print(f"Error extracting text from page {page_num}: {str(page_error)}")
                
                if not text.strip():
                    print(f"Warning: No text extracted from PDF file: {file_path}")
                    return ""
                
                # For job descriptions, check if this looks like a JD and try to structure it
                if "job description" in text.lower() or "position" in text.lower() or "responsibilities" in text.lower():
                    # This might be a job description
                    job_data = {}
                    
                    # Try to extract a title
                    title_match = re.search(r'^(.+?)\n', text) or re.search(r'job title[:\s]+(.+?)[\n\.]', text, re.IGNORECASE)
                    if title_match:
                        job_data['title'] = title_match.group(1).strip()
                    
                    # Try to extract a company
                    company_match = re.search(r'company[:\s]+(.+?)[\n\.]', text, re.IGNORECASE)
                    if company_match:
                        job_data['company'] = company_match.group(1).strip()
                    
                    # Try to extract required skills
                    skills_match = re.search(r'required skills[:\s]+(.+?)(?=preferred skills|\n\n|$)', text, re.IGNORECASE | re.DOTALL)
                    if skills_match:
                        skills_text = skills_match.group(1).strip()
                        # Split by common list markers
                        skills = re.split(r'[•\-*]\s*|\d+\.\s*|\n', skills_text)
                        job_data['required_skills'] = [s.strip() for s in skills if s.strip()]
                    
                    # Try to extract required experience
                    exp_match = re.search(r'(\d+)[\+]?\s*(?:years?|yrs)[\s\w]*experience', text, re.IGNORECASE)
                    if exp_match:
                        job_data['required_experience'] = exp_match.group(1).strip()
                    
                    # Try to extract required education
                    edu_match = re.search(r'(?:Bachelor|Master|PhD|Degree|Diploma)[\s\w]*(?:in|of)[\s\w]+', text, re.IGNORECASE)
                    if edu_match:
                        job_data['required_education'] = edu_match.group(0).strip()
                    
                    # If we've extracted some structured data, return it as JSON
                    if job_data:
                        if 'title' not in job_data:
                            job_data['title'] = "Untitled Position"
                        if 'company' not in job_data:
                            job_data['company'] = "Unknown Company"
                        if 'required_skills' not in job_data:
                            job_data['required_skills'] = []
                        if 'preferred_skills' not in job_data:
                            job_data['preferred_skills'] = []
                        
                        return json.dumps(job_data)
                
                # Return the raw text if no structured data was extracted
                return text
                
            except Exception as e:
                print(f"Error reading PDF: {str(e)}")
                traceback.print_exc()
                return ""
        elif file_path.endswith(".txt"):
            # Handle plain text files
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading text file: {str(e)}")
                return ""
        else:
            print(f"Unsupported file type: {file_path}")
            return ""
    except Exception as e:
        print(f"General error reading file: {str(e)}")
        traceback.print_exc()
        return ""

# Track processing status
processing_status = {
    'jd_processing': False,
    'cv_processing': False,
    'matching_in_progress': False
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_jd', methods=['POST'])
def upload_jd():
    try:
        if 'jd_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400

        file = request.files['jd_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            allowed_extensions_str = ', '.join(ALLOWED_EXTENSIONS)
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Supported types: {allowed_extensions_str}'
            }), 400

        try:
            processing_status['jd_processing'] = True
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'job_descriptions', filename)
            file.save(file_path)

            print(f"Saved job description file to {file_path}")

            # Read file content
            jd_text = read_file_content(file_path)
            if not jd_text:
                return jsonify({
                    'success': False,
                    'error': 'Could not read file content. The file may be empty or corrupted.'
                }), 400

            print(f"Successfully read job description content ({len(jd_text)} chars)")
            
            # Process the job description
            try:
                jd_id = recruit_system.process_job_description(jd_text)
                if not jd_id:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to process job description. The system returned an invalid ID.'
                    }), 500
                    
                print(f"Successfully processed job description with ID: {jd_id}")
                
                # Store the current job description ID in the session
                session['current_jd_id'] = jd_id
                session['uploaded_candidate_ids'] = []  # Reset uploaded candidates for new JD
                session.modified = True
                
                # Get processed JD data
                jd_data = recruit_system.db.get_job_description(jd_id)
                if not jd_data:
                    return jsonify({
                        'success': True,
                        'jd_id': jd_id,
                        'jd_data': {
                            'title': 'Unknown Position',
                            'company': 'Unknown Company',
                            'required_skills': [],
                            'preferred_skills': [],
                            'required_experience': 0,
                            'required_education': ''
                        },
                        'message': 'Job description saved but could not retrieve details'
                    })
                
                return jsonify({
                    'success': True,
                    'jd_id': jd_id,
                    'jd_data': {
                        'title': jd_data.get('title', 'Job Position'),
                        'company': jd_data.get('company', 'Company'),
                        'required_skills': jd_data.get('required_skills', []),
                        'preferred_skills': jd_data.get('preferred_skills', []),
                        'required_experience': jd_data.get('required_experience', 0),
                        'required_education': jd_data.get('required_education', '')
                    },
                    'message': 'Job description processed successfully'
                })
            except Exception as process_error:
                print(f"Error in job description processing: {str(process_error)}")
                import traceback
                traceback.print_exc()
                
                # Return a more descriptive error
                return jsonify({
                    'success': False,
                    'error': f'Error processing job description: {str(process_error)}',
                    'details': 'The file was uploaded but could not be processed correctly.'
                }), 500
                
        except IOError as io_error:
            print(f"File IO error: {str(io_error)}")
            return jsonify({
                'success': False,
                'error': f'File IO error: {str(io_error)}'
            }), 500
            
    except Exception as e:
        print(f"Unexpected error in upload_jd: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500
    finally:
        processing_status['jd_processing'] = False

@app.route('/upload_cv', methods=['POST'])
def upload_cv():
    """Upload and process CV."""
    try:
        if "cv_file" not in request.files:
            print("Error: No file part in request")
            return jsonify({"success": False, "message": "No file part"}), 400
            
        file = request.files["cv_file"]
        if file.filename == "":
            print("Error: No selected file")
            return jsonify({"success": False, "message": "No selected file"}), 400
            
        if not allowed_file(file.filename):
            print(f"Error: File type not allowed for {file.filename}")
            return jsonify({"success": False, "message": f"File type not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400
            
        # Save the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], "cvs", filename)
        file.save(filepath)
        
        # Read the content from the file
        content = read_file_content(filepath)
        if not content:
            print(f"Error: Failed to extract content from file {filename}")
            return jsonify({"success": False, "message": f"Failed to extract content from file {filename}. Please ensure the file is not corrupted and is in a supported format."}), 400
        
        # Simply parse the CV text with the CV parser
        try:
            cv_data = recruit_system.cv_parser.parse(content)
            
            if not cv_data:
                print(f"Error: Failed to parse CV content from {filename}")
                return jsonify({"success": False, "message": f"Failed to parse CV content from {filename}. Please ensure the file contains valid CV data."}), 400
            
            # Ensure candidate_id is valid
            candidate_id = cv_data.get("Candidate_ID")
            if not candidate_id or candidate_id == "undefined":
                timestamp = int(time.time())
                candidate_id = f"C{timestamp % 10000}"
                cv_data["Candidate_ID"] = candidate_id
            
            # Simple insertion into database
            db_id = recruit_system.db.insert_candidate(cv_data)
            
            # Store the candidate ID in the session for this upload session
            if 'uploaded_candidate_ids' not in session:
                session['uploaded_candidate_ids'] = []
            session['uploaded_candidate_ids'].append(db_id)
            session.modified = True
            
            return jsonify({
                "success": True,
                "message": f"CV uploaded and parsed successfully. Candidate ID: {candidate_id}",
                "candidate_id": db_id,
                "candidate_data": cv_data
            }), 200
            
        except Exception as e:
            print(f"Error processing CV: {str(e)}")
            traceback.print_exc()
            return jsonify({"success": False, "message": f"Error processing CV: {str(e)}"}), 500
    
    except Exception as e:
        print(f"Error in upload_cv: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/get_candidate/<int:candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    try:
        candidate_data = recruit_system.get_candidate_details(candidate_id)
        if not candidate_data:
            return jsonify({
                'success': False,
                'error': 'Candidate not found'
            }), 404
            
        return jsonify({
            'success': True,
            'candidate': candidate_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/match_candidates', methods=['POST'])
def match_candidates():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        jd_id = data.get('jd_id')
        candidate_ids = data.get('candidate_ids', [])
        
        if not jd_id:
            return jsonify({'success': False, 'error': 'Job description ID is required'}), 400
            
        # Set matching status
        processing_status['matching_in_progress'] = True
        
        print(f"Starting matching process for JD ID {jd_id} with candidates: {candidate_ids}")
        
        # Get job description data
        jd_data = recruit_system.db.get_job_description(jd_id)
        if not jd_data:
            return jsonify({'success': False, 'error': f'Job description with ID {jd_id} not found'}), 404
        
        # Ensure we have valid candidates to match
        if not candidate_ids or len(candidate_ids) == 0:
            # Try to get all candidates from the database
            print("No candidate IDs provided, fetching all candidates")
            all_candidates = recruit_system.db.get_all_candidates()
            candidate_ids = [c.get('id') for c in all_candidates]
            
            if not candidate_ids or len(candidate_ids) == 0:
                return jsonify({
                    'success': False, 
                    'error': 'No candidates available to match. Please upload CVs first.'
                }), 400
        
        # Check what candidates we have in the session
        session_candidates = session.get('uploaded_candidate_ids', [])
        print(f"Session candidates: {session_candidates}")
        
        # Use all submitted candidate IDs (both from session and direct upload)
        try:
            # Perform matching with detailed CV analysis
            matches = recruit_system.match_candidates(jd_id, candidate_ids)
            
            print(f"Got {len(matches)} matches from recruit_system.match_candidates")
            
            if not matches or len(matches) == 0:
                return jsonify({
                    'success': True,
                    'matches': [],
                    'message': 'No matching candidates found for this job description'
                })
            
            # Format job description data
            formatted_jd = {
                'title': jd_data.get('title', 'Job Position'),
                'company': jd_data.get('company', 'Company'),
                'required_skills': jd_data.get('required_skills', []),
                'preferred_skills': jd_data.get('preferred_skills', []),
                'required_experience': jd_data.get('required_experience', 'Not specified'),
                'required_education': jd_data.get('required_education', 'Not specified')
            }
            
            # Prepare response data
            match_results = []
            for i, match in enumerate(matches):
                # Format the score to display as percentage
                score_percent = int(match['score'] * 100)
                
                # Debug each match
                print(f"Processing match {i}:")
                print(f"  - candidate_id: {match.get('candidate_id')}")
                print(f"  - candidate_info: {match.get('candidate_info', {}).get('name', 'Unknown')}")
                
                # Make sure the result structure matches what the frontend expects
                match_result = {
                    'candidate_id': match.get('candidate_id'),       # Keep database ID for reference
                    'candidate_info': match.get('candidate_info', {}),   # Keep the entire candidate_info object intact
                    'score': match.get('score', 0),                  # Raw score (0-1)
                    'score_percent': score_percent,                  # Percentage (0-100)
                    'analysis': match.get('analysis', ''),
                    'jd_data': formatted_jd  # Include the job description data
                }
                match_results.append(match_result)
            
            # Log the match results to console for debugging
            print(f"Match results prepared for web display: {len(match_results)} candidates")
            
            # Try to update dashboard data after matching
            try:
                # Set the session_candidate_ids in the app context for the dashboard
                app.config['SESSION_CANDIDATE_IDS'] = session.get('uploaded_candidate_ids', [])
                recruit_system.get_dashboard_data(jd_id)
            except Exception as e:
                print(f"Failed to update dashboard: {str(e)}")
            
            return jsonify({
                'success': True,
                'matches': match_results,
                'message': f'Found {len(match_results)} matching candidates'
            })
        except Exception as matching_error:
            print(f"Error during candidate matching: {str(matching_error)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'success': False,
                'error': f'Error during candidate matching: {str(matching_error)}'
            }), 500
    except Exception as e:
        processing_status['matching_in_progress'] = False
        print(f"Error in match_candidates: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        processing_status['matching_in_progress'] = False

@app.route('/request_interviews', methods=['POST'])
def request_interviews():
    try:
        jd_id = request.form.get('jd_id', '')
        candidate_ids = request.form.getlist('candidate_ids[]')
        
        if not jd_id or not candidate_ids:
            return jsonify({
                'success': False,
                'error': 'Missing job description ID or candidate IDs'
            }), 400
            
        recruit_system.send_interview_requests(int(jd_id), [int(cid) for cid in candidate_ids])
        
        return jsonify({
            'success': True,
            'message': f"Interview requests sent to {len(candidate_ids)} candidates"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reject_candidates', methods=['POST'])
def reject_candidates():
    try:
        jd_id = request.form.get('jd_id', '')
        candidate_ids = request.form.getlist('candidate_ids[]')
        
        if not jd_id or not candidate_ids:
            return jsonify({
                'success': False,
                'error': 'Missing job description ID or candidate IDs'
            }), 400
            
        recruit_system.send_rejection_emails(int(jd_id), [int(cid) for cid in candidate_ids])
        
        return jsonify({
            'success': True,
            'message': f"Rejection emails sent to {len(candidate_ids)} candidates"
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard/<int:jd_id>')
def dashboard(jd_id):
    try:
        # Pass session-uploaded candidates to the dashboard
        session_candidates = session.get('uploaded_candidate_ids', [])
        dashboard_data = recruit_system.get_dashboard_data(jd_id, session_candidates)
        return jsonify({
            'success': True,
            'dashboard_data': dashboard_data
        })
    except Exception as e:
        print(f"Error fetching dashboard data: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reset_database', methods=['POST'])
def reset_database():
    """Reset the database to remove pre-loaded data and only keep real-time uploaded data"""
    try:
        # Create a new connection to avoid issues with other connections
        conn = sqlite3.connect(recruit_system.db.db_path)
        cursor = conn.cursor()
        
        # Clear all tables but keep the structure
        cursor.execute("DELETE FROM candidates")
        cursor.execute("DELETE FROM job_descriptions")
        cursor.execute("DELETE FROM matches")
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Database reset successfully. Only real-time uploaded data will be shown.'
        })
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get the current processing status."""
    try:
        return jsonify({
            'success': True,
            'status': processing_status,
            'session_info': {
                'has_jd': 'current_jd_id' in session,
                'uploaded_candidates_count': len(session.get('uploaded_candidate_ids', []))
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

@app.route('/api/job-descriptions/<int:jd_id>', methods=['GET'])
def get_job_description(jd_id):
    try:
        jd_data = recruit_system.db.get_job_description(jd_id)
        if not jd_data:
            return jsonify({"success": False, "message": "Job description not found"}), 404
            
        return jsonify({
            "success": True,
            "job_description": jd_data
        })
    except Exception as e:
        print(f"Error getting job description: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/current_jd', methods=['GET'])
def get_current_jd():
    """Get the current job description details."""
    try:
        if 'current_jd_id' not in session:
            return jsonify({
                'success': False,
                'error': 'No job description uploaded'
            }), 404
        
        jd_id = session['current_jd_id']
        jd_data = recruit_system.db.get_job_description(jd_id)
        
        if not jd_data:
            return jsonify({
                'success': False,
                'error': 'Job description not found'
            }), 404
        
        # Parse the stored job description data
        try:
            jd_content = json.loads(jd_data['content'])
        except:
            jd_content = {
                'position': 'Not specified',
                'company': 'Not specified',
                'description': jd_data.get('content', ''),
                'required_skills': [],
                'preferred_skills': [],
                'required_experience': 'Not specified',
                'required_education': 'Not specified'
            }
        
        return jsonify({
            'success': True,
            'job_description': jd_content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
