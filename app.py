# app.py
from flask import Flask, render_template, request, jsonify
from __init__ import OllamaRecruitPro
import os
import time

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ui', 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
recruit_system = OllamaRecruitPro()

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
        processing_status['jd_processing'] = True
        jd_text = request.form.get('jd_text', '')
        if not jd_text:
            return jsonify({
                'success': False,
                'error': 'No job description provided'
            }), 400
            
        jd_id = recruit_system.process_job_description(jd_text)
        
        return jsonify({
            'success': True,
            'jd_id': jd_id,
            'message': 'Job description processed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        processing_status['jd_processing'] = False

@app.route('/upload_cv', methods=['POST'])
def upload_cv():
    try:
        processing_status['cv_processing'] = True
        cv_text = request.form.get('cv_text', '')
        if not cv_text:
            return jsonify({
                'success': False,
                'error': 'No CV text provided'
            }), 400
            
        candidate_id = recruit_system.process_cv(cv_text)
        
        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'message': 'CV processed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        processing_status['cv_processing'] = False

@app.route('/match', methods=['POST'])
def match():
    try:
        processing_status['matching_in_progress'] = True
        jd_id = request.form.get('jd_id', '')
        if not jd_id:
            return jsonify({
                'success': False,
                'error': 'No job description ID provided'
            }), 400
            
        matches = recruit_system.match_candidates(int(jd_id))
        
        return jsonify({
            'success': True,
            'matches': matches,
            'message': f'Found {len(matches)} matches'
        })
    except Exception as e:
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

@app.route('/dashboard/<int:jd_id>')
def dashboard(jd_id):
    try:
        dashboard_data = recruit_system.get_dashboard_data(jd_id)
        
        return jsonify({
            'success': True,
            'dashboard_data': dashboard_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/status')
def get_status():
    return jsonify(processing_status)

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
