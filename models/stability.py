# import datetime

# from cleaned import employment_history  # Assuming employment_history is a list of dicts with 'from' and 'to' dates

# def calculate_stability(job_durations):
#     """
#     Calculate the stability of a person based on their job durations.

#     Parameters:
#     job_durations (list of int): List of job durations in months.

#     Returns:
#     float: Stability score (higher means more stable).
#     """
#     if not job_durations:
#         return 0.0

#     total_duration = sum(job_durations)
#     num_jobs = len(job_durations)
#     average_duration = total_duration / num_jobs

#     # Stability score is the average duration of jobs
#     stability_score = average_duration

#     return stability_score

# def calculate_job_durations(employment_history):
#     """
#     Calculate job durations from employment history.

#     Parameters:
#     employment_history (list of dict): List of employment history with 'from' and 'to' dates.

#     Returns:
#     list of int: List of job durations in months.
#     """
#     job_durations = []
#     for job in employment_history:
#         from_date = datetime.datetime.strptime(job['from'], '%Y-%m-%d')
#         to_date = datetime.datetime.strptime(job['to'], '%Y-%m-%d')
#         duration = (to_date - from_date).days // 30  # Convert days to months
#         job_durations.append(duration)
#     return job_durations

# # Example usage
# employment_history = [
#     {'from': '2018-01-01', 'to': '2020-01-01'},
#     {'from': '2020-02-01', 'to': '2021-02-01'},
#     {'from': '2021-03-01', 'to': '2022-03-01'},
#     # Add more employment history as needed
# ]

# job_durations = calculate_job_durations(employment_history)
# stability_score = calculate_stability(job_durations)
# print(f"Stability Score: {stability_score}")