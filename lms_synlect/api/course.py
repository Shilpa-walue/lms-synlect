"""
Course API for DreamsLMS React Frontend Integration
Provides course listing, filtering, and course details endpoints
"""

import frappe
from frappe import _
import json
from frappe.utils import cint, flt


def get_course_image(course_doc):
    """Get the course image URL - returns full URL for Frappe Cloud"""
    image_path = None

    # Check various possible image field names in Frappe LMS
    if hasattr(course_doc, 'image') and course_doc.image:
        image_path = course_doc.image
    elif hasattr(course_doc, 'hero_image') and course_doc.hero_image:
        image_path = course_doc.hero_image
    elif hasattr(course_doc, 'course_image') and course_doc.course_image:
        image_path = course_doc.course_image

    if not image_path:
        return ""

    # If already a full URL, return as-is
    if image_path.startswith('http://') or image_path.startswith('https://'):
        return image_path

    # Return the path as-is (frontend will add the base URL)
    return image_path


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


# ==================== COURSE CREATION API ====================

@frappe.whitelist()
def create_course(
    title=None,
    description=None,
    short_introduction=None,
    category=None,
    level=None,
    price=None,
    duration=None,
    image=None,
    is_featured=False,
    chapters=None
):
    """
    Create a new course with optional chapters and lessons

    Args:
        title: Course title (required)
        description: Full course description
        short_introduction: Short intro for cards
        category: Course category
        level: Course level (Basic, Intermediate, Advanced)
        price: Course price (0 for free)
        duration: Course duration string
        image: Course image path
        is_featured: Whether course is featured
        chapters: JSON array of chapters with lessons
            [{"title": "Chapter 1", "description": "...", "lessons": [{"title": "Lesson 1", "content": "..."}]}]

    Returns:
        {
            "success": bool,
            "course_id": Course document name,
            "message": Status message
        }
    """
    try:
        # Validate required fields
        if not title:
            return {
                "success": False,
                "message": _("Course title is required")
            }

        # Get current user as instructor
        current_user = frappe.session.user
        if current_user == "Guest":
            return {
                "success": False,
                "message": _("Authentication required to create courses")
            }

        # Parse chapters if provided as JSON string
        if chapters and isinstance(chapters, str):
            try:
                chapters = json.loads(chapters)
            except json.JSONDecodeError:
                chapters = None

        # Create course document
        course_doc = frappe.new_doc("LMS Course")
        course_doc.title = title
        course_doc.owner = current_user

        # Set optional fields if they exist
        if description and hasattr(course_doc, 'description'):
            course_doc.description = description
        if short_introduction and hasattr(course_doc, 'short_introduction'):
            course_doc.short_introduction = short_introduction
        if category and hasattr(course_doc, 'category'):
            course_doc.category = category
        if level:
            if hasattr(course_doc, 'level'):
                course_doc.level = level
            elif hasattr(course_doc, 'difficulty'):
                course_doc.difficulty = level
        if price is not None:
            if hasattr(course_doc, 'course_price'):
                course_doc.course_price = flt(price)
            if hasattr(course_doc, 'price'):
                course_doc.price = flt(price)
            if hasattr(course_doc, 'paid'):
                course_doc.paid = 1 if flt(price) > 0 else 0
        if duration and hasattr(course_doc, 'duration'):
            course_doc.duration = duration
        if image and hasattr(course_doc, 'image'):
            course_doc.image = image
        if is_featured:
            if hasattr(course_doc, 'featured'):
                course_doc.featured = 1
            elif hasattr(course_doc, 'is_featured'):
                course_doc.is_featured = 1

        # Set instructor field if exists
        if hasattr(course_doc, 'instructor'):
            course_doc.instructor = current_user

        # Set published to true by default
        if hasattr(course_doc, 'published'):
            course_doc.published = 1

        course_doc.insert()
        course_name = course_doc.name

        # Create chapters and lessons if provided
        if chapters and isinstance(chapters, list):
            for idx, chapter_data in enumerate(chapters, 1):
                if frappe.db.exists("DocType", "Course Chapter"):
                    chapter_doc = frappe.new_doc("Course Chapter")
                    chapter_doc.course = course_name
                    chapter_doc.title = chapter_data.get("title", f"Chapter {idx}")
                    if hasattr(chapter_doc, 'description'):
                        chapter_doc.description = chapter_data.get("description", "")
                    chapter_doc.idx = idx
                    chapter_doc.insert()

                    # Create lessons for this chapter
                    lessons = chapter_data.get("lessons", [])
                    for lesson_idx, lesson_data in enumerate(lessons, 1):
                        if frappe.db.exists("DocType", "Course Lesson"):
                            lesson_doc = frappe.new_doc("Course Lesson")
                            lesson_doc.chapter = chapter_doc.name
                            lesson_doc.title = lesson_data.get("title", f"Lesson {lesson_idx}")
                            if hasattr(lesson_doc, 'content'):
                                lesson_doc.content = lesson_data.get("content", "")
                            if hasattr(lesson_doc, 'course'):
                                lesson_doc.course = course_name
                            if hasattr(lesson_doc, 'include_in_preview'):
                                lesson_doc.include_in_preview = lesson_data.get("isPreview", 0)
                            if hasattr(lesson_doc, 'video_url'):
                                lesson_doc.video_url = lesson_data.get("videoUrl", "")
                            lesson_doc.idx = lesson_idx
                            lesson_doc.insert()

        frappe.db.commit()

        return {
            "success": True,
            "course_id": course_name,
            "message": _("Course created successfully")
        }

    except Exception as e:
        frappe.log_error(f"Create course error: {str(e)}", "Course API")
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e) if frappe.conf.developer_mode else _("An error occurred while creating the course")
        }


