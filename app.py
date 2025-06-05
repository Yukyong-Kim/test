import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch
import io
import tempfile
import os

# 페이지 설정
st.set_page_config(
    page_title="전공 선택 시스템",
    page_icon="🎓",
    layout="wide"
)

# 데이터베이스 초기화
def init_database():
    conn = sqlite3.connect('student_major.db')
    cursor = conn.cursor()
    
    # 학생 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            semester1_gpa REAL,
            completed_courses TEXT,
            major_preference_1 TEXT,
            major_preference_2 TEXT,
            major_preference_3 TEXT,
            major_preference_4 TEXT,
            major_preference_5 TEXT,
            is_submitted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# 비밀번호 해시화
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 학생 등록
def register_student(student_id, name, password):
    conn = sqlite3.connect('student_major.db')
    cursor = conn.cursor()
    
    try:
        hashed_password = hash_password(password)
        cursor.execute('''
            INSERT INTO students (student_id, name, password)
            VALUES (?, ?, ?)
        ''', (student_id, name, hashed_password))
        conn.commit()
        return True, "회원가입이 완료되었습니다."
    except sqlite3.IntegrityError:
        return False, "이미 존재하는 학번입니다."
    finally:
        conn.close()

# 학생 로그인
def login_student(student_id, password):
    conn = sqlite3.connect('student_major.db')
    cursor = conn.cursor()
    
    hashed_password = hash_password(password)
    cursor.execute('''
        SELECT name FROM students WHERE student_id = ? AND password = ?
    ''', (student_id, hashed_password))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None, result[0] if result else None

