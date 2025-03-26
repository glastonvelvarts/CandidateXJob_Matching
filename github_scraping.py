# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# import time

# def scrape_github_repositories(username):
#     CHROMEDRIVER_PATH = "C:/Users/glast/OneDrive/Desktop/chromedriver.exe"
    
#     options = Options()
#     options.add_argument("--headless")
    
#     service = Service(CHROMEDRIVER_PATH)
#     driver = webdriver.Chrome(service=service, options=options)
    
#     base_url = f"https://github.com/{username}?tab=repositories"
#     driver.get(base_url)
#     time.sleep(3)
    
#     repositories = []
#     repo_elements = driver.find_elements(By.XPATH, "//h3[@class='wb-break-all']/a")
    
#     for repo in repo_elements:
#         repo_name = repo.text.strip()
#         repo_url = repo.get_attribute("href")
        
#         driver.get(repo_url)
#         time.sleep(2)
        
#         # Extract topics/tags
#         topics = driver.find_elements(By.XPATH, "//a[@class='topic-tag topic-tag-link']")
#         skills = [topic.text.strip() for topic in topics]
        
#         # Extract primary language
#         lang_element = driver.find_elements(By.XPATH, "//span[@class='color-fg-default text-bold mr-1']")
#         primary_language = lang_element[0].text.strip() if lang_element else "Unknown"
        
#         repositories.append({"name": repo_name, "url": repo_url, "skills": skills, "primary_language": primary_language})
    
#     driver.quit()
#     return repositories

# if __name__ == "__main__":
#     username = "glastonvelvarts"
#     projects = scrape_github_repositories(username)
    
#     if projects:
#         print("GitHub Projects:")
#         for project in projects:
#             print(f"- {project['name']} ({project['primary_language']}): {project['url']}")
#             print(f"  Skills: {', '.join(project['skills']) if project['skills'] else 'No specific skills listed'}")
#     else:
#         print("No repositories found.")