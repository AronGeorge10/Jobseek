import csv
from collections import defaultdict

def load_jobs_data(file_path):
    jobs_data = defaultdict(list)
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            job_title = row['Job Title']
            skills = row['Key Skills'].split('|') 
            jobs_data[job_title].extend(skills)
    return jobs_data

def recommend_jobs(jobs_data, input_skills, num_recommendations=3):
    input_skills = set(skill.strip().lower() for skill in input_skills)
    job_matches = {}

    for job, required_skills in jobs_data.items():
        required_skills = set(skill.strip().lower() for skill in required_skills)
        match_score = len(input_skills.intersection(required_skills)) / len(required_skills)
        job_matches[job] = match_score

    top_jobs = sorted(job_matches.items(), key=lambda x: x[1], reverse=True)[:num_recommendations]
    return top_jobs

def main():
    jobs_data = load_jobs_data('jobs.csv')
    
    while True:
        user_skills = input("Enter your skills (comma-separated) or 'quit' to exit: ")
        if user_skills.lower() == 'quit':
            break
        
        skills_list = [skill.strip() for skill in user_skills.split(',')]
        recommended_jobs = recommend_jobs(jobs_data, skills_list)
        
        print("\nTop 3 Recommended Jobs:")
        for i, (job, score) in enumerate(recommended_jobs, 1):
            print(f"{i}. {job} (Match Score: {score:.2%})")

if __name__ == "__main__":
    main()
