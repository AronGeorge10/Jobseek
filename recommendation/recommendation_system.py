import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import src.notebook.skills_extraction as skills_extraction
from ftfy import fix_text
import re  # Import the re module

def get_recommendations(user_id, job_data):
    # Extract skills from the user's resume
    resume_path = f'E:\\jobseek\\recommendation\\utilities\\resumes\\{user_id}.pdf'  # Update with actual path
    skills = skills_extraction.skills_extractor(resume_path)
    skills_text = ' '.join(skills)

    # Load job profiles
    job_profiles = load_job_profiles(job_data)

    # Vectorize the skills and job profiles
    vectorizer = TfidfVectorizer(min_df=1, analyzer=ngrams, lowercase=False)
    tfidf_job_profiles = vectorizer.fit_transform(job_profiles['Processed_JD'])
    tfidf_skills = vectorizer.transform([skills_text])

    # Find the nearest neighbors
    nbrs = NearestNeighbors(n_neighbors=5, n_jobs=-1).fit(tfidf_job_profiles)
    distances, indices = nbrs.kneighbors(tfidf_skills)

    # Get top N recommendations
    recommended_jobs = job_data.iloc[indices[0]]

    return recommended_jobs

def load_job_profiles(job_data):
    # Ensure job_data contains the expected features
    expected_features = ['Processed_JD']
    if not all(feature in job_data.columns for feature in expected_features):
        raise ValueError(f"Job data must contain the following features: {expected_features}")
    
    return job_data[expected_features]

def load_job_data():
    return pd.read_csv(r'E:\jobseek\src\data\jd_structured_data.csv')

def ngrams(string, n=3):
    string = fix_text(string)  # fix text
    string = string.encode("ascii", errors="ignore").decode()  # remove non-ascii chars
    string = string.lower()
    chars_to_remove = [")", "(", ".", "|", "[", "]", "{", "}", "'"]
    rx = '[' + re.escape(''.join(chars_to_remove)) + ']'
    string = re.sub(rx, '', string)
    string = string.replace('&', 'and')
    string = string.replace(',', ' ')
    string = string.replace('-', ' ')
    string = string.title()  # normalize case - capital at start of each word
    string = re.sub(' +', ' ', string).strip()  # get rid of multiple spaces and replace with a single
    string = ' ' + string + ' '  # pad names for ngrams...
    string = re.sub(r'[,-./]|\sBD', r'', string)
    ngrams = zip(*[string[i:] for i in range(n)])
    return [''.join(ngram) for ngram in ngrams]
