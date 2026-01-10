"""
Course API for DreamsLMS React Frontend Integration
Provides course listing, filtering, and course details endpoints
"""

import frappe
from frappe import _
import json
from frappe.utils import cint, flt


def get_course_image(course_doc):
    """Get the course image URL"""
    if hasattr(course_doc, 'image') and course_doc.image:
        return course_doc.image
    if hasattr(course_doc, 'hero_image') and course_doc.hero_image:
        return course_doc.hero_image
    return ""


def get_course_instructor(course_doc):
    """Get instructor details for a course"""
    instructor_name = ""
    instructor_id = ""
    instructor_avatar = ""

    # Frappe LMS uses 'owner' or specific instructor field
    if hasattr(course_doc, 'instructor') and course_doc.instructor:
        instructor_id = course_doc.instructor
    else:
        instructor_id = course_doc.owner

    if instructor_id:
        user = frappe.get_doc("User", instructor_id)
        instructor_name = user.full_name or instructor_id
        instructor_avatar = user.user_image or ""

    return {
        "id": instructor_id,
        "name": instructor_name,
        "avatar": instructor_avatar
    }


def get_course_stats(course_name):
    """Get course statistics like enrollments, lessons count"""
    # Count enrolled students
    student_count = frappe.db.count(
        "LMS Enrollment",
        filters={"course": course_name}
    ) or 0

    # Count lessons/chapters
    lesson_count = 0
    if frappe.db.exists("DocType", "Course Chapter"):
        chapters = frappe.get_all(
            "Course Chapter",
            filters={"course": course_name},
            fields=["name"]
        )
        for chapter in chapters:
            lessons = frappe.db.count(
                "Course Lesson",
                filters={"chapter": chapter.name}
            ) or 0
            lesson_count += lessons

    # If no chapters, try direct lessons count
    if lesson_count == 0 and frappe.db.exists("DocType", "Course Lesson"):
        lesson_count = frappe.db.count(
            "Course Lesson",
            filters={"course": course_name}
        ) or 0

    return {
        "students": student_count,
        "lessons": lesson_count
    }


def get_course_rating(course_name):
    """Get average course rating and review count"""
    rating = 0
    review_count = 0

    # Check if course review doctype exists
    if frappe.db.exists("DocType", "LMS Course Review"):
        reviews = frappe.get_all(
            "LMS Course Review",
            filters={"course": course_name},
            fields=["rating"]
        )
        if reviews:
            review_count = len(reviews)
            total_rating = sum([r.rating for r in reviews])
            rating = round(total_rating / review_count, 1)

    return {
        "rating": rating,
        "reviewCount": review_count
    }


def format_course_for_frontend(course_doc):
    """Format a course document for the React frontend"""
    course_name = course_doc.name if hasattr(course_doc, 'name') else course_doc.get('name')

    # Get stats
    stats = get_course_stats(course_name)
    rating_info = get_course_rating(course_name)

    # Get price info
    price = 0
    original_price = 0
    is_free = True

    if hasattr(course_doc, 'paid'):
        is_free = not course_doc.paid
    if hasattr(course_doc, 'course_price'):
        price = flt(course_doc.course_price) or 0
        is_free = price == 0
    if hasattr(course_doc, 'price'):
        price = flt(course_doc.price) or 0
        is_free = price == 0

    original_price = price  # Can be modified if discount field exists

    # Get category
    category = ""
    if hasattr(course_doc, 'category') and course_doc.category:
        category = course_doc.category

    # Get level/difficulty
    level = "Basic"
    if hasattr(course_doc, 'level') and course_doc.level:
        level = course_doc.level
    elif hasattr(course_doc, 'difficulty') and course_doc.difficulty:
        level = course_doc.difficulty

    # Get duration
    duration = ""
    if hasattr(course_doc, 'video_link'):
        duration = "Self-paced"
    if hasattr(course_doc, 'duration') and course_doc.duration:
        duration = course_doc.duration

    # Check if featured
    is_featured = False
    if hasattr(course_doc, 'featured'):
        is_featured = bool(course_doc.featured)
    if hasattr(course_doc, 'is_featured'):
        is_featured = bool(course_doc.is_featured)

    # Get instructor info
    instructor = get_course_instructor(course_doc)

    return {
        "id": course_name,
        "title": course_doc.title if hasattr(course_doc, 'title') else course_name,
        "slug": course_doc.name.lower().replace(" ", "-"),
        "description": course_doc.short_introduction if hasattr(course_doc, 'short_introduction') else (course_doc.description if hasattr(course_doc, 'description') else ""),
        "image": get_course_image(course_doc),
        "instructor": instructor,
        "category": category,
        "price": price,
        "originalPrice": original_price,
        "rating": rating_info["rating"],
        "reviewCount": rating_info["reviewCount"],
        "level": level,
        "duration": duration,
        "lessons": stats["lessons"],
        "students": stats["students"],
        "isFree": is_free,
        "isFeatured": is_featured,
        "createdAt": str(course_doc.creation) if hasattr(course_doc, 'creation') else "",
        "published": course_doc.published if hasattr(course_doc, 'published') else True
    }


