# agents/dashboard.py
import json

class DashboardAgent:
    def __init__(self, db):
        self.db = db
    
    def generate_dashboard(self, jd_id):
        """
        Generate dashboard data for a job description
        """
        # In a real system, we would query the database for actual statistics
        # For the hackathon, we'll generate some sample data
        
        # Get job description data
        jd_data = self.db.get_job_description(jd_id)
        if not jd_data:
            return {
                "error": "Job description not found"
            }
        
        # Sample dashboard data
        dashboard_data = {
            "job_title": jd_data.get('title', 'Unknown Position'),
            "company": jd_data.get('company', 'Unknown Company'),
            "total_candidates": 10,  # Example value
            "matched_candidates": 4,  # Example value
            "avg_match_score": 76,  # Example percentage
            "top_skills": [
                {"name": "Python", "count": 8},
                {"name": "JavaScript", "count": 6},
                {"name": "SQL", "count": 5},
                {"name": "REST API", "count": 4},
                {"name": "Git", "count": 4}
            ],
            "match_distribution": {
                "90-100%": 1,
                "80-89%": 3,
                "70-79%": 2,
                "60-69%": 1,
                "Below 60%": 3
            },
            "status_breakdown": {
                "interview_requested": 2,
                "interview_scheduled": 1,
                "rejected": 1,
                "pending": 6
            }
        }
        
        return dashboard_data
