import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def load_jobs_data(file_path):
    return pd.read_csv(file_path)

def preprocess_text(text):
    return ' '.join(word.strip().lower() for word in str(text).split())

def recommend_jobs(jobs_data, input_skills, num_recommendations=3):
    print(f"Input skills: {input_skills}")  # Debug print
    
    # Combine all relevant fields for matching
    jobs_data['combined_text'] = jobs_data['Job Title'] + ' ' + jobs_data['Industry'] + ' ' + jobs_data['Sector'] + ' ' + jobs_data['Key Skills']
    jobs_data['combined_text'] = jobs_data['combined_text'].apply(preprocess_text)
    
    input_skills = preprocess_text(input_skills)

    vectorizer = TfidfVectorizer()
    text_matrix = vectorizer.fit_transform(jobs_data['combined_text'])
    input_vector = vectorizer.transform([input_skills])

    cosine_similarities = cosine_similarity(input_vector, text_matrix).flatten()
    job_matches = list(zip(range(len(jobs_data)), cosine_similarities))
    job_matches.sort(key=lambda x: x[1], reverse=True)

    recommendations = []
    unique_titles = set()
    for idx, score in job_matches:
        job = jobs_data.iloc[idx]
        title = job['Job Title']
        if title not in unique_titles:
            unique_titles.add(title)
            recommendations.append({
                "title": title,
                "industry": job['Industry'],
                "sector": job['Sector'],
                "salary": job['Job Salary'],
                "score": score * 100
            })
            if len(recommendations) == num_recommendations:
                break

    print(f"Number of recommendations: {len(recommendations)}")  # Debug print
    for job in recommendations:
        print(f"Job: {job['title']}, Score: {job['score']}")  # Debug print

    return recommendations

# Load the jobs data when the module is imported
jobs_data = load_jobs_data('E:\jobseek\jobs.csv')

def get_job_recommendations(skills):
    return recommend_jobs(jobs_data, skills)
