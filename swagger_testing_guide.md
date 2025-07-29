# 🌐 Swagger UI Testing Guide

## ✅ **Working Endpoints (No Database Required)**

### 1. **Authentication & Authorization**

#### Get API Information
- **Endpoint**: `GET /`
- **Auth**: None required
- **Expected**: 200 success with API info

#### Health Check
- **Endpoint**: `GET /health`
- **Auth**: None required
- **Expected**: 503 (unhealthy database) but API info included

#### Create JWT Token
- **Endpoint**: `POST /auth/token`
- **Auth**: None required
- **Parameters**: 
  - `user_id`: "test_user"
  - `permissions`: ["read", "query", "admin"]
- **Expected**: 200 with JWT token

#### Get User Info
- **Endpoint**: `GET /user/info`
- **Auth**: Required (`Bearer demo-key-123`)
- **Expected**: 200 with user details

### 2. **Export System (Format Info)**

#### Get Export Formats
- **Endpoint**: `GET /export/formats`
- **Auth**: Required (`Bearer demo-key-123`)
- **Expected**: 200 with supported formats (csv, excel, json, parquet)

#### Get Export Templates
- **Endpoint**: `GET /export/templates`
- **Auth**: Required (`Bearer demo-key-123`)
- **Expected**: 200 with available templates

### 3. **Query System (Templates Only)**

#### Get Query Templates
- **Endpoint**: `GET /query/templates`
- **Auth**: Required (`Bearer demo-key-123`)
- **Expected**: 200 with predefined query templates

### 4. **Admin Dashboard**

#### Admin Dashboard
- **Endpoint**: `GET /admin/dashboard`
- **Auth**: Required (`Bearer admin-key-456`)
- **Expected**: 200 with system status (database will show unhealthy)

#### System Resources
- **Endpoint**: `GET /admin/system/resources`
- **Auth**: Required (`Bearer admin-key-456`)
- **Expected**: 200 with CPU, memory, disk usage

#### Cache Management
- **Endpoint**: `GET /admin/cache/management`
- **Auth**: Required (`Bearer admin-key-456`)
- **Expected**: 200 with cache status (disabled without Redis)

#### Rate Limit Status
- **Endpoint**: `GET /admin/rate-limits/status`
- **Auth**: Required (`Bearer admin-key-456`)
- **Expected**: 200 with rate limiting configuration

### 5. **WebSocket Info**

#### WebSocket Connections
- **Endpoint**: `GET /ws/connections`
- **Auth**: None required
- **Expected**: 200 with active connections (0 initially)

---

## ❌ **Endpoints That Need Database**

These will return 500 errors without PostgreSQL:

- `POST /query/` - Execute SQL queries
- `POST /export/query` - Export query results
- `GET /datasets` - List database tables
- `GET /schema` - Get table schema
- `POST /export/template/{template_id}` - Export from templates
- `GET /admin/database/health` - Database health details

---

## 🧪 **Step-by-Step Testing**

### Step 1: Basic Authentication Test
1. Go to `GET /user/info`
2. Click "Try it out"
3. Click "Authorize" button (top right)
4. Enter: `Bearer demo-key-123`
5. Click "Authorize" and "Close"
6. Click "Execute"
7. ✅ Should see: `200` with user details

### Step 2: System Monitoring Test
1. Go to `GET /admin/system/resources`
2. Click "Try it out"
3. Click "Authorize" button
4. Enter: `Bearer admin-key-456`
5. Click "Authorize" and "Close"
6. Click "Execute"
7. ✅ Should see: `200` with CPU/memory usage

### Step 3: Export Formats Test
1. Go to `GET /export/formats`
2. Make sure you're authorized with demo key
3. Click "Execute"
4. ✅ Should see: `200` with supported formats

### Step 4: JWT Token Creation
1. Go to `POST /auth/token`
2. Click "Try it out"
3. Enter parameters:
   - `user_id`: "my_test_user"
   - `permissions`: ["read", "query", "admin"]
4. Click "Execute"
5. ✅ Should see: `200` with new JWT token
6. Copy the `access_token` value
7. Test it in `GET /user/info` by authorizing with `Bearer <your-new-token>`

---

## 🔧 **For Database-Dependent Features**

To test query execution and exports, you need:

1. **PostgreSQL Database**:
   ```bash
   # Install PostgreSQL and create database
   createdb survey_db
   ```

2. **Update Configuration**:
   ```bash
   # Edit .env file
   DATABASE_URL=postgresql://your_username:your_password@localhost/survey_db
   ```

3. **Optional: Redis for Caching**:
   ```bash
   # Install and start Redis
   redis-server
   ```

---

## 🎯 **What You Can Test Right Now**

Without any additional setup, you can fully test:
- ✅ Authentication system
- ✅ Admin monitoring dashboard
- ✅ Export format information
- ✅ System resource monitoring
- ✅ Query templates
- ✅ JWT token creation and validation
- ✅ WebSocket connection management
- ✅ API documentation and validation

The core API infrastructure is working perfectly! 🚀
