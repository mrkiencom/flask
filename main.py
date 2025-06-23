import json
import os
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify

app = Flask(__name__)

# Cấu hình PostgreSQL
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT', '5432')


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            port=DB_PORT
        )
        return conn
    except psycopg2.Error as err:
        print(f"Lỗi kết nối PostgreSQL: {err}")
        return None


def log_chat(session_id, intent_name, user_input, bot_response):
    conn = get_db_connection()
    if conn is None:
        return
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO chat_bot (session_id, intent_name, user_input, bot_response)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (session_id, intent_name, user_input, bot_response))
            conn.commit()
    except Exception as e:
        print(f"Lỗi khi ghi lịch sử chat: {e}")
    finally:
        conn.close()


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName')
    session = req.get("session", "unknown")
    session_id = session.split("/")[-1]
    user_input = req.get('queryResult', {}).get('queryText', '')

    if intent_name == 'WELCOME':
        return handle_welcome_intent(session)
    elif intent_name == 'Search_Course_by_name':
        return Search_Course_by_name(req, session_id, intent_name, user_input)
    elif intent_name == 'Search_Course_Combined':
        return Search_Course_Combined(req, session_id, intent_name, user_input)
    elif intent_name == 'Search_Course_by_Category':
        return Search_Course_by_Category(req, session_id, intent_name, user_input)
    elif intent_name == 'Search_Course_by_Topic':
        return Search_Course_by_Topic(req, session_id, intent_name, user_input)
    elif intent_name == 'Get_Course_Price':
        return Get_Course_Price(req, session_id, intent_name, user_input)

    return jsonify({'fulfillmentText': 'Xin lỗi, tôi không hiểu ý của bạn.'})


# ------------------------- CÁC HÀM TÌM KIẾM + GHI LỊCH SỬ ------------------------- #

def Search_Course_by_name(req, session_id, intent_name, user_input):
    ten_khoa_hoc = req.get('queryResult', {}).get('parameters', {}).get('course_name')
    if not ten_khoa_hoc:
        response = 'Bạn có thể cung cấp thêm thông tin về khóa học không?'
        log_chat(session_id, intent_name, user_input, response)
        return jsonify({'fulfillmentText': response})

    found_course = get_course_by_title(ten_khoa_hoc)

    if found_course:
        response = (
            f"Thông tin về khóa học '{found_course['title']}':\n"
            f"- Cấp độ: {found_course.get('level', 'không rõ')}\n"
            f"- Thể loại: {found_course.get('category', 'không rõ')}\n"
            f"- Chủ đề: {found_course.get('topic', 'không rõ')}\n"
            f"- Giá hiện tại: {found_course.get('price', 0)} đ.\n"
            f"Xem chi tiết: http://locahost:8080/courseDetail/{found_course['course_id']}"
        )
    else:
        response = f"Không tìm thấy thông tin cho khóa học '{ten_khoa_hoc}'. Bạn có thể kiểm tra lại tên không?"

    log_chat(session_id, intent_name, user_input, response)
    return jsonify({'fulfillmentText': response})


def Search_Course_Combined(req, session_id, intent_name, user_input):
    p = req.get('queryResult', {}).get('parameters', {})
    found_courses = get_courses_combined(
        name=p.get('course_name'),
        level=p.get('course_level'),
        category=p.get('course_category'),
        topic=p.get('course_topic')
    )

    if found_courses:
        response = "Dưới đây là một số khóa học phù hợp:\n"
        for c in found_courses:
            response += f"- {c['title']} (Giá: {c['price']}đ): http://locahost:8080/courseDetail/{c['course_id']}\n"
    else:
        response = "Không tìm thấy khóa học phù hợp với yêu cầu của bạn."

    log_chat(session_id, intent_name, user_input, response)
    return jsonify({'fulfillmentText': response})


def Search_Course_by_Category(req, session_id, intent_name, user_input):
    category = req.get('queryResult', {}).get('parameters', {}).get('course_category')
    if not category:
        response = "Bạn muốn tìm khóa học thuộc thể loại nào?"
        log_chat(session_id, intent_name, user_input, response)
        return jsonify({'fulfillmentText': response})

    courses = get_courses_by_category(category)
    if courses:
        response = f"Các khóa học thuộc thể loại '{category}':\n"
        for c in courses:
            response += f"- {c['title']} (Giá: {c['price']}đ): http://locahost:8080/courseDetail/{c['course_id']}\n"
    else:
        response = f"Không có khóa học nào thuộc thể loại '{category}'."

    log_chat(session_id, intent_name, user_input, response)
    return jsonify({'fulfillmentText': response})


