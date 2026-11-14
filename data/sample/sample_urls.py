"""
Sample browsing session dataset for simulation, unit testing, and demonstration.
Each record follows the schema: (user_id, url, time_spent_in_seconds, user_email).
"""

SAMPLE_BROWSING_ACTIVITY = [
    (101, "https://www.github.com", 400, "student101@university.edu"),
    (102, "https://www.instagram.com", 600, "student102@university.edu"),
    (102, "https://www.youtube.com/wwe", 350, "student102@university.edu"),
    (101, "https://www.youtube.com/freecodecamp", 800, "student101@university.edu"),
    (102, "https://www.youtube.com/@bbkivines", 1000, "student102@university.edu"),
    (101, "https://www.geeksforgeeks.org/", 350, "student101@university.edu"),
    (102, "https://ums.lpu.in", 200, "student102@university.edu"),
    (103, "https://ome.tv/", 450, "student103@university.edu"),
    (103, "https://en.wikipedia.org/wiki/Textile", 450, "student103@university.edu"),
    (103, "https://web.whatsapp.com/", 450, "student103@university.edu"),
    (104, "https://www.leetcode.com", 350, "student104@university.edu"),
    (104, "https://stackoverflow.com", 500, "student104@university.edu"),
]

# Backward compatibility aliases
USER_DATA = SAMPLE_BROWSING_ACTIVITY
URL_LIST = SAMPLE_BROWSING_ACTIVITY
