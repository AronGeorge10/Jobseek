import sys
import os

# Add the src directory to the Python path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
print(f"Adding to sys.path: {src_path}")
sys.path.append(src_path)

import streamlit as st
import pandas as pd
import PyPDF2
from pyresparser import ResumeParser
from sklearn.neighbors import NearestNeighbors
from components.job_recommender import ngrams, getNearestN, jd_df
import notebook.skills_extraction as skills_extraction
from sklearn.feature_extraction.text import TfidfVectorizer

# Function to process the resume and recommend jobs
def process_resume(file):
    try:
        # Extract text from PDF resume
        resume_skills = skills_extraction.skills_extractor(file)

        # Perform job recommendation based on parsed resume data
        skills = []
        skills.append(' '.join(word for word in resume_skills))
        
        # Feature Engineering:
        vectorizer = TfidfVectorizer(min_df=1, analyzer=ngrams, lowercase=False)
        tfidf = vectorizer.fit_transform(skills)

        nbrs = NearestNeighbors(n_neighbors=1, n_jobs=-1).fit(tfidf)
        jd_test = (jd_df['Processed_JD'].values.astype('U'))

        distances, indices = getNearestN(jd_test)
        test = list(jd_test) 
        matches = []

        for i, j in enumerate(indices):
            dist = round(distances[i][0], 2)
            temp = [dist]
            matches.append(temp)
        
        matches = pd.DataFrame(matches, columns=['Match confidence'])

        # Following recommends Top 5 Jobs based on candidate resume:
        jd_df['match'] = matches['Match confidence']
        
        return jd_df.head(5).sort_values('match')
    except Exception as e:
        raise

# Streamlit app
def main():
    st.title("Job Recommendation App")
    st.write("Upload your resume in PDF format")

    # File uploader
    uploaded_file = st.file_uploader("Choose a file", type=['pdf'])

    if uploaded_file is not None:
        try:
            # Process resume and recommend jobs
            df_jobs = process_resume(uploaded_file)

            # Display recommended jobs as DataFrame
            st.write("Recommended Jobs:")
            st.dataframe(df_jobs[['Job Title', 'Company Name', 'Location', 'Industry', 'Sector', 'Average Salary']])
        except Exception as e:
            st.error(f"An error occurred: {e}")

# Run the Streamlit app
if __name__ == '__main__':
    main()
