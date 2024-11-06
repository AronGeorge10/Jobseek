import matplotlib.pyplot as plt

# Sample metrics for visualization
metrics = ['Accuracy', 'Precision', 'Recall', 'F1-score', 'User Satisfaction']
scores = [0.85, 0.82, 0.88, 0.85, 0.9]  # Replace with actual scores

# Creating the bar chart
plt.figure(figsize=(10, 6))
plt.bar(metrics, scores, color=['blue', 'green', 'orange', 'red', 'purple'])
plt.xlabel('Evaluation Metrics')
plt.ylabel('Scores')
plt.title('Model Evaluation Metrics')
plt.ylim(0, 1)
plt.show()
