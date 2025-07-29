# 🗄️ Database Setup Guide for Survey Data API Gateway

## 🎯 **What Database Setup Gives You**

With database setup, you'll unlock:
- ✅ **SQL Query Execution** - Run real SELECT queries
- ✅ **Data Export** - Export query results to CSV, Excel, JSON, Parquet
- ✅ **Schema Introspection** - View table structures and metadata
- ✅ **Performance Monitoring** - Track query performance and optimization
- ✅ **Template Queries** - Execute predefined report queries

---

## 🚀 **Option 1: Quick SQLite Setup (Easiest - 2 minutes)**

### Step 1: Install SQLite Support
```powershell
pip install sqlite3
```

### Step 2: Create SQLite Database with Sample Data
```powershell
# This will create a local SQLite file with sample survey data
python -c "
import sqlite3
import json
from datetime import datetime, timedelta
import random

# Create database
conn = sqlite3.connect('survey_data.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE surveys (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    created_date DATE DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'active'
)''')

cursor.execute('''
CREATE TABLE responses (
    id INTEGER PRIMARY KEY,
    survey_id INTEGER,
    respondent_age INTEGER,
    respondent_gender TEXT,
    response_text TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (survey_id) REFERENCES surveys (id)
)''')

cursor.execute('''
CREATE TABLE demographics (
    id INTEGER PRIMARY KEY,
    survey_id INTEGER,
    age_group TEXT,
    gender TEXT,
    location TEXT,
    education_level TEXT,
    income_range TEXT,
    FOREIGN KEY (survey_id) REFERENCES surveys (id)
)''')

# Insert sample data
surveys = [
    ('Customer Satisfaction Survey', 'Annual customer satisfaction survey for our services'),
    ('Product Feedback Survey', 'Feedback collection for new product features'),
    ('Employee Engagement Survey', 'Internal survey to measure employee satisfaction'),
    ('Market Research Survey', 'Understanding market trends and preferences'),
    ('User Experience Survey', 'Collecting feedback on website usability')
]

for title, desc in surveys:
    cursor.execute('INSERT INTO surveys (title, description) VALUES (?, ?)', (title, desc))

# Generate sample responses
responses_data = [
    (1, 25, 'Female', 'Very satisfied with the service quality', 5),
    (1, 34, 'Male', 'Good service but room for improvement', 4),
    (1, 28, 'Female', 'Average experience, could be better', 3),
    (2, 22, 'Male', 'Love the new features!', 5),
    (2, 45, 'Female', 'Features are useful but complex', 4),
    (3, 31, 'Male', 'Good work environment', 4),
    (3, 29, 'Female', 'Satisfied with current role', 4),
    (4, 38, 'Male', 'Market analysis is comprehensive', 5),
    (5, 26, 'Female', 'Website is user-friendly', 4)
]

for survey_id, age, gender, text, rating in responses_data:
    cursor.execute('''
        INSERT INTO responses (survey_id, respondent_age, respondent_gender, response_text, rating)
        VALUES (?, ?, ?, ?, ?)
    ''', (survey_id, age, gender, text, rating))

# Insert demographics
demo_data = [
    (1, '25-34', 'Female', 'New York', 'Bachelor', '$50-75k'),
    (1, '35-44', 'Male', 'California', 'Master', '$75-100k'),
    (2, '18-24', 'Male', 'Florida', 'High School', '$25-40k'),
    (3, '25-34', 'Male', 'Washington', 'Bachelor', '$60-85k'),
    (4, '35-44', 'Male', 'Texas', 'PhD', '$100k+'),
    (5, '25-34', 'Female', 'Oregon', 'Master', '$70-95k')
]

for survey_id, age_group, gender, location, education, income in demo_data:
    cursor.execute('''
        INSERT INTO demographics (survey_id, age_group, gender, location, education_level, income_range)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (survey_id, age_group, gender, location, education, income))

conn.commit()
conn.close()
print('✅ SQLite database created successfully with sample data!')
"
```

### Step 3: Update Configuration
```powershell
# Update your .env file
$envContent = @"
# Database Configuration (SQLite)
DATABASE_URL=sqlite:///survey_data.db

# JWT Configuration
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
API_TITLE=Survey Data API Gateway
API_VERSION=1.0.0
DEBUG=True

# Rate Limiting (requests per minute)
RATE_LIMIT=100

# Query Limits
MAX_QUERY_TIMEOUT=30
MAX_RESULT_ROWS=10000
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "✅ Configuration updated for SQLite!"
```

