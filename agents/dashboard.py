# agents/dashboard.py
import json

class DashboardAgent:
    def __init__(self, db):
        self.db = db
    
    def generate_dashboard(self, jd_id, session_candidates=None):
        """
        Generate dashboard data for a job description.
        If session_candidates is provided, only these candidates will be considered.
        """
        # Get job description data
        jd_data = self.db.get_job_description(jd_id)
        if not jd_data:
            return {
                "error": "Job description not found"
            }
            
        try:
            # Get matches for this job description
            matches = []
            try:
                # This query would get all matches for the JD
                cursor = self.db.connection.cursor()
                cursor.execute(
                    "SELECT candidate_id, score, justification FROM matches WHERE jd_id = ?", 
                    (jd_id,)
                )
                matches_raw = cursor.fetchall()
                
                # Process match data, filtering by session candidates if provided
                for match in matches_raw:
                    candidate_id = match['candidate_id']
                    
                    # Skip if we're using session candidates and this one isn't in the list
                    if session_candidates is not None and candidate_id not in session_candidates:
                        print(f"Skipping candidate {candidate_id} for dashboard as it wasn't uploaded in this session")
                        continue
                        
                    candidate_data = self.db.get_candidate(candidate_id)
                    if candidate_data:
                        matches.append({
                            'candidate_id': candidate_id,
                            'score': match['score'],
                            'name': candidate_data.get('Name', 'Unknown'),
                            'skills': candidate_data.get('Skills', [])
                        })
            except Exception as e:
                print(f"Error getting matches: {str(e)}")
            
            # Instead of all candidates, only count those related to this job description
            # This only shows real-time uploaded candidates that were matched
            total_candidates = len(matches)
            matched_candidates = len(matches)
            
            # If we have session_candidates but no matches yet, show the count of uploaded candidates
            if session_candidates is not None and matched_candidates == 0:
                total_candidates = len(session_candidates)
                
                # Get these candidates for skill information
                all_candidates = []
                for cid in session_candidates:
                    candidate = self.db.get_candidate(cid)
                    if candidate:
                        all_candidates.append(candidate)
            else:
                all_candidates = [self.db.get_candidate(match['candidate_id']) for match in matches]
                all_candidates = [c for c in all_candidates if c]  # Remove None values
            
            # Calculate average match score
            if matched_candidates > 0:
                avg_match_score = int(sum(match['score'] * 100 for match in matches) / matched_candidates)
            else:
                avg_match_score = 0
                
            # Calculate match distribution
            match_distribution = {
                "90-100%": 0,
                "80-89%": 0,
                "70-79%": 0,
                "60-69%": 0,
                "Below 60%": 0
            }
            
            for match in matches:
                score = match['score'] * 100
                if score >= 90:
                    match_distribution["90-100%"] += 1
                elif score >= 80:
                    match_distribution["80-89%"] += 1
                elif score >= 70:
                    match_distribution["70-79%"] += 1
                elif score >= 60:
                    match_distribution["60-69%"] += 1
                else:
                    match_distribution["Below 60%"] += 1
            
            # Get top skills from matched candidates only
            all_skills = {}
            for candidate in all_candidates:
                if candidate:
                    skills = candidate.get('Skills', [])
                    for skill in skills:
                        if skill in all_skills:
                            all_skills[skill] += 1
                        else:
                            all_skills[skill] = 1
            
            # Sort skills by frequency
            top_skills = [
                {"name": skill, "count": count}
                for skill, count in sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Prepare dashboard data
            dashboard_data = {
                "job_title": jd_data.get('title', 'Unknown Position'),
                "company": jd_data.get('company', 'Unknown Company'),
                "total_candidates": total_candidates,
                "matched_candidates": matched_candidates,
                "avg_match_score": avg_match_score,
                "top_skills": top_skills,
                "match_distribution": match_distribution,
                "status_breakdown": {
                    "interview_requested": 0,  # This would be set from real data in production
                    "interview_scheduled": 0,
                    "rejected": 0,
                    "pending": matched_candidates
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            print(f"Error generating dashboard: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return minimal valid data if there's an error
            return {
                "job_title": jd_data.get('title', 'Unknown Position'),
                "company": jd_data.get('company', 'Unknown Company'),
                "total_candidates": 0,
                "matched_candidates": 0,
                "avg_match_score": 0,
                "top_skills": [],
                "match_distribution": {},
                "status_breakdown": {}
            }
