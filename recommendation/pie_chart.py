import matplotlib.pyplot as plt

# Sample demographics data for visualization
demographics = ['Male', 'Female', 'Non-Binary', 'Others']
distribution = [45, 40, 10, 5]  # Replace with actual data

# Creating the pie chart
plt.figure(figsize=(8, 8))
plt.pie(distribution, labels=demographics, autopct='%1.1f%%', startangle=140, colors=['skyblue', 'lightcoral', 'yellowgreen', 'orange'])
plt.title('Demographic Distribution in Job Recommendations')
plt.show()
