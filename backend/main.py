from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
import os, json, sqlite3, secrets, hashlib, hmac
import pandas as pd
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'placify.db')
MODEL_PATH = os.path.join(BASE_DIR, 'placement_percentage_model.joblib')
COLUMNS_PATH = os.path.join(BASE_DIR, 'placement_model_columns.joblib')
NUMERIC_DEFAULTS_PATH = os.path.join(BASE_DIR, 'numeric_defaults.joblib')
CATEGORICAL_DEFAULTS_PATH = os.path.join(BASE_DIR, 'categorical_defaults.joblib')
app = FastAPI(title='Placify Student Placement API', version='2.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
model = joblib.load(MODEL_PATH)
model_columns = joblib.load(COLUMNS_PATH)
numeric_defaults = joblib.load(NUMERIC_DEFAULTS_PATH)
categorical_defaults = joblib.load(CATEGORICAL_DEFAULTS_PATH)

class Signup(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    roll: str = Field(min_length=1, max_length=40)
    branch: str
    year: str
class Login(BaseModel):
    email: EmailStr
    password: str
class Profile(BaseModel):
    age: int = Field(default=21, ge=16, le=70)
    gender: str = 'Prefer not to say'
    cgpa: float = Field(ge=0, le=10)
    branch: str = 'CSE'
    college_tier: str = 'Tier 2'
    internships_count: int = Field(ge=0, le=50)
    projects_count: int = Field(ge=0, le=100)
    certifications_count: int = Field(default=0, ge=0, le=100)
    coding_skill_score: float = Field(ge=0, le=100)
    aptitude_score: float = Field(ge=0, le=100)
    communication_skill_score: float = Field(ge=0, le=100)
    logical_reasoning_score: float = Field(ge=0, le=100)
    hackathons_participated: int = Field(default=0, ge=0, le=100)
    github_repos: int = Field(default=0, ge=0, le=1000)
    linkedin_connections: int = Field(default=0, ge=0, le=100000)
    mock_interview_score: float = Field(default=50, ge=0, le=100)
    attendance_percentage: float = Field(ge=0, le=100)
    backlogs: int = Field(default=0, ge=0, le=100)
    extracurricular_score: float = Field(default=50, ge=0, le=100)
    leadership_score: float = Field(default=50, ge=0, le=100)
    volunteer_experience: str = 'No'
    sleep_hours: float = Field(default=7, ge=0, le=24)
    study_hours_per_day: float = Field(default=3, ge=0, le=24)
    skills: list[str] = []

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 180000).hex()
    return salt, digest

def init_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_salt TEXT NOT NULL, password_hash TEXT NOT NULL, roll TEXT, branch TEXT, year TEXT, role TEXT NOT NULL DEFAULT 'student', token TEXT, profile_json TEXT, prediction REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT)''')
        c.execute("UPDATE users SET role='admin' WHERE email=?", (os.getenv('PLACIFY_ADMIN_EMAIL','admin@placify.com').lower(),))
        email = os.getenv('PLACIFY_ADMIN_EMAIL','admin@placify.com').lower()
        if not c.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            salt, digest = hash_password(os.getenv('PLACIFY_ADMIN_PASSWORD','Admin@12345'))
            c.execute('INSERT INTO users(name,email,password_salt,password_hash,role) VALUES(?,?,?,?,?)', ('Placify Administrator', email, salt, digest, 'admin'))
init_db()

def current_user(authorization):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401, 'Please log in to continue.')
    token = authorization[7:]
    with connect() as c: user = c.execute('SELECT * FROM users WHERE token=?', (token,)).fetchone()
    if not user: raise HTTPException(401, 'Your session has expired. Please log in again.')
    return user

def public_user(user):
    return {'id': user['id'], 'name': user['name'], 'email': user['email'], 'roll': user['roll'], 'branch': user['branch'], 'year': user['year'], 'role': user['role'], 'created_at': user['created_at']}

def make_row(p):
    row = {k: float(v) for k,v in numeric_defaults.items() if k not in ['student_id','salary_package_lpa','placement_percentage']}
    row.update(categorical_defaults)
    row.update({k:p.get(k) for k in ['age','gender','cgpa','branch','college_tier','internships_count','projects_count','certifications_count','coding_skill_score','aptitude_score','communication_skill_score','logical_reasoning_score','hackathons_participated','github_repos','linkedin_connections','mock_interview_score','attendance_percentage','backlogs','extracurricular_score','leadership_score','volunteer_experience','sleep_hours','study_hours_per_day'] if k in p and p[k] is not None})
    row['branch'] = {'CSE-DS':'CSE','CSE - Data Science':'CSE'}.get(row.get('branch'), row.get('branch','CSE'))
    row['gender'] = row.get('gender') if row.get('gender') in ['Male','Female'] else categorical_defaults.get('gender','Male')
    row['college_tier'] = row.get('college_tier') if row.get('college_tier') in ['Tier 1','Tier 2','Tier 3'] else 'Tier 2'
    df = pd.DataFrame([row]).drop(columns=['student_id','placement_status','salary_package_lpa','placement_percentage'], errors='ignore')
    df = pd.get_dummies(df, drop_first=True, dtype=int).reindex(columns=model_columns, fill_value=0)
    return df

@app.get('/')
def home(): return {'message':'Placify API is running','docs':'/docs'}
@app.get('/api/health')
def health(): return {'status':'ok','model_loaded':model is not None}
@app.post('/api/auth/signup')
def signup(data: Signup):
    email = data.email.lower().strip()
    salt, digest = hash_password(data.password)
    with connect() as c:
        if c.execute('SELECT id FROM users WHERE email=? OR roll=?', (email,data.roll.strip())).fetchone(): raise HTTPException(409,'An account with this email or roll number already exists.')
        c.execute('INSERT INTO users(name,email,password_salt,password_hash,roll,branch,year,role) VALUES(?,?,?,?,?,?,?,?)', (data.name.strip(),email,salt,digest,data.roll.strip(),data.branch,data.year,'student'))
    return {'message':'Account created. Please log in.'}
@app.post('/api/auth/login')
def login(data: Login):
    with connect() as c: user = c.execute('SELECT * FROM users WHERE email=?', (data.email.lower().strip(),)).fetchone()
    if not user: raise HTTPException(401,'Invalid email or password.')
    _, digest = hash_password(data.password, user['password_salt'])
    if not hmac.compare_digest(digest,user['password_hash']): raise HTTPException(401,'Invalid email or password.')
    token = secrets.token_urlsafe(32)
    with connect() as c: c.execute('UPDATE users SET token=? WHERE id=?',(token,user['id']))
    with connect() as c: user = c.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
    return {'token':token,'user':public_user(user),'has_profile':bool(user['profile_json'])}
@app.get('/api/auth/me')
def me(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization); return {'user':public_user(user),'has_profile':bool(user['profile_json'])}
@app.post('/api/auth/logout')
def logout(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    with connect() as c: c.execute('UPDATE users SET token=NULL WHERE id=?',(user['id'],))
    return {'message':'Logged out.'}
@app.get('/api/profile')
def get_profile(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    return {'profile':json.loads(user['profile_json']) if user['profile_json'] else None,'prediction':user['prediction']}
@app.put('/api/profile')
def save_profile(profile: Profile, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user['role']!='student': raise HTTPException(403,'Student profile editing is only available for student accounts.')
    payload=profile.model_dump()
    with connect() as c: c.execute('UPDATE users SET profile_json=?, updated_at=CURRENT_TIMESTAMP, branch=COALESCE(branch,?) WHERE id=?',(json.dumps(payload),payload['branch'],user['id']))
    return {'message':'Student profile saved.','profile':payload}
@app.post('/api/predict')
def predict(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if not user['profile_json']: raise HTTPException(400,'Please save your student profile first.')
    p=json.loads(user['profile_json'])
    score=float(model.predict(make_row(p))[0]); score=max(0.0,min(100.0,score)); score=round(score,2)
    with connect() as c: c.execute('UPDATE users SET prediction=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',(score,user['id']))
    return {'placement_percentage':score,'note':'A model-based estimate, not a guarantee of placement.'}
@app.get('/api/admin/stats')
def admin_stats(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user['role']!='admin': raise HTTPException(403,'Administrator access required.')
    with connect() as c:
        total=c.execute("SELECT COUNT(*) n FROM users WHERE role='student'").fetchone()['n']
        completed=c.execute("SELECT COUNT(*) n FROM users WHERE role='student' AND profile_json IS NOT NULL").fetchone()['n']
        predicted=c.execute("SELECT COUNT(*) n FROM users WHERE role='student' AND prediction IS NOT NULL").fetchone()['n']
        avg=c.execute("SELECT AVG(prediction) n FROM users WHERE role='student' AND prediction IS NOT NULL").fetchone()['n']
    return {'total_students':total,'profiles_completed':completed,'predictions_generated':predicted,'average_prediction':round(avg,2) if avg is not None else None}
@app.get('/api/admin/students')
def admin_students(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user['role']!='admin': raise HTTPException(403,'Administrator access required.')
    with connect() as c: rows=c.execute("SELECT * FROM users WHERE role='student' ORDER BY created_at DESC").fetchall()
    result=[]
    for r in rows:
        p=json.loads(r['profile_json']) if r['profile_json'] else None
        result.append({**public_user(r),'profile':p,'prediction':r['prediction'],'profile_complete':bool(p),'updated_at':r['updated_at']})
    return {'students':result}
@app.get('/api/admin/students/{student_id}')
def admin_student(student_id: int, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user['role']!='admin': raise HTTPException(403,'Administrator access required.')
    with connect() as c: r=c.execute("SELECT * FROM users WHERE id=? AND role='student'",(student_id,)).fetchone()
    if not r: raise HTTPException(404,'Student not found.')
    return {**public_user(r),'profile':json.loads(r['profile_json']) if r['profile_json'] else None,'prediction':r['prediction'],'updated_at':r['updated_at']}