@frappe.whitelist(allow_guest=True)
def get_courses(
    category=None,
    level=None,
    instructor=None,
    price_type=None,
    min_price=None,
    max_price=None,
    rating=None,
    search=None,
    sort_by=None,
    page=1,
    page_size=10
):
    """
    Get list of courses with filtering and pagination

    Args:
        category: Filter by category name
        level: Filter by level (Basic, Intermediate, Advanced)
        instructor: Filter by instructor name
        price_type: Filter by price type ('all', 'free', 'paid')
        min_price: Minimum price filter
        max_price: Maximum price filter
        rating: Minimum rating filter
        search: Search in title, description, instructor
        sort_by: Sort option ('newest', 'popular', 'rating', 'price_low', 'price_high')
        page: Page number (default: 1)
        page_size: Items per page (default: 10)

    Returns:
        {
            "success": bool,
            "courses": Array of course objects,
            "totalCount": Total matching courses,
            "pageSize": Items per page,
            "currentPage": Current page number,
            "totalPages": Total pages
        }
    """
    try:
        # Parse JSON if data comes as request body
        if frappe.request.data:
            try:
                data = json.loads(frappe.request.data)
                category = data.get("category", category)
                level = data.get("level", level)
                instructor = data.get("instructor", instructor)
                price_type = data.get("priceType", price_type)
                min_price = data.get("minPrice", min_price)
                max_price = data.get("maxPrice", max_price)
                rating = data.get("rating", rating)
                search = data.get("search", search)
                sort_by = data.get("sortBy", sort_by)
                page = data.get("page", page)
                page_size = data.get("pageSize", page_size)
            except json.JSONDecodeError:
                pass

        # Parse URL parameters
        page = cint(page) or 1
        page_size = cint(page_size) or 10

        # Check if LMS Course doctype exists
        if not frappe.db.exists("DocType", "LMS Course"):
            return {
                "success": False,
                "message": _("LMS Course doctype not found. Please ensure Frappe LMS is installed.")
            }

        # Build filters
        filters = {}

        # Only show published courses
        if frappe.db.has_column("LMS Course", "published"):
            filters["published"] = 1

        # Category filter
        if category:
            if frappe.db.has_column("LMS Course", "category"):
                filters["category"] = category

        # Level filter
        if level:
            level_field = None
            if frappe.db.has_column("LMS Course", "level"):
                level_field = "level"
            elif frappe.db.has_column("LMS Course", "difficulty"):
                level_field = "difficulty"

            if level_field:
                filters[level_field] = level

        # Price type filter
        if price_type:
            if price_type == "free":
                if frappe.db.has_column("LMS Course", "paid"):
                    filters["paid"] = 0
            elif price_type == "paid":
                if frappe.db.has_column("LMS Course", "paid"):
                    filters["paid"] = 1

        # Instructor filter
        if instructor:
            if frappe.db.has_column("LMS Course", "instructor"):
                filters["instructor"] = ["like", f"%{instructor}%"]
            else:
                filters["owner"] = ["like", f"%{instructor}%"]

        # Determine sort order
        order_by = "creation desc"  # Default: newest first
        if sort_by == "newest":
            order_by = "creation desc"
        elif sort_by == "popular":
            order_by = "creation desc"  # Will sort by enrollment count later
        elif sort_by == "rating":
            order_by = "creation desc"  # Will sort by rating later
        elif sort_by == "price_low":
            if frappe.db.has_column("LMS Course", "course_price"):
                order_by = "course_price asc"
        elif sort_by == "price_high":
            if frappe.db.has_column("LMS Course", "course_price"):
                order_by = "course_price desc"

        # Get all courses with filters
        all_courses = frappe.get_all(
            "LMS Course",
            filters=filters,
            fields=["*"],
            order_by=order_by
        )

        # Apply search filter
        if search:
            search_lower = search.lower()
            filtered_courses = []
            for course in all_courses:
                title = (course.title or "").lower()
                description = (course.short_introduction or course.description or "").lower()
                owner = (course.owner or "").lower()

                if search_lower in title or search_lower in description or search_lower in owner:
                    filtered_courses.append(course)
            all_courses = filtered_courses

        # Apply price range filter
        if min_price is not None or max_price is not None:
            min_p = flt(min_price) if min_price else 0
            max_p = flt(max_price) if max_price else float('inf')

            filtered_courses = []
            for course in all_courses:
                price = flt(course.get("course_price") or course.get("price") or 0)
                if min_p <= price <= max_p:
                    filtered_courses.append(course)
            all_courses = filtered_courses

        # Format courses for frontend
        formatted_courses = []
        for course in all_courses:
            # Create a simple namespace object for compatibility
            class CourseDoc:
                pass
            course_obj = CourseDoc()
            for key, value in course.items():
                setattr(course_obj, key, value)

            formatted = format_course_for_frontend(course_obj)
            formatted_courses.append(formatted)

        # Apply rating filter
        if rating:
            min_rating = flt(rating)
            formatted_courses = [c for c in formatted_courses if c["rating"] >= min_rating]

        # Sort by popularity (student count) or rating if requested
        if sort_by == "popular":
            formatted_courses.sort(key=lambda x: x["students"], reverse=True)
        elif sort_by == "rating":
            formatted_courses.sort(key=lambda x: x["rating"], reverse=True)

        # Calculate pagination
        total_count = len(formatted_courses)
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_courses = formatted_courses[start_idx:end_idx]

        return {
            "success": True,
            "courses": paginated_courses,
            "totalCount": total_count,
            "pageSize": page_size,
            "currentPage": page,
            "totalPages": total_pages
        }

    except Exception as e:
        frappe.log_error(f"Get courses error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": str(e) if frappe.conf.developer_mode else _("An error occurred while fetching courses"),
            "courses": [],
            "totalCount": 0,
            "pageSize": page_size,
            "currentPage": page,
            "totalPages": 0
        }


