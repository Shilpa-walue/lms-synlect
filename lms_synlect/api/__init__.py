# LMS Synlect API Module
# This module contains API endpoints for React frontend integration
#
# Available APIs:
#
# Authentication (lms_synlect.api.auth):
#   - login: POST /api/method/lms_synlect.api.auth.login
#   - register: POST /api/method/lms_synlect.api.auth.register
#   - logout: POST /api/method/lms_synlect.api.auth.logout
#   - me: GET /api/method/lms_synlect.api.auth.me
#   - refresh_token: POST /api/method/lms_synlect.api.auth.refresh_token
#   - forgot_password: POST /api/method/lms_synlect.api.auth.forgot_password
#   - change_password: POST /api/method/lms_synlect.api.auth.change_password
#
# Courses (lms_synlect.api.course):
#   - get_courses: GET /api/method/lms_synlect.api.course.get_courses
#   - get_course: GET /api/method/lms_synlect.api.course.get_course
#   - get_featured_courses: GET /api/method/lms_synlect.api.course.get_featured_courses
#   - get_categories: GET /api/method/lms_synlect.api.course.get_categories
#   - get_instructors: GET /api/method/lms_synlect.api.course.get_instructors
#   - get_course_curriculum: GET /api/method/lms_synlect.api.course.get_course_curriculum