def Search_Course_by_Topic(req, session_id, intent_name, user_input):
    topic = req.get('queryResult', {}).get('parameters', {}).get('course_topic')
    if not topic:
        response = "Bạn muốn tìm khóa học về chủ đề nào?"
        log_chat(session_id, intent_name, user_input, response)
        return jsonify({'fulfillmentText': response})

    courses = get_courses_by_topic(topic)
    if courses:
        response = f"Các khóa học về chủ đề '{topic}':\n"
        for c in courses:
            response += f"- {c['title']} (Giá: {c['price']}đ): http://locahost:8080/courseDetail/{c['course_id']}\n"
    else:
        response = f"Không có khóa học nào về chủ đề '{topic}'."

    log_chat(session_id, intent_name, user_input, response)
    return jsonify({'fulfillmentText': response})


def Get_Course_Price(req, session_id, intent_name, user_input):
    name = req.get('queryResult', {}).get('parameters', {}).get('course_name')
    if not name:
        response = "Bạn muốn hỏi giá khóa học nào?"
        log_chat(session_id, intent_name, user_input, response)
        return jsonify({'fulfillmentText': response})

    course = get_course_by_title(name)
    if course:
        try:
            price = float(course['price'])
            if price == 0:
                response = f"Khóa học '{course['title']}' là miễn phí."
            else:
                response = f"Khóa học '{course['title']}' có giá {price}đ."
            response += f" Xem: http://locahost:8080/courseDetail/{course['course_id']}"
        except:
            response = f"Không xác định được giá khóa học '{course['title']}'."
    else:
        response = f"Không tìm thấy khóa học '{name}'."

    log_chat(session_id, intent_name, user_input, response)
    return jsonify({'fulfillmentText': response})


# ------------------------- CÁC TRUY VẤN SQL KHÁC ------------------------- #

def get_course_by_title(title):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM courses WHERE LOWER(title) LIKE %s LIMIT 1", (f"%{title.lower()}%",))
            result = cursor.fetchone()
            return dict(result) if result else None
    except Exception as e:
        print(f"Lỗi truy vấn course theo title: {e}")
        return None
    finally:
        conn.close()


def get_courses_combined(name=None, level=None, category=None, topic=None):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Lỗi truy vấn combined: {e}")
        return None
    finally:
        conn.close()


def get_courses_by_category(category):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM courses WHERE LOWER(category) LIKE %s LIMIT 5", (f"%{category.lower()}%",))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Lỗi truy vấn category: {e}")
        return None
    finally:
        conn.close()


def get_courses_by_topic(topic):
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM courses WHERE LOWER(topic) LIKE %s LIMIT 5", (f"%{topic.lower()}%",))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Lỗi truy vấn topic: {e}")
        return None
    finally:
        conn.close()

def handle_welcome_intent(full_session_id):
    session_id = full_session_id.split('/')[-1]  # lấy phần session_id cuối

    conn = get_db_connection()
    if conn is None:
        return jsonify({'fulfillmentText': 'Không thể kết nối database.'})

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT user_input, bot_response FROM chat_bot WHERE session_id = %s ORDER BY id ASC LIMIT 5",
            (session_id,)
        )
        rows = cursor.fetchall()

        if not rows:
            return jsonify({'fulfillmentText': 'Chào mừng bạn đến với chatbot! Hỏi mình bất cứ điều gì nhé.'})

        # Tạo chuỗi tin nhắn từ lịch sử
        messages = []
        for pair in rows:
            messages.append({"text": {"text": [f"Bạn: {pair['user_input']}"]}})
            messages.append({"text": {"text": [f"Bot: {pair['bot_response']}"]}})

        return jsonify({"fulfillmentMessages": messages})
    except Exception as e:
        print(f"Lỗi lấy lịch sử trong WELCOME: {e}")
        return jsonify({'fulfillmentText': 'Có lỗi xảy ra khi tải lịch sử.'})
    finally:
        cursor.close()
        conn.close()



# ------------------------- MAIN ------------------------- #

if __name__ == '__main__':
    print("Đang chạy ứng dụng Flask...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