@frappe.whitelist(allow_guest=True)
def get_course(course_id=None, slug=None):
    """
    Get a single course by ID or slug

    Args:
        course_id: Course document name/ID
        slug: Course slug

    Returns:
        {
            "success": bool,
            "course": Course object
        }
    """
    try:
        if not course_id and not slug:
            return {
                "success": False,
                "message": _("Course ID or slug is required")
            }

        course_name = course_id

        # If slug provided, find by slug (name in Frappe)
        if slug and not course_id:
            # Try to find course by name that matches slug pattern
            courses = frappe.get_all(
                "LMS Course",
                filters={},
                fields=["name"]
            )
            for c in courses:
                if c.name.lower().replace(" ", "-") == slug.lower():
                    course_name = c.name
                    break

        if not course_name or not frappe.db.exists("LMS Course", course_name):
            return {
                "success": False,
                "message": _("Course not found")
            }

        course_doc = frappe.get_doc("LMS Course", course_name)
        formatted_course = format_course_for_frontend(course_doc)

        # Add additional details for single course view
        formatted_course["fullDescription"] = course_doc.description if hasattr(course_doc, 'description') else ""

        return {
            "success": True,
            "course": formatted_course
        }

    except Exception as e:
        frappe.log_error(f"Get course error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while fetching course details")
        }


@frappe.whitelist(allow_guest=True)
def get_featured_courses(limit=6):
    """
    Get featured courses

    Args:
        limit: Maximum number of courses to return

    Returns:
        {
            "success": bool,
            "courses": Array of featured course objects
        }
    """
    try:
        limit = cint(limit) or 6

        # Check for featured field
        filters = {}
        if frappe.db.has_column("LMS Course", "featured"):
            filters["featured"] = 1
        elif frappe.db.has_column("LMS Course", "is_featured"):
            filters["is_featured"] = 1

        if frappe.db.has_column("LMS Course", "published"):
            filters["published"] = 1

        courses = frappe.get_all(
            "LMS Course",
            filters=filters,
            fields=["*"],
            limit=limit,
            order_by="creation desc"
        )

        # If no featured courses found, return newest courses
        if not courses:
            filters = {}
            if frappe.db.has_column("LMS Course", "published"):
                filters["published"] = 1

            courses = frappe.get_all(
                "LMS Course",
                filters=filters,
                fields=["*"],
                limit=limit,
                order_by="creation desc"
            )

        formatted_courses = []
        for course in courses:
            class CourseDoc:
                pass
            course_obj = CourseDoc()
            for key, value in course.items():
                setattr(course_obj, key, value)

            formatted = format_course_for_frontend(course_obj)
            formatted_courses.append(formatted)

        return {
            "success": True,
            "courses": formatted_courses
        }

    except Exception as e:
        frappe.log_error(f"Get featured courses error: {str(e)}", "Course API")
        return {
            "success": False,
            "courses": [],
            "message": _("An error occurred while fetching featured courses")
        }


