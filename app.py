import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import openpyxl

# 한글 폰트 설정 (시스템에 설치된 한글 폰트 사용)
try:
    font_path = os.path.join(os.path.dirname(__file__), "NotoSansKR-Regular.ttf")
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("NotoSans", font_path))
        korean_font = "NotoSans"
    else:
        korean_font = "Helvetica"  # fallback    
except:
    korean_font = 'Helvetica'

# 데이터베이스 초기화
def init_database():
    conn = sqlite3.connect('major_selection.db')
    cursor = conn.cursor()
    
    # 사용자 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # 신청 정보 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            student_id TEXT PRIMARY KEY,
            gpa REAL,
            completed_courses TEXT,
            major_1 TEXT,
            major_2 TEXT,
            major_3 TEXT,
            major_4 TEXT,
            major_5 TEXT,
            is_submitted BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (student_id) REFERENCES users (student_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# 비밀번호 해시화
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 사용자 등록
def register_user(student_id, name, password):
    conn = sqlite3.connect('major_selection.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (student_id, name, password_hash)
            VALUES (?, ?, ?)
        ''', (student_id, name, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# 관리자 계정 식별 포함된 로그인 함수 (변경됨)
def login_user(student_id, password):
    conn = sqlite3.connect('major_selection.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name FROM users 
        WHERE student_id = ? AND password_hash = ?
    ''', (student_id, hash_password(password)))

    result = cursor.fetchone()
    conn.close()

    if result:
        if student_id == 'admin':
            return '관리자'
        return result[0]
    return None

# 신청 정보 저장
def save_application(student_id, gpa, courses, majors, is_submitted=False):
    conn = sqlite3.connect('major_selection.db')
    cursor = conn.cursor()
    
    courses_str = ','.join(courses) if courses else ''
    
    cursor.execute('''
        INSERT OR REPLACE INTO applications 
        (student_id, gpa, completed_courses, major_1, major_2, major_3, major_4, major_5, is_submitted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_id, gpa, courses_str, majors[0], majors[1], majors[2], majors[3], majors[4], is_submitted))
    
    conn.commit()
    conn.close()

# 신청 정보 조회
def get_application(student_id):
    conn = sqlite3.connect('major_selection.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT gpa, completed_courses, major_1, major_2, major_3, major_4, major_5, is_submitted
        FROM applications WHERE student_id = ?
    ''', (student_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        gpa, courses_str, m1, m2, m3, m4, m5, is_submitted = result
        courses = courses_str.split(',') if courses_str else []
        majors = [m1, m2, m3, m4, m5]
        return gpa, courses, majors, is_submitted
    
    return None, [], ['', '', '', '', ''], False

# PDF 생성
def create_pdf(student_id, name, gpa, courses, majors):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 한글 스타일 정의
    korean_style = ParagraphStyle(
        'Korean',
        parent=styles['Normal'],
        fontName=korean_font,
        fontSize=12,
        spaceAfter=12,
    )
    
    title_style = ParagraphStyle(
        'KoreanTitle',
        parent=styles['Title'],
        fontName=korean_font,
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # 중앙 정렬
    )
    
    story = []
    
    # 제목
    title = Paragraph("전공 선택 신청서", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # 기본 정보
    info_data = [
        ['학번', student_id],
        ['이름', name],
        ['1학기 학점', f'{gpa}/4.3'],
        ['이수 교과목', ', '.join(courses) if courses else '없음']
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), korean_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # 전공 지망 순위
    major_title = Paragraph("전공 지망 순위", korean_style)
    story.append(major_title)
    
    major_names = ['인공지능', '컴퓨터과학', '데이터사이언스', '신소재물리', '지능형전자시스템']
    major_data = [['순위', '전공명']]
    
    for i, major in enumerate(majors):
        if major:
            major_data.append([f'{i+1}지망', major])
    
    major_table = Table(major_data, colWidths=[1.5*inch, 4*inch])
    major_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), korean_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(major_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# Streamlit 앱
def main():
    st.set_page_config(page_title="전공선택 신청시스템", page_icon="🎓", layout="wide")
    
    # 데이터베이스 초기화
    init_database()
    
    st.title("🎓 전공선택 신청시스템")
    
    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'student_id' not in st.session_state:
        st.session_state.student_id = ''
    if 'name' not in st.session_state:
        st.session_state.name = ''
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    
    # 사이드바 - 로그인/등록
    with st.sidebar:
        if not st.session_state.logged_in:
            st.header("로그인 / 회원가입")
            
            tab1, tab2 = st.tabs(["로그인", "회원가입"])
            
            with tab1:
                st.subheader("로그인")
                login_student_id = st.text_input("학번", key="login_id")
                login_password = st.text_input("비밀번호", type="password", key="login_pw")
                
                if st.button("로그인"):
                    if login_student_id and login_password:
                        name = login_user(login_student_id, login_password)
                        if name:
                            st.session_state.logged_in = True
                            st.session_state.student_id = login_student_id
                            st.session_state.name = name
                            st.session_state.is_admin = (login_student_id == 'admin')
                            st.success(f"{name}님, 환영합니다!")
                            st.rerun()
                        else:
                            st.error("학번 또는 비밀번호가 잘못되었습니다.")
                    else:
                        st.error("학번과 비밀번호를 입력해주세요.")
            
            with tab2:
                st.subheader("회원가입")
                reg_student_id = st.text_input("학번", key="reg_id")
                reg_name = st.text_input("이름", key="reg_name")
                reg_password = st.text_input("비밀번호", type="password", key="reg_pw")
                reg_confirm_password = st.text_input("비밀번호 확인", type="password", key="reg_confirm_pw")
                
                if st.button("회원가입"):
                    if all([reg_student_id, reg_name, reg_password, reg_confirm_password]):
                        if reg_password == reg_confirm_password:
                            if register_user(reg_student_id, reg_name, reg_password):
                                st.success("회원가입이 완료되었습니다!")
                            else:
                                st.error("이미 등록된 학번입니다.")
                        else:
                            st.error("비밀번호가 일치하지 않습니다.")
                    else:
                        st.error("모든 항목을 입력해주세요.")
        
        else:
            st.header(f"👤 {st.session_state.name}님")
            st.write(f"학번: {st.session_state.student_id}")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                st.session_state.student_id = ''
                st.session_state.name = ''
                st.rerun()
    
    # 메인 컨텐츠
    if st.session_state.logged_in:
        if st.session_state.is_admin:
            st.header("📊 관리자 대시보드")
            conn = sqlite3.connect('major_selection.db')
            df = pd.read_sql_query('''
                SELECT u.student_id, u.name, a.gpa, a.completed_courses,
                   a.major_1, a.major_2, a.major_3, a.major_4, a.major_5,
                   a.is_submitted
                FROM users u
                LEFT JOIN applications a ON u.student_id = a.student_id
            ''', conn)
            conn.close()

            st.dataframe(df)
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)

            st.download_button(
                label="📥 전체 신청 데이터 Excel 다운로드",
                data=excel_buffer,
                file_name="전공선택_신청자_데이터.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.header("전공선택 신청")
        
        # 기존 신청 정보 불러오기
            saved_gpa, saved_courses, saved_majors, is_submitted = get_application(st.session_state.student_id)
        
            if is_submitted:
                st.success("✅ 최종 제출되었습니다.")
                st.info("제출된 내용을 확인하고 PDF를 다운로드할 수 있습니다.")
        
        # 폼 생성
            with st.form("application_form"):
                col1, col2 = st.columns(2)
            
                with col1:
                    st.subheader("📊 학업 정보")
                
                # 학점 입력
                    gpa = st.number_input(
                        "1학기 학점 (4.3 만점)",
                        min_value=0.0,
                        max_value=4.3,
                        value=saved_gpa if saved_gpa else 0.0,
                        step=0.1,
                        format="%.2f",
                        disabled=is_submitted
                    )
                
                # 이수 교과목 입력
                    available_courses = [
                        "대학기초수학", "이산수학", "기초물리1", "기초물리2",
                        "파이썬프로그래밍", "미분적분학", "C프로그래밍"
                    ]
                
                    selected_courses = st.multiselect(
                        "이수한 교과목을 선택하세요",
                        available_courses,
                        default=saved_courses,
                        disabled=is_submitted
                    )
            
                with col2:
                    st.subheader("🎯 전공 지망 순위")
                
                    major_options = ["", "인공지능", "컴퓨터과학", "데이터사이언스", "신소재물리", "지능형전자시스템"]
                
                    majors = []
                    for i in range(5):
                        major = st.selectbox(
                            f"{i+1}지망",
                            major_options,
                            index=major_options.index(saved_majors[i]) if saved_majors[i] in major_options else 0,
                            disabled=is_submitted
                        )
                        majors.append(major)
            
            # 버튼들
                col1, col2, col3 = st.columns(3)
            
                with col1:
                    save_button = st.form_submit_button("💾 임시저장", disabled=is_submitted)
            
                with col2:
                    submit_button = st.form_submit_button("📋 최종제출", disabled=is_submitted)
            
                with col3:
                    # PDF 다운로드는 폼 외부에서 처리
                    pass
        
            # 폼 처리
            if save_button:
                save_application(st.session_state.student_id, gpa, selected_courses, majors, False)
                st.success("임시저장이 완료되었습니다!")
        
            if submit_button:
                # 유효성 검사
                if gpa <= 0:
                    st.error("학점을 입력해주세요.")
                elif not any(majors):
                    st.error("최소 1개의 전공을 선택해주세요.")
                else:
                    save_application(st.session_state.student_id, gpa, selected_courses, majors, True)
                    st.success("최종 제출이 완료되었습니다!")
                    st.balloons()
                    st.rerun()
        
        # PDF 다운로드 버튼 (현재 정보 기준)
            if gpa > 0 or any(majors):
                st.subheader(" 전공선택 신청서를 다운로드하세요.")
                pdf_buffer = create_pdf(
                    st.session_state.student_id,
                    st.session_state.name,
                    gpa,
                    selected_courses,
                    majors
                )
                st.download_button(
                    label="📥 PDF 파일 다운로드",
                    data=pdf_buffer.getvalue(),
                    file_name=f"전공선택신청서_{st.session_state.student_id}.pdf",
                    mime="application/pdf"
                )
    
    else:
        st.info("👈 사이드바에서 로그인하거나 회원가입을 해주세요.")
        
        # 시스템 소개
        st.header("📋 시스템 안내")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 선택 가능한 전공")
            majors_info = [
                "• 인공지능",
                "• 컴퓨터과학", 
                "• 데이터사이언스",
                "• 신소재물리",
                "• 지능형전자시스템"
            ]
            for major in majors_info:
                st.write(major)
        
        with col2:
            st.subheader("📚 이수 가능한 교과목")
            courses_info = [
                "• 대학기초수학",
                "• 이산수학",
                "• 기초물리1",
                "• 기초물리2", 
                "• 파이썬프로그래밍",
                "• 미분적분학",
                "• C프로그래밍"
            ]
            for course in courses_info:
                st.write(course)
        
        st.subheader("✨ 주요 기능")
        features = [
            "🔐 학번과 비밀번호로 안전한 로그인",
            "📊 1학기 학점과 이수교과목 입력",
            "🎯 1지망부터 5지망까지 전공 순위 선택",
            "💾 임시저장으로 언제든 수정 가능",
            "📋 최종제출 후 내용 확정",
            "📄 신청서 PDF 다운로드"
        ]
        for feature in features:
            st.write(feature)

if __name__ == "__main__":
    main()