---

## 🐘 **Option 2: PostgreSQL Setup (Recommended for Production)**

### Step 1: Install PostgreSQL
```powershell
# Download and install PostgreSQL from: https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql
```

### Step 2: Create Database and User
```powershell
# Connect to PostgreSQL
psql -U postgres

# In PostgreSQL prompt:
CREATE DATABASE survey_db;
CREATE USER survey_user WITH PASSWORD 'survey_password';
GRANT ALL PRIVILEGES ON DATABASE survey_db TO survey_user;
\q
```

### Step 3: Initialize with Sample Data
```powershell
# Connect to your new database
psql -U survey_user -d survey_db

# Run the initialization script (already created: init_db.sql)
\i init_db.sql
\q
```

### Step 4: Update Configuration
```powershell
# Update .env file
$envContent = @"
# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://survey_user:survey_password@localhost/survey_db

# JWT Configuration
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
API_TITLE=Survey Data API Gateway
API_VERSION=1.0.0
DEBUG=True

# Rate Limiting (requests per minute)
RATE_LIMIT=100

# Query Limits
MAX_QUERY_TIMEOUT=30
MAX_RESULT_ROWS=10000
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "✅ Configuration updated for PostgreSQL!"
```

---

## 🐳 **Option 3: Docker Setup (Easiest for Development)**

### Step 1: Start PostgreSQL with Docker
```powershell
# Start PostgreSQL container
docker run --name survey-postgres -d `
  -e POSTGRES_DB=survey_db `
  -e POSTGRES_USER=survey_user `
  -e POSTGRES_PASSWORD=survey_password `
  -p 5432:5432 `
  postgres:15-alpine

# Wait for container to start
Start-Sleep -Seconds 10

# Initialize with sample data
docker exec -i survey-postgres psql -U survey_user -d survey_db < init_db.sql
```

### Step 2: Update Configuration (same as PostgreSQL option above)

---

## ☁️ **Option 4: Cloud Database (Production Ready)**

### Free Tier Options:
1. **Supabase** (Free PostgreSQL): https://supabase.com
2. **PlanetScale** (Free MySQL): https://planetscale.com
3. **Neon** (Free PostgreSQL): https://neon.tech

### Step 1: Create Database Online
- Sign up for any service above
- Create a new database
- Get connection string

### Step 2: Update Configuration
```powershell
# Update .env with your cloud connection string
DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

---

## 🧪 **Testing Database Setup**

### After any setup, restart your API:
```powershell
# Stop current server (Ctrl+C if running in terminal)
# Start again
python -m uvicorn app.main:app --reload
```

### Test Database Connection:
```powershell
# Test with our existing test script
python test_api.py
```

### Or test specific endpoints:
```powershell
# Test query execution
curl -X POST "http://localhost:8000/query/" `
  -H "Authorization: Bearer demo-key-123" `
  -H "Content-Type: application/json" `
  -d '{"sql": "SELECT * FROM surveys LIMIT 5"}'

# Test data export
curl -X POST "http://localhost:8000/export/query" `
  -H "Authorization: Bearer demo-key-123" `
  -H "Content-Type: application/json" `
  -d '{"sql": "SELECT * FROM surveys", "format": "json"}' `
  -o "export_test.json"
```

---

## 🎯 **What Each Option Gives You**

| Option | Setup Time | Best For | Pros | Cons |
|--------|------------|----------|------|------|
| **SQLite** | 2 min | Testing/Demo | Super quick, no install | Limited concurrent users |
| **PostgreSQL** | 10 min | Development | Full SQL features | Local setup required |
| **Docker** | 5 min | Development | Easy cleanup | Requires Docker |
| **Cloud** | 3 min | Production | Managed, scalable | May have usage limits |

---

## ⚡ **Quick Start Recommendation**

**Start with SQLite** (Option 1) - you'll have a working database in 2 minutes! You can always migrate to PostgreSQL later for production.

After setup, you'll be able to:
- ✅ Execute real SQL queries via API
- ✅ Export data in multiple formats
- ✅ Use all admin dashboard features
- ✅ Test performance monitoring
- ✅ Use WebSocket query streaming

---

## 🔧 **Need Help?**

Choose the option that fits your needs and I can help you through the specific setup steps!