# 학생 정보 저장
def save_student_data(student_id, gpa, courses, preferences):
    conn = sqlite3.connect('student_major.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE students SET 
            semester1_gpa = ?,
            completed_courses = ?,
            major_preference_1 = ?,
            major_preference_2 = ?,
            major_preference_3 = ?,
            major_preference_4 = ?,
            major_preference_5 = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE student_id = ?
    ''', (gpa, ','.join(courses), preferences[0], preferences[1], 
          preferences[2], preferences[3], preferences[4], student_id))
    
    conn.commit()
    conn.close()

# 학생 정보 불러오기
def load_student_data(student_id):
    conn = sqlite3.connect('student_major.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT semester1_gpa, completed_courses, major_preference_1,
               major_preference_2, major_preference_3, major_preference_4,
               major_preference_5, is_submitted
        FROM students WHERE student_id = ?
    ''', (student_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        gpa, courses_str, pref1, pref2, pref3, pref4, pref5, is_submitted = result
        courses = courses_str.split(',') if courses_str else []
        preferences = [pref1, pref2, pref3, pref4, pref5]
        return gpa, courses, preferences, is_submitted
    return None, [], [None]*5, False

# 최종 제출
def submit_application(student_id):
    conn = sqlite3.connect('student_major.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE students SET is_submitted = 1, updated_at = CURRENT_TIMESTAMP
        WHERE student_id = ?
    ''', (student_id,))
    
    conn.commit()
    conn.close()

# 관리자 데이터 조회 (한글 컬럼명)
def get_all_students():
    conn = sqlite3.connect('student_major.db')
    df = pd.read_sql_query('''
        SELECT student_id, name, semester1_gpa, completed_courses,
               major_preference_1, major_preference_2, major_preference_3,
               major_preference_4, major_preference_5, is_submitted,
               created_at, updated_at
        FROM students ORDER BY student_id
    ''', conn)
    conn.close()
    
    # 컬럼명을 한글로 변경
    df.columns = [
        '학번', '이름', '1학기학점', '이수교과목',
        '1지망', '2지망', '3지망', '4지망', '5지망',
        '제출여부', '등록일시', '수정일시'
    ]
    
    # 제출여부를 한글로 변경
    df['제출여부'] = df['제출여부'].map({0: '미제출', 1: '제출완료'})
    
    return df

# PDF 생성 (한글 지원)
def create_pdf(student_id, name, gpa, courses, preferences):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 한글 폰트 등록 시도 (시스템에 따라 다를 수 있음)
    try:
        # Windows의 경우
        font_path = "C:/Windows/Fonts/malgun.ttf"  # 맑은 고딕
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("MalgunGothic", font_path))
            korean_font = "MalgunGothic"
        else:
            # Linux/Mac의 경우 또는 폰트가 없는 경우
            korean_font = "Helvetica"
    except:
        korean_font = "Helvetica"
    
    # 제목
    try:
        p.setFont(korean_font + "-Bold" if korean_font == "MalgunGothic" else "Helvetica-Bold", 20)
    except:
        p.setFont("Helvetica-Bold", 20)
    p.drawString(50, height - 50, "전공 선택 신청서")
    
    # 학생 정보
    try:
        p.setFont(korean_font, 12)
    except:
        p.setFont("Helvetica", 12)
    
    y_pos = height - 100
    
    p.drawString(50, y_pos, f"학번: {student_id}")
    y_pos -= 30
    p.drawString(50, y_pos, f"이름: {name}")
    y_pos -= 30
    p.drawString(50, y_pos, f"1학기 학점: {gpa}/4.3")
    y_pos -= 30
    
    # 이수 과목
    p.drawString(50, y_pos, "1학기 이수 교과목:")
    y_pos -= 20
    for course in courses:
        p.drawString(70, y_pos, f"• {course}")
        y_pos -= 20
    
    y_pos -= 20
    
    # 전공 희망 순위
    p.drawString(50, y_pos, "전공 희망 순위:")
    y_pos -= 20
    
    preference_names = ["1지망", "2지망", "3지망", "4지망", "5지망"]
    
    for i, pref in enumerate(preferences):
        if pref:
            p.drawString(70, y_pos, f"{preference_names[i]}: {pref}")
            y_pos -= 20
    
    # 제출 시간
    y_pos -= 30
    p.drawString(50, y_pos, f"제출 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}")
    
    p.save()
    buffer.seek(0)
    return buffer

# 메인 애플리케이션
def main():
    init_database()
    
    st.title("🎓 전공 선택 시스템")
    
    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'student_id' not in st.session_state:
        st.session_state.student_id = None
    if 'student_name' not in st.session_state:
        st.session_state.student_name = None
    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False
    
    # 사이드바 메뉴
    with st.sidebar:
        st.header("메뉴")
        
        if not st.session_state.logged_in and not st.session_state.admin_mode:
            menu = st.selectbox("선택하세요", ["로그인", "회원가입", "관리자 모드"])
        elif st.session_state.admin_mode:
            menu = "관리자 모드"
            if st.button("로그아웃"):
                st.session_state.admin_mode = False
                st.rerun()
        else:
            menu = "전공 선택"
            st.write(f"안녕하세요, {st.session_state.student_name}님!")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                st.session_state.student_id = None
                st.session_state.student_name = None
                st.rerun()
    
    # 전공 목록
    majors = ["인공지능", "컴퓨터과학", "데이터사이언스", "신소재물리", "지능형전자시스템"]
    
    # 이수 가능 과목 목록
    available_courses = [
        "대학기초수학", "이산수학", "기초물리1", "기초물리2", 
        "파이썬프로그래밍", "미분적분학", "C프로그래밍"
    ]
    
    if menu == "회원가입":
        st.header("회원가입")
        
        with st.form("register_form"):
            student_id = st.text_input("학번")
            name = st.text_input("이름")
            password = st.text_input("비밀번호", type="password")
            password_confirm = st.text_input("비밀번호 확인", type="password")
            
            if st.form_submit_button("회원가입"):
                if not student_id or not name or not password:
                    st.error("모든 필드를 입력해주세요.")
                elif password != password_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    success, message = register_student(student_id, name, password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    elif menu == "로그인":
        st.header("로그인")
        
        with st.form("login_form"):
            student_id = st.text_input("학번")
            password = st.text_input("비밀번호", type="password")
            
            if st.form_submit_button("로그인"):
                if not student_id or not password:
                    st.error("학번과 비밀번호를 입력해주세요.")
                else:
                    success, name = login_student(student_id, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.student_id = student_id
                        st.session_state.student_name = name
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.error("학번 또는 비밀번호가 올바르지 않습니다.")
    
    elif menu == "관리자 모드":
        if not st.session_state.admin_mode:
            st.header("관리자 로그인")
            admin_password = st.text_input("관리자 비밀번호", type="password")
            if st.button("관리자 로그인"):
                if admin_password == "admin123":  # 간단한 관리자 비밀번호
                    st.session_state.admin_mode = True
                    st.rerun()
                else:
                    st.error("관리자 비밀번호가 올바르지 않습니다.")
        else:
            st.header("📊 관리자 대시보드")
            
            df = get_all_students()
            
            if not df.empty:
                st.subheader("학생 데이터")
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드 (한글 시트명 및 파일명)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='전공선택현황', index=False)
                
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=output.getvalue(),
                    file_name=f"전공선택현황_{datetime.now().strftime('%Y년%m월%d일_%H시%M분')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # 통계 정보
                st.subheader("📈 통계")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("총 학생 수", len(df))
                
                with col2:
                    submitted = df[df['제출여부'] == '제출완료'].shape[0]
                    st.metric("제출 완료", submitted)
                
                with col3:
                    pending = df[df['제출여부'] == '미제출'].shape[0]
                    st.metric("미제출", pending)
                
                # 전공별 지원 현황
                st.subheader("전공별 지원 현황 (1지망 기준)")
                major_counts = df['1지망'].value_counts()
                if not major_counts.empty:
                    st.bar_chart(major_counts)
            else:
                st.info("등록된 학생이 없습니다.")
    
    elif menu == "전공 선택" and st.session_state.logged_in:
        st.header(f"전공 선택 - {st.session_state.student_name}님")
        
        # 기존 데이터 불러오기
        saved_gpa, saved_courses, saved_preferences, is_submitted = load_student_data(st.session_state.student_id)
        
        if is_submitted:
            st.success("✅ 이미 최종 제출이 완료되었습니다.")
            st.info("제출된 내용을 확인하고 PDF를 다운로드할 수 있습니다.")
        
        # 1학기 성적 정보
        st.subheader("1학기 성적 정보")
        
        col1, col2 = st.columns(2)
        
        with col1:
            gpa = st.number_input(
                "1학기 학점 (4.3 만점)", 
                min_value=0.0, 
                max_value=4.3, 
                step=0.1,
                value=saved_gpa if saved_gpa else 0.0
            )
        
        with col2:
            completed_courses = st.multiselect(
                "1학기 이수 교과목",
                available_courses,
                default=saved_courses
            )
        
        # 전공 희망 순위
        st.subheader("전공 희망 순위")
        
        preferences = [None] * 5
        available_majors = majors.copy()
        
        for i in range(5):
            # 기존 선택 값이 있으면 복원
            default_value = saved_preferences[i] if saved_preferences[i] in available_majors else None
            if default_value is None and saved_preferences[i]:
                # 이미 제출된 경우 이전 선택을 보여주되, 선택 불가능하게 함
                if is_submitted:
                    st.write(f"{i+1}지망: {saved_preferences[i]}")
                    preferences[i] = saved_preferences[i]
                    continue
            
            if not is_submitted:
                if available_majors:
                    selected = st.selectbox(
                        f"{i+1}지망",
                        ["선택하세요"] + available_majors,
                        index=available_majors.index(default_value) + 1 if default_value else 0,
                        key=f"major_{i}"
                    )
                    
                    if selected != "선택하세요":
                        preferences[i] = selected
                        available_majors.remove(selected)
                else:
                    st.write(f"{i+1}지망: 선택 가능한 전공이 없습니다.")
            else:
                st.write(f"{i+1}지망: {saved_preferences[i] if saved_preferences[i] else '미선택'}")
                preferences[i] = saved_preferences[i]
        
        # 버튼들
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if not is_submitted and st.button("💾 저장"):
                save_student_data(st.session_state.student_id, gpa, completed_courses, preferences)
                st.success("데이터가 저장되었습니다!")
                st.rerun()
        
        with col2:
            if not is_submitted and st.button("📤 최종 제출"):
                if gpa > 0 and completed_courses and preferences[0]:
                    save_student_data(st.session_state.student_id, gpa, completed_courses, preferences)
                    submit_application(st.session_state.student_id)
                    st.success("최종 제출이 완료되었습니다!")
                    st.rerun()
                else:
                    st.error("모든 필수 항목을 입력해주세요. (학점, 이수과목, 최소 1지망)")
        
        with col3:
            # PDF 다운로드
            if (gpa > 0 and completed_courses and preferences[0]) or is_submitted:
                current_gpa = saved_gpa if is_submitted else gpa
                current_courses = saved_courses if is_submitted else completed_courses
                current_preferences = saved_preferences if is_submitted else preferences
                
                pdf_buffer = create_pdf(
                    st.session_state.student_id,
                    st.session_state.student_name,
                    current_gpa,
                    current_courses,
                    current_preferences
                )
                
                st.download_button(
                    label="📄 PDF 다운로드",
                    data=pdf_buffer.getvalue(),
                    file_name=f"전공선택신청서_{st.session_state.student_id}_{datetime.now().strftime('%Y년%m월%d일')}.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    main()
