import json
import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify

app = Flask(__name__)

# Cấu hình PostgreSQL (nên dùng biến môi trường khi deploy thật)
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT', '5432')


def get_db_connection():
    print("Đang cố gắng kết nối PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            port=DB_PORT
        )
        print("Kết nối PostgreSQL thành công!")
        return conn
    except psycopg2.Error as err:
        print(f"Lỗi kết nối PostgreSQL: {err}")
        return None


@app.route('/webhook', methods=['POST'])
def webhook():
    print("Webhook request nhận được!")
    req = request.get_json(silent=True, force=True)
    intent_name = req.get('queryResult').get('intent').get('displayName')

    if intent_name == 'Search_Course_by_name':
        return Search_Course_by_name(req)
    elif intent_name == 'Search_Course_Combined': 
        return Search_Course_Combined(req)
    elif intent_name == 'Search_Course_by_Category': 
        return Search_Course_by_Category(req)
    elif intent_name == 'Search_Course_by_Topic': 
        return Search_Course_by_Topic(req) 
    elif intent_name == 'Get_Course_Price':
        return Get_Course_Price(req)

    return jsonify({'fulfillmentText': 'Xin lỗi, tôi không hiểu ý của bạn.'})


def get_course_by_title(title):
    conn = get_db_connection()
    if conn is None:
        return None
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        query = "SELECT * FROM courses WHERE LOWER(title) LIKE %s LIMIT 1"
        cursor.execute(query, (f"%{title.lower()}%",))
        course = cursor.fetchone()
        return dict(course) if course else None
    except Exception as err:
        print(f"Lỗi truy vấn: {err}")
        return None
    finally:
        cursor.close()
        conn.close()


def Search_Course_by_name(req):
    parameters = req.get('queryResult').get('parameters')
    ten_khoa_hoc = parameters.get('course_name')

    if not ten_khoa_hoc:
        return jsonify({'fulfillmentText': 'Bạn có thể cung cấp thêm thông tin về khóa học không?'})

    found_course = get_course_by_title(ten_khoa_hoc)

    if found_course:
        course_id = found_course.get('course_id', 'không rõ')
        level = found_course.get('level', 'không rõ')
        category = found_course.get('category', 'không rõ')
        topic = found_course.get('topic', 'không rõ')
        price = found_course.get('price', '0')

        response_text = (
            f"Thông tin về khóa học '{found_course['title']}':\n"
            f"- Cấp độ: {level}\n"
            f"- Thể loại: {category}\n"
            f"- Chủ đề: {topic}\n"
            f"- Giá hiện tại: {price} $.\n"
            f"Bạn có thể xem chi tiết tại đây: http://doanshop.onrender.com/detailCourse/{course_id}"
        )
    else:
        response_text = f"Không tìm thấy thông tin cho khóa học '{ten_khoa_hoc}'. Bạn có thể kiểm tra lại tên không?"

    return jsonify({'fulfillmentText': response_text})


def get_courses_combined(name=None, level=None, category=None, topic=None):
    conn = get_db_connection()
    if conn is None:
        return None
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        query = "SELECT * FROM courses WHERE 1=1"
        params = []

        if name:
            query += " AND LOWER(title) LIKE %s"
            params.append(f"%{name.lower()}%")
        if level:
            query += " AND LOWER(level) LIKE %s"
            params.append(f"%{level.lower()}%")
        if category:
            query += " AND LOWER(category) LIKE %s"
            params.append(f"%{category.lower()}%")
        if topic:
            query += " AND LOWER(topic) LIKE %s"
            params.append(f"%{topic.lower()}%")

        query += " LIMIT 5"
        cursor.execute(query, tuple(params))
        courses = cursor.fetchall()
        return [dict(c) for c in courses]
    except Exception as err:
        print(f"Lỗi truy vấn kết hợp: {err}")
        return None
    finally:
        cursor.close()
        conn.close()


def Search_Course_Combined(req):
    p = req.get('queryResult').get('parameters')
    found_courses = get_courses_combined(
        name=p.get('course_name'),
        level=p.get('course_level'),
        category=p.get('course_category'),
        topic=p.get('course_topic')
    )

    if found_courses:
        response_text = "Dưới đây là một số khóa học phù hợp:\n"
        for course in found_courses:
            response_text += f"- {course['title']} (Giá: {course['price']}$): http://doanshop.onrender.com/detailCourse/{course['course_id']}\n"
    else:
        response_text = "Không tìm thấy khóa học phù hợp với yêu cầu của bạn."

    return jsonify({'fulfillmentText': response_text})


def get_courses_by_category(category):
    conn = get_db_connection()
    if conn is None:
        return None
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        query = "SELECT * FROM courses WHERE LOWER(category) LIKE %s LIMIT 5"
        cursor.execute(query, (f"%{category.lower()}%",))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as err:
        print(f"Lỗi truy vấn category: {err}")
        return None
    finally:
        cursor.close()
        conn.close()


def Search_Course_by_Category(req):
    category = req.get('queryResult').get('parameters').get('course_category')
    if not category:
        return jsonify({'fulfillmentText': 'Bạn muốn tìm khóa học thuộc thể loại nào?'})

    courses = get_courses_by_category(category)

    if courses:
        response_text = f"Các khóa học thuộc thể loại '{category}':\n"
        for course in courses:
            response_text += f"- {course['title']} (Giá: {course['price']}$): http://doanshop.onrender.com/detailCourse/{course['course_id']}\n"
    else:
        response_text = f"Không có khóa học nào thuộc thể loại '{category}'."

    return jsonify({'fulfillmentText': response_text})


def get_courses_by_topic(topic):
    conn = get_db_connection()
    if conn is None:
        return None
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        query = "SELECT * FROM courses WHERE LOWER(topic) LIKE %s LIMIT 5"
        cursor.execute(query, (f"%{topic.lower()}%",))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as err:
        print(f"Lỗi truy vấn topic: {err}")
        return None
    finally:
        cursor.close()
        conn.close()


def Search_Course_by_Topic(req):
    topic = req.get('queryResult').get('parameters').get('course_topic')
    if not topic:
        return jsonify({'fulfillmentText': 'Bạn muốn tìm khóa học về chủ đề nào?'})

    courses = get_courses_by_topic(topic)

    if courses:
        response_text = f"Các khóa học về chủ đề '{topic}':\n"
        for course in courses:
            response_text += f"- {course['title']} (Giá: {course['price']}$): http://doanshop.onrender.com/detailCourse/{course['course_id']}\n"
    else:
        response_text = f"Không có khóa học nào về chủ đề '{topic}'."

    return jsonify({'fulfillmentText': response_text})


def Get_Course_Price(req):
    name = req.get('queryResult').get('parameters').get('course_name')
    if not name:
        return jsonify({'fulfillmentText': 'Bạn muốn hỏi giá khóa học nào?'})

    course = get_course_by_title(name)
    if course:
        try:
            price = float(course['price'])
            if price == 0:
                message = f"Khóa học '{course['title']}' là miễn phí."
            else:
                message = f"Khóa học '{course['title']}' có giá {price}$."
        except:
            message = f"Không xác định được giá khóa học '{course['title']}'."
        message += f" Xem: http://doanshop.onrender.com/detailCourse/{course['course_id']}"
    else:
        message = f"Không tìm thấy khóa học '{name}'."

    return jsonify({'fulfillmentText': message})


if __name__ == '__main__':
    print("Đang chạy ứng dụng Flask...")
    try:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    except Exception as e:
        print(f"Lỗi khi chạy ứng dụng Flask: {e}")