@frappe.whitelist()
def update_course(
    course_id=None,
    title=None,
    description=None,
    short_introduction=None,
    category=None,
    level=None,
    price=None,
    duration=None,
    image=None,
    is_featured=None,
    published=None
):
    """
    Update an existing course

    Args:
        course_id: Course document name (required)
        Other args: Fields to update

    Returns:
        {
            "success": bool,
            "message": Status message
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

        current_user = frappe.session.user
        course_doc = frappe.get_doc("LMS Course", course_id)

        # Check if user owns the course or is admin
        is_owner = course_doc.owner == current_user
        is_instructor = hasattr(course_doc, 'instructor') and course_doc.instructor == current_user
        is_admin = "System Manager" in frappe.get_roles(current_user)

        if not (is_owner or is_instructor or is_admin):
            return {
                "success": False,
                "message": _("You don't have permission to update this course")
            }

        # Update fields
        if title:
            course_doc.title = title
        if description and hasattr(course_doc, 'description'):
            course_doc.description = description
        if short_introduction and hasattr(course_doc, 'short_introduction'):
            course_doc.short_introduction = short_introduction
        if category and hasattr(course_doc, 'category'):
            course_doc.category = category
        if level:
            if hasattr(course_doc, 'level'):
                course_doc.level = level
            elif hasattr(course_doc, 'difficulty'):
                course_doc.difficulty = level
        if price is not None:
            if hasattr(course_doc, 'course_price'):
                course_doc.course_price = flt(price)
            if hasattr(course_doc, 'price'):
                course_doc.price = flt(price)
            if hasattr(course_doc, 'paid'):
                course_doc.paid = 1 if flt(price) > 0 else 0
        if duration and hasattr(course_doc, 'duration'):
            course_doc.duration = duration
        if image and hasattr(course_doc, 'image'):
            course_doc.image = image
        if is_featured is not None:
            if hasattr(course_doc, 'featured'):
                course_doc.featured = 1 if is_featured else 0
            elif hasattr(course_doc, 'is_featured'):
                course_doc.is_featured = 1 if is_featured else 0
        if published is not None and hasattr(course_doc, 'published'):
            course_doc.published = 1 if published else 0

        course_doc.save()
        frappe.db.commit()

        return {
            "success": True,
            "message": _("Course updated successfully")
        }

    except Exception as e:
        frappe.log_error(f"Update course error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": str(e) if frappe.conf.developer_mode else _("An error occurred while updating the course")
        }


# ==================== LESSON DETAILS API ====================

@frappe.whitelist(allow_guest=True)
def get_lesson_details(lesson_id=None, course_id=None):
    """
    Get detailed lesson content

    Args:
        lesson_id: Lesson document name
        course_id: Course ID (to verify access)

    Returns:
        {
            "success": bool,
            "lesson": Lesson object with content
        }
    """
    try:
        if not lesson_id:
            return {
                "success": False,
                "message": _("Lesson ID is required")
            }

        if not frappe.db.exists("DocType", "Course Lesson"):
            return {
                "success": False,
                "message": _("Course Lesson doctype not found")
            }

        if not frappe.db.exists("Course Lesson", lesson_id):
            return {
                "success": False,
                "message": _("Lesson not found")
            }

        lesson_doc = frappe.get_doc("Course Lesson", lesson_id)
        current_user = frappe.session.user

        # Check if this is a preview lesson or user has access
        is_preview = bool(lesson_doc.include_in_preview) if hasattr(lesson_doc, 'include_in_preview') else False
        is_guest = current_user == "Guest"

        # Get course info for enrollment check
        course_name = None
        if hasattr(lesson_doc, 'course') and lesson_doc.course:
            course_name = lesson_doc.course
        elif hasattr(lesson_doc, 'chapter') and lesson_doc.chapter:
            chapter = frappe.get_doc("Course Chapter", lesson_doc.chapter)
            course_name = chapter.course if hasattr(chapter, 'course') else None

        # Check enrollment if not preview and not guest
        has_access = is_preview
        if not is_guest and course_name:
            if frappe.db.exists("LMS Enrollment", {"course": course_name, "member": current_user}):
                has_access = True
            # Check if user is the course owner
            if frappe.db.exists("LMS Course", course_name):
                course_doc = frappe.get_doc("LMS Course", course_name)
                if course_doc.owner == current_user:
                    has_access = True
                if hasattr(course_doc, 'instructor') and course_doc.instructor == current_user:
                    has_access = True

        # Return limited info for non-enrolled users on non-preview lessons
        lesson_data = {
            "id": lesson_doc.name,
            "title": lesson_doc.title,
            "isPreview": is_preview,
            "order": lesson_doc.idx if hasattr(lesson_doc, 'idx') else 0,
            "chapterId": lesson_doc.chapter if hasattr(lesson_doc, 'chapter') else None,
            "courseId": course_name
        }

        if has_access:
            # Include full content for enrolled users or preview lessons
            lesson_data["content"] = lesson_doc.content if hasattr(lesson_doc, 'content') else ""
            lesson_data["videoUrl"] = lesson_doc.video_url if hasattr(lesson_doc, 'video_url') else ""
            lesson_data["duration"] = lesson_doc.duration if hasattr(lesson_doc, 'duration') else ""
            lesson_data["youtubeVideoId"] = lesson_doc.youtube_video_id if hasattr(lesson_doc, 'youtube_video_id') else ""
            lesson_data["quizId"] = lesson_doc.quiz_id if hasattr(lesson_doc, 'quiz_id') else None
        else:
            lesson_data["requiresEnrollment"] = True

        return {
            "success": True,
            "lesson": lesson_data,
            "hasAccess": has_access
        }

    except Exception as e:
        frappe.log_error(f"Get lesson details error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while fetching lesson details")
        }


@frappe.whitelist(allow_guest=True)
def get_chapter_lessons(chapter_id=None):
    """
    Get all lessons for a chapter with details

    Args:
        chapter_id: Chapter document name

    Returns:
        {
            "success": bool,
            "lessons": Array of lesson objects
        }
    """
    try:
        if not chapter_id:
            return {
                "success": False,
                "message": _("Chapter ID is required")
            }

        if not frappe.db.exists("DocType", "Course Chapter"):
            return {
                "success": False,
                "message": _("Course Chapter doctype not found")
            }

        if not frappe.db.exists("Course Chapter", chapter_id):
            return {
                "success": False,
                "message": _("Chapter not found")
            }

        chapter_doc = frappe.get_doc("Course Chapter", chapter_id)
        current_user = frappe.session.user
        is_guest = current_user == "Guest"

        # Check enrollment
        course_name = chapter_doc.course if hasattr(chapter_doc, 'course') else None
        has_access = False

        if not is_guest and course_name:
            if frappe.db.exists("LMS Enrollment", {"course": course_name, "member": current_user}):
                has_access = True
            if frappe.db.exists("LMS Course", course_name):
                course_doc = frappe.get_doc("LMS Course", course_name)
                if course_doc.owner == current_user:
                    has_access = True
                if hasattr(course_doc, 'instructor') and course_doc.instructor == current_user:
                    has_access = True

        lessons = []
        if frappe.db.exists("DocType", "Course Lesson"):
            lesson_docs = frappe.get_all(
                "Course Lesson",
                filters={"chapter": chapter_id},
                fields=["*"],
                order_by="idx"
            )

            for lesson in lesson_docs:
                is_preview = bool(lesson.get("include_in_preview", 0))

                lesson_data = {
                    "id": lesson.name,
                    "title": lesson.title,
                    "isPreview": is_preview,
                    "order": lesson.idx or 0,
                    "duration": lesson.get("duration", "")
                }

                # Include content for enrolled users or preview lessons
                if has_access or is_preview:
                    lesson_data["content"] = lesson.get("content", "")
                    lesson_data["videoUrl"] = lesson.get("video_url", "")
                    lesson_data["youtubeVideoId"] = lesson.get("youtube_video_id", "")
                else:
                    lesson_data["requiresEnrollment"] = True

                lessons.append(lesson_data)

        return {
            "success": True,
            "lessons": lessons,
            "chapter": {
                "id": chapter_doc.name,
                "title": chapter_doc.title,
                "description": chapter_doc.description if hasattr(chapter_doc, 'description') else "",
                "courseId": course_name
            },
            "hasAccess": has_access
        }

    except Exception as e:
        frappe.log_error(f"Get chapter lessons error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while fetching chapter lessons")
        }


# ==================== COURSE PROGRESS API ====================

@frappe.whitelist()
def save_progress(
    course_id=None,
    lesson_id=None,
    chapter_id=None,
    progress_percent=None,
    is_completed=False,
    video_position=None,
    notes=None
):
    """
    Save or update course/lesson progress for a user

    Args:
        course_id: Course document name (required)
        lesson_id: Lesson document name (optional)
        chapter_id: Chapter document name (optional)
        progress_percent: Progress percentage (0-100)
        is_completed: Whether the item is completed
        video_position: Current video position in seconds
        notes: User notes for the lesson

    Returns:
        {
            "success": bool,
            "message": Status message
        }
    """
    try:
        current_user = frappe.session.user
        if current_user == "Guest":
            return {
                "success": False,
                "message": _("Authentication required to save progress")
            }

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

        # Check if LMS Course Progress doctype exists, create if not
        progress_doctype = "LMS Course Progress"
        if not frappe.db.exists("DocType", progress_doctype):
            # Try alternative doctypes
            if frappe.db.exists("DocType", "Course Progress"):
                progress_doctype = "Course Progress"
            else:
                # Create a simple progress tracking using custom doctype or cache
                # For now, use cache-based progress tracking
                cache_key = f"course_progress:{current_user}:{course_id}"
                if lesson_id:
                    cache_key = f"lesson_progress:{current_user}:{lesson_id}"

                progress_data = {
                    "user": current_user,
                    "course_id": course_id,
                    "lesson_id": lesson_id,
                    "chapter_id": chapter_id,
                    "progress_percent": flt(progress_percent) if progress_percent else 0,
                    "is_completed": bool(is_completed),
                    "video_position": cint(video_position) if video_position else 0,
                    "notes": notes or "",
                    "updated_at": frappe.utils.now()
                }

                frappe.cache().set_value(cache_key, json.dumps(progress_data), expires_in_sec=86400 * 365)  # 1 year

                return {
                    "success": True,
                    "message": _("Progress saved successfully")
                }

        # Use doctype-based progress tracking
        filters = {"course": course_id, "member": current_user}
        if lesson_id:
            filters["lesson"] = lesson_id

        existing = frappe.get_all(progress_doctype, filters=filters, limit=1)

        if existing:
            progress_doc = frappe.get_doc(progress_doctype, existing[0].name)
        else:
            progress_doc = frappe.new_doc(progress_doctype)
            progress_doc.course = course_id
            progress_doc.member = current_user
            if lesson_id and hasattr(progress_doc, 'lesson'):
                progress_doc.lesson = lesson_id
            if chapter_id and hasattr(progress_doc, 'chapter'):
                progress_doc.chapter = chapter_id

        # Update progress fields
        if progress_percent is not None and hasattr(progress_doc, 'progress'):
            progress_doc.progress = flt(progress_percent)
        if is_completed and hasattr(progress_doc, 'is_complete'):
            progress_doc.is_complete = 1
        if video_position is not None and hasattr(progress_doc, 'video_position'):
            progress_doc.video_position = cint(video_position)
        if notes and hasattr(progress_doc, 'notes'):
            progress_doc.notes = notes

        progress_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": _("Progress saved successfully")
        }

    except Exception as e:
        frappe.log_error(f"Save progress error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": str(e) if frappe.conf.developer_mode else _("An error occurred while saving progress")
        }


@frappe.whitelist()
def get_progress(course_id=None, lesson_id=None):
    """
    Get course/lesson progress for current user

    Args:
        course_id: Course document name (required)
        lesson_id: Optional lesson ID for specific lesson progress

    Returns:
        {
            "success": bool,
            "progress": Progress object or array of lesson progress
        }
    """
    try:
        current_user = frappe.session.user
        if current_user == "Guest":
            return {
                "success": False,
                "message": _("Authentication required to view progress")
            }

        if not course_id:
            return {
                "success": False,
                "message": _("Course ID is required")
            }

        # Check for progress doctype
        progress_doctype = "LMS Course Progress"
        if not frappe.db.exists("DocType", progress_doctype):
            if frappe.db.exists("DocType", "Course Progress"):
                progress_doctype = "Course Progress"
            else:
                # Use cache-based progress
                if lesson_id:
                    cache_key = f"lesson_progress:{current_user}:{lesson_id}"
                    cached = frappe.cache().get_value(cache_key)
                    if cached:
                        return {
                            "success": True,
                            "progress": json.loads(cached)
                        }
                else:
                    # Get all lesson progress for course
                    course_progress = []
                    if frappe.db.exists("DocType", "Course Chapter"):
                        chapters = frappe.get_all("Course Chapter", filters={"course": course_id}, fields=["name"])
                        for chapter in chapters:
                            if frappe.db.exists("DocType", "Course Lesson"):
                                lessons = frappe.get_all("Course Lesson", filters={"chapter": chapter.name}, fields=["name"])
                                for lesson in lessons:
                                    cache_key = f"lesson_progress:{current_user}:{lesson.name}"
                                    cached = frappe.cache().get_value(cache_key)
                                    if cached:
                                        course_progress.append(json.loads(cached))

                    # Calculate overall progress
                    total_lessons = sum([len(frappe.get_all("Course Lesson", filters={"chapter": c.name}))
                                        for c in frappe.get_all("Course Chapter", filters={"course": course_id})])
                    completed_lessons = len([p for p in course_progress if p.get("is_completed")])
                    overall_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

                    return {
                        "success": True,
                        "progress": {
                            "courseId": course_id,
                            "overallProgress": round(overall_percent, 1),
                            "completedLessons": completed_lessons,
                            "totalLessons": total_lessons,
                            "lessonProgress": course_progress
                        }
                    }

                return {
                    "success": True,
                    "progress": None
                }

        # Use doctype-based progress
        if lesson_id:
            progress = frappe.get_all(
                progress_doctype,
                filters={"course": course_id, "member": current_user, "lesson": lesson_id},
                fields=["*"],
                limit=1
            )
            if progress:
                return {
                    "success": True,
                    "progress": {
                        "lessonId": lesson_id,
                        "progressPercent": progress[0].get("progress", 0),
                        "isCompleted": bool(progress[0].get("is_complete", 0)),
                        "videoPosition": progress[0].get("video_position", 0),
                        "notes": progress[0].get("notes", "")
                    }
                }
        else:
            # Get all progress for course
            all_progress = frappe.get_all(
                progress_doctype,
                filters={"course": course_id, "member": current_user},
                fields=["*"]
            )

            total_lessons = 0
            if frappe.db.exists("DocType", "Course Chapter"):
                chapters = frappe.get_all("Course Chapter", filters={"course": course_id})
                for chapter in chapters:
                    if frappe.db.exists("DocType", "Course Lesson"):
                        total_lessons += frappe.db.count("Course Lesson", {"chapter": chapter.name})

            completed = len([p for p in all_progress if p.get("is_complete")])
            overall = (completed / total_lessons * 100) if total_lessons > 0 else 0

            return {
                "success": True,
                "progress": {
                    "courseId": course_id,
                    "overallProgress": round(overall, 1),
                    "completedLessons": completed,
                    "totalLessons": total_lessons,
                    "lessonProgress": [{
                        "lessonId": p.get("lesson"),
                        "progressPercent": p.get("progress", 0),
                        "isCompleted": bool(p.get("is_complete", 0)),
                        "videoPosition": p.get("video_position", 0)
                    } for p in all_progress]
                }
            }

        return {
            "success": True,
            "progress": None
        }

    except Exception as e:
        frappe.log_error(f"Get progress error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while fetching progress")
        }


@frappe.whitelist()
def mark_lesson_complete(lesson_id=None, course_id=None):
    """
    Mark a lesson as completed

    Args:
        lesson_id: Lesson document name (required)
        course_id: Course document name (optional, will be derived if not provided)

    Returns:
        {
            "success": bool,
            "message": Status message,
            "courseProgress": Updated overall course progress
        }
    """
    try:
        current_user = frappe.session.user
        if current_user == "Guest":
            return {
                "success": False,
                "message": _("Authentication required")
            }

        if not lesson_id:
            return {
                "success": False,
                "message": _("Lesson ID is required")
            }

        # Get course_id from lesson if not provided
        if not course_id:
            if frappe.db.exists("DocType", "Course Lesson"):
                lesson = frappe.get_doc("Course Lesson", lesson_id)
                if hasattr(lesson, 'course') and lesson.course:
                    course_id = lesson.course
                elif hasattr(lesson, 'chapter') and lesson.chapter:
                    chapter = frappe.get_doc("Course Chapter", lesson.chapter)
                    course_id = chapter.course if hasattr(chapter, 'course') else None

        if not course_id:
            return {
                "success": False,
                "message": _("Could not determine course for this lesson")
            }

        # Save progress
        result = save_progress(
            course_id=course_id,
            lesson_id=lesson_id,
            progress_percent=100,
            is_completed=True
        )

        if not result.get("success"):
            return result

        # Get updated course progress
        progress_result = get_progress(course_id=course_id)

        return {
            "success": True,
            "message": _("Lesson marked as complete"),
            "courseProgress": progress_result.get("progress") if progress_result.get("success") else None
        }

    except Exception as e:
        frappe.log_error(f"Mark lesson complete error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while marking lesson complete")
        }


# ==================== LIVE CLASSES API ====================

@frappe.whitelist(allow_guest=True)
def get_live_classes(
    course_id=None,
    instructor_id=None,
    status=None,
    upcoming_only=False,
    page=1,
    page_size=10
):
    """
    Get live classes with optional filtering

    Args:
        course_id: Filter by course
        instructor_id: Filter by instructor
        status: Filter by status (scheduled, live, completed, cancelled)
        upcoming_only: Only return upcoming classes
        page: Page number
        page_size: Items per page

    Returns:
        {
            "success": bool,
            "liveClasses": Array of live class objects,
            "totalCount": Total matching classes
        }
    """
    try:
        page = cint(page) or 1
        page_size = cint(page_size) or 10

        # Check if Live Class doctype exists
        live_class_doctype = "LMS Live Class"
        if not frappe.db.exists("DocType", live_class_doctype):
            if frappe.db.exists("DocType", "Live Class"):
                live_class_doctype = "Live Class"
            else:
                # Return empty if doctype doesn't exist
                return {
                    "success": True,
                    "liveClasses": [],
                    "totalCount": 0,
                    "message": _("Live class feature not configured")
                }

        # Build filters
        filters = {}
        if course_id:
            filters["course"] = course_id
        if instructor_id:
            if frappe.db.has_column(live_class_doctype, "instructor"):
                filters["instructor"] = instructor_id
            else:
                filters["owner"] = instructor_id
        if status:
            if frappe.db.has_column(live_class_doctype, "status"):
                filters["status"] = status

        # Get live classes
        live_classes = frappe.get_all(
            live_class_doctype,
            filters=filters,
            fields=["*"],
            order_by="creation desc"
        )

        # Filter upcoming if requested
        if upcoming_only:
            from frappe.utils import now_datetime, get_datetime
            current_time = now_datetime()
            live_classes = [
                lc for lc in live_classes
                if (hasattr(lc, 'start_time') or lc.get('start_time')) and
                get_datetime(lc.get('start_time') or lc.start_time) > current_time
            ]

        # Format for frontend
        formatted_classes = []
        for lc in live_classes:
            instructor_info = {"id": "", "name": "", "avatar": ""}
            instructor_id = lc.get("instructor") or lc.get("owner")
            if instructor_id and frappe.db.exists("User", instructor_id):
                user = frappe.get_doc("User", instructor_id)
                instructor_info = {
                    "id": instructor_id,
                    "name": user.full_name or instructor_id,
                    "avatar": user.user_image or ""
                }

            formatted_classes.append({
                "id": lc.name,
                "title": lc.get("title") or lc.get("class_title") or "Live Class",
                "description": lc.get("description") or "",
                "courseId": lc.get("course") or "",
                "instructor": instructor_info,
                "startTime": str(lc.get("start_time") or ""),
                "endTime": str(lc.get("end_time") or ""),
                "duration": lc.get("duration") or "",
                "status": lc.get("status") or "scheduled",
                "meetingUrl": lc.get("meeting_url") or lc.get("zoom_link") or "",
                "meetingId": lc.get("meeting_id") or "",
                "maxParticipants": cint(lc.get("max_participants")) or 0,
                "currentParticipants": cint(lc.get("current_participants")) or 0,
                "isRecorded": bool(lc.get("is_recorded") or lc.get("record_session")),
                "recordingUrl": lc.get("recording_url") or "",
                "createdAt": str(lc.creation) if hasattr(lc, 'creation') else ""
            })

        # Pagination
        total_count = len(formatted_classes)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = formatted_classes[start_idx:end_idx]

        return {
            "success": True,
            "liveClasses": paginated,
            "totalCount": total_count,
            "currentPage": page,
            "totalPages": total_pages,
            "pageSize": page_size
        }

    except Exception as e:
        frappe.log_error(f"Get live classes error: {str(e)}", "Course API")
        return {
            "success": False,
            "liveClasses": [],
            "message": _("An error occurred while fetching live classes")
        }


@frappe.whitelist(allow_guest=True)
def get_live_class(class_id=None):
    """
    Get single live class details

    Args:
        class_id: Live class document name

    Returns:
        {
            "success": bool,
            "liveClass": Live class object
        }
    """
    try:
        if not class_id:
            return {
                "success": False,
                "message": _("Live class ID is required")
            }

        live_class_doctype = "LMS Live Class"
        if not frappe.db.exists("DocType", live_class_doctype):
            if frappe.db.exists("DocType", "Live Class"):
                live_class_doctype = "Live Class"
            else:
                return {
                    "success": False,
                    "message": _("Live class feature not configured")
                }

        if not frappe.db.exists(live_class_doctype, class_id):
            return {
                "success": False,
                "message": _("Live class not found")
            }

        lc = frappe.get_doc(live_class_doctype, class_id)

        instructor_info = {"id": "", "name": "", "avatar": ""}
        instructor_id = lc.instructor if hasattr(lc, 'instructor') else lc.owner
        if instructor_id and frappe.db.exists("User", instructor_id):
            user = frappe.get_doc("User", instructor_id)
            instructor_info = {
                "id": instructor_id,
                "name": user.full_name or instructor_id,
                "avatar": user.user_image or ""
            }

        return {
            "success": True,
            "liveClass": {
                "id": lc.name,
                "title": lc.title if hasattr(lc, 'title') else lc.name,
                "description": lc.description if hasattr(lc, 'description') else "",
                "courseId": lc.course if hasattr(lc, 'course') else "",
                "instructor": instructor_info,
                "startTime": str(lc.start_time) if hasattr(lc, 'start_time') else "",
                "endTime": str(lc.end_time) if hasattr(lc, 'end_time') else "",
                "duration": lc.duration if hasattr(lc, 'duration') else "",
                "status": lc.status if hasattr(lc, 'status') else "scheduled",
                "meetingUrl": lc.meeting_url if hasattr(lc, 'meeting_url') else "",
                "meetingId": lc.meeting_id if hasattr(lc, 'meeting_id') else "",
                "maxParticipants": cint(lc.max_participants) if hasattr(lc, 'max_participants') else 0,
                "isRecorded": bool(lc.is_recorded) if hasattr(lc, 'is_recorded') else False,
                "recordingUrl": lc.recording_url if hasattr(lc, 'recording_url') else "",
                "agenda": lc.agenda if hasattr(lc, 'agenda') else "",
                "prerequisites": lc.prerequisites if hasattr(lc, 'prerequisites') else "",
                "createdAt": str(lc.creation)
            }
        }

    except Exception as e:
        frappe.log_error(f"Get live class error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while fetching live class details")
        }


@frappe.whitelist()
def create_live_class(
    title=None,
    course_id=None,
    description=None,
    start_time=None,
    end_time=None,
    duration=None,
    meeting_url=None,
    max_participants=None,
    is_recorded=False,
    agenda=None
):
    """
    Create a new live class (instructor only)

    Args:
        title: Class title (required)
        course_id: Associated course
        description: Class description
        start_time: Start datetime
        end_time: End datetime
        duration: Duration string
        meeting_url: Meeting/Zoom URL
        max_participants: Maximum participants allowed
        is_recorded: Whether to record the session
        agenda: Class agenda

    Returns:
        {
            "success": bool,
            "liveClassId": Created class ID
        }
    """
    try:
        current_user = frappe.session.user
        if current_user == "Guest":
            return {
                "success": False,
                "message": _("Authentication required")
            }

        if not title:
            return {
                "success": False,
                "message": _("Title is required")
            }

        live_class_doctype = "LMS Live Class"
        if not frappe.db.exists("DocType", live_class_doctype):
            if frappe.db.exists("DocType", "Live Class"):
                live_class_doctype = "Live Class"
            else:
                return {
                    "success": False,
                    "message": _("Live class feature not configured. DocType not found.")
                }

        lc = frappe.new_doc(live_class_doctype)
        lc.title = title
        lc.owner = current_user

        if hasattr(lc, 'instructor'):
            lc.instructor = current_user
        if course_id and hasattr(lc, 'course'):
            lc.course = course_id
        if description and hasattr(lc, 'description'):
            lc.description = description
        if start_time and hasattr(lc, 'start_time'):
            lc.start_time = start_time
        if end_time and hasattr(lc, 'end_time'):
            lc.end_time = end_time
        if duration and hasattr(lc, 'duration'):
            lc.duration = duration
        if meeting_url and hasattr(lc, 'meeting_url'):
            lc.meeting_url = meeting_url
        if max_participants and hasattr(lc, 'max_participants'):
            lc.max_participants = cint(max_participants)
        if is_recorded and hasattr(lc, 'is_recorded'):
            lc.is_recorded = 1
        if agenda and hasattr(lc, 'agenda'):
            lc.agenda = agenda

        if hasattr(lc, 'status'):
            lc.status = "scheduled"

        lc.insert()
        frappe.db.commit()

        return {
            "success": True,
            "liveClassId": lc.name,
            "message": _("Live class created successfully")
        }

    except Exception as e:
        frappe.log_error(f"Create live class error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": str(e) if frappe.conf.developer_mode else _("An error occurred while creating live class")
        }


@frappe.whitelist()
def join_live_class(class_id=None):
    """
    Join a live class (registers attendance)

    Args:
        class_id: Live class document name

    Returns:
        {
            "success": bool,
            "meetingUrl": URL to join the meeting
        }
    """
    try:
        current_user = frappe.session.user
        if current_user == "Guest":
            return {
                "success": False,
                "message": _("Authentication required to join live class")
            }

        if not class_id:
            return {
                "success": False,
                "message": _("Live class ID is required")
            }

        live_class_doctype = "LMS Live Class"
        if not frappe.db.exists("DocType", live_class_doctype):
            if frappe.db.exists("DocType", "Live Class"):
                live_class_doctype = "Live Class"
            else:
                return {
                    "success": False,
                    "message": _("Live class feature not configured")
                }

        if not frappe.db.exists(live_class_doctype, class_id):
            return {
                "success": False,
                "message": _("Live class not found")
            }

        lc = frappe.get_doc(live_class_doctype, class_id)

        # Check if class is live or scheduled
        status = lc.status if hasattr(lc, 'status') else "scheduled"
        if status == "completed":
            return {
                "success": False,
                "message": _("This live class has ended")
            }
        if status == "cancelled":
            return {
                "success": False,
                "message": _("This live class has been cancelled")
            }

        # Record attendance (using cache if doctype doesn't exist)
        attendance_key = f"live_class_attendance:{class_id}"
        attendees = frappe.cache().get_value(attendance_key)
        if attendees:
            attendees = json.loads(attendees)
        else:
            attendees = []

        if current_user not in attendees:
            attendees.append(current_user)
            frappe.cache().set_value(attendance_key, json.dumps(attendees), expires_in_sec=86400)

            # Update participant count if field exists
            if hasattr(lc, 'current_participants'):
                lc.current_participants = len(attendees)
                lc.save(ignore_permissions=True)
                frappe.db.commit()

        meeting_url = lc.meeting_url if hasattr(lc, 'meeting_url') else ""

        return {
            "success": True,
            "meetingUrl": meeting_url,
            "message": _("Joined live class successfully")
        }

    except Exception as e:
        frappe.log_error(f"Join live class error: {str(e)}", "Course API")
        return {
            "success": False,
            "message": _("An error occurred while joining live class")
        }