@frappe.whitelist(allow_guest=True)
def get_categories():
    """
    Get all course categories

    Returns:
        {
            "success": bool,
            "categories": Array of category names
        }
    """
    try:
        categories = []

        # Check if LMS Category doctype exists
        if frappe.db.exists("DocType", "LMS Category"):
            cat_docs = frappe.get_all(
                "LMS Category",
                fields=["name", "category_name", "title"],
                order_by="name"
            )
            for cat in cat_docs:
                categories.append(cat.category_name or cat.title or cat.name)
        else:
            # Get unique categories from courses
            if frappe.db.has_column("LMS Course", "category"):
                course_categories = frappe.get_all(
                    "LMS Course",
                    fields=["category"],
                    distinct=True
                )
                categories = list(set([c.category for c in course_categories if c.category]))

        return {
            "success": True,
            "categories": categories
        }

    except Exception as e:
        frappe.log_error(f"Get categories error: {str(e)}", "Course API")
        return {
            "success": False,
            "categories": [],
            "message": _("An error occurred while fetching categories")
        }


@frappe.whitelist(allow_guest=True)
def get_instructors():
    """
    Get list of instructors

    Returns:
        {
            "success": bool,
            "instructors": Array of instructor objects
        }
    """
    try:
        # Get unique course owners/instructors
        courses = frappe.get_all(
            "LMS Course",
            fields=["owner", "instructor"] if frappe.db.has_column("LMS Course", "instructor") else ["owner"],
            distinct=True
        )

        instructor_ids = set()
        for course in courses:
            if hasattr(course, 'instructor') and course.instructor:
                instructor_ids.add(course.instructor)
            else:
                instructor_ids.add(course.owner)

        instructors = []
        for instructor_id in instructor_ids:
            if instructor_id and frappe.db.exists("User", instructor_id):
                user = frappe.get_doc("User", instructor_id)
                instructors.append({
                    "id": instructor_id,
                    "name": user.full_name or instructor_id,
                    "avatar": user.user_image or ""
                })

        return {
            "success": True,
            "instructors": instructors
        }

    except Exception as e:
        frappe.log_error(f"Get instructors error: {str(e)}", "Course API")
        return {
            "success": False,
            "instructors": [],
            "message": _("An error occurred while fetching instructors")
        }


@frappe.whitelist(allow_guest=True)
def get_course_curriculum(course_id):
    """
    Get course curriculum (chapters and lessons)

    Args:
        course_id: Course document name/ID

    Returns:
        {
            "success": bool,
            "curriculum": Array of chapter objects with lessons
        }
    """
    try:
        if not course_id:
            return {
                "success": False,
                "message": _("Course ID is required")
            }

        if not frappe.db.exists("LMS Course", course_id):
            return {
                "success": False,
                "message": _("Course not found")
            }

        curriculum = []

        # Get chapters
        if frappe.db.exists("DocType", "Course Chapter"):
            chapters = frappe.get_all(
                "Course Chapter",
                filters={"course": course_id},
                fields=["name", "title", "description", "idx"],
                order_by="idx"
            )

            for chapter in chapters:
                lessons = []

                # Get lessons for this chapter
                if frappe.db.exists("DocType", "Course Lesson"):
                    lesson_docs = frappe.get_all(
                        "Course Lesson",
                        filters={"chapter": chapter.name},
                        fields=["name", "title", "include_in_preview", "idx"],
                        order_by="idx"
                    )

                    for lesson in lesson_docs:
                        lessons.append({
                            "id": lesson.name,
                            "title": lesson.title,
                            "isPreview": bool(lesson.include_in_preview) if hasattr(lesson, 'include_in_preview') else False,
                            "order": lesson.idx
                        })

                curriculum.append({
                    "id": chapter.name,
                    "title": chapter.title,
                    "description": chapter.description or "",
                    "order": chapter.idx,
                    "lessons": lessons
                })

        return {
            "success": True,
            "curriculum": curriculum
        }

    except Exception as e:
        frappe.log_error(f"Get curriculum error: {str(e)}", "Course API")
        return {
            "success": False,
            "curriculum": [],
            "message": _("An error occurred while fetching curriculum")
        }
