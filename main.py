from flask import Blueprint, request, jsonify
import psycopg2
import psycopg2.extras
import os

webhook_bp = Blueprint('webhook', __name__)

def get_db_connection():
    print("Đang cố gắng kết nối PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            port=os.environ.get('DB_PORT', 5432)
        )
        print("Kết nối PostgreSQL thành công!")
        return conn
    except psycopg2.Error as err:
        print(f"Lỗi kết nối PostgreSQL: {err}")
        return None

def get_course_by_title(title):
    conn = get_db_connection()
    if conn is None:
        return None

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = "SELECT * FROM courses WHERE LOWER(title) LIKE %s LIMIT 1"
        cursor.execute(query, (f"%{title.lower()}%",))
        return cursor.fetchone()
    except psycopg2.Error as err:
        print(f"Lỗi truy vấn PostgreSQL: {err}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_courses_by_category(category_name):
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = "SELECT * FROM courses WHERE LOWER(category) = %s"
        cursor.execute(query, (category_name.lower(),))
        return cursor.fetchall()
    except psycopg2.Error as err:
        print(f"Lỗi truy vấn PostgreSQL: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_courses_by_topic(topic):
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = "SELECT * FROM courses WHERE LOWER(topic) = %s"
        cursor.execute(query, (topic.lower(),))
        return cursor.fetchall()
    except psycopg2.Error as err:
        print(f"Lỗi truy vấn PostgreSQL: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_courses_by_price(is_paid):
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        query = "SELECT * FROM courses WHERE is_paid = %s"
        cursor.execute(query, (is_paid,))
        return cursor.fetchall()
    except psycopg2.Error as err:
        print(f"Lỗi truy vấn PostgreSQL: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    intent_name = data.get('intent')
    parameters = data.get('parameters', {})

    response = {}

    if intent_name == 'FindCourseByTitle':
        title = parameters.get('title')
        if title:
            course = get_course_by_title(title)
            if course:
                response = {"fulfillmentText": f"Khóa học '{course['title']}' thuộc chủ đề '{course['topic']}' và thể loại '{course['category']}'."}
            else:
                response = {"fulfillmentText": "Không tìm thấy khóa học phù hợp."}
        else:
            response = {"fulfillmentText": "Bạn vui lòng cung cấp tên khóa học."}

    elif intent_name == 'FindCourseByCategory':
        category = parameters.get('category')
        if category:
            courses = get_courses_by_category(category)
            if courses:
                course_titles = [course['title'] for course in courses]
                response = {"fulfillmentText": f"Các khóa học trong thể loại '{category}': " + ", ".join(course_titles)}
            else:
                response = {"fulfillmentText": "Không tìm thấy khóa học nào trong thể loại này."}
        else:
            response = {"fulfillmentText": "Bạn vui lòng cung cấp thể loại khóa học."}

    elif intent_name == 'FindCourseByTopic':
        topic = parameters.get('topic')
        if topic:
            courses = get_courses_by_topic(topic)
            if courses:
                course_titles = [course['title'] for course in courses]
                response = {"fulfillmentText": f"Các khóa học về chủ đề '{topic}': " + ", ".join(course_titles)}
            else:
                response = {"fulfillmentText": "Không tìm thấy khóa học nào về chủ đề này."}
        else:
            response = {"fulfillmentText": "Bạn vui lòng cung cấp chủ đề khóa học."}

    elif intent_name == 'FindCourseByPrice':
        is_paid = parameters.get('is_paid')
        if is_paid is not None:
            courses = get_courses_by_price(is_paid)
            if courses:
                course_titles = [course['title'] for course in courses]
                loai = "trả phí" if is_paid else "miễn phí"
                response = {"fulfillmentText": f"Các khóa học {loai}: " + ", ".join(course_titles)}
            else:
                response = {"fulfillmentText": "Không tìm thấy khóa học phù hợp."}
        else:
            response = {"fulfillmentText": "Bạn vui lòng chỉ định có trả phí hay không."}

    else:
        response = {"fulfillmentText": "Xin lỗi, tôi chưa hiểu yêu cầu của bạn."}

    return jsonify(response)
