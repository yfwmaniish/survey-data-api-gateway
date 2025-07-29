# Survey Data API Gateway

A secure, scalable API gateway that allows users to execute SQL queries on survey datasets and retrieve results in structured JSON format.

## 🚀 Features

- **Secure Query Execution**: Execute SELECT queries with SQL injection protection
- **Dataset Introspection**: Get metadata about available tables and schemas
- **Multiple Authentication**: Support for both JWT tokens and API keys
- **Query Templates**: Predefined safe query templates for common operations
- **Rate Limiting**: Built-in protection against API abuse
- **Docker Ready**: Easy deployment with Docker containers
- **Comprehensive Logging**: Full audit trail of all API operations

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Docker (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fastapi-api-gateway
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t survey-api-gateway .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 --env-file .env survey-api-gateway
   ```

## 📚 API Documentation

Once the application is running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication

The API supports two authentication methods:

### API Keys (Recommended for production)
```bash
curl -X POST "http://localhost:8000/query/" \
     -H "Authorization: Bearer demo-key-123" \
     -H "Content-Type: application/json" \
     -d '{"sql": "SELECT * FROM surveys LIMIT 10"}'
```

### JWT Tokens
```bash
# Get a token
curl -X POST "http://localhost:8000/auth/token?user_id=test_user"

# Use the token
curl -X POST "http://localhost:8000/query/" \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"sql": "SELECT * FROM surveys LIMIT 10"}'
```

## 🔑 Demo API Keys

For testing purposes, the following API keys are available:

- `demo-key-123`: Read and query permissions
- `admin-key-456`: Full admin permissions

## 📊 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/query/` | Execute SQL queries |
| GET | `/datasets` | List available datasets |
| GET | `/schema?table=<name>` | Get table schema |
| GET | `/query/templates` | Get query templates |

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/user/info` | Current user info |
| POST | `/auth/token` | Create JWT token (dev only) |

## 💡 Usage Examples

### Basic Query
```bash
curl -X POST "http://localhost:8000/query/" \
     -H "Authorization: Bearer demo-key-123" \
     -H "Content-Type: application/json" \
     -d '{
       "sql": "SELECT id, name, age FROM users WHERE age > 25 LIMIT 10"
     }'
```

### Get Available Datasets
```bash
curl -X GET "http://localhost:8000/datasets" \
     -H "Authorization: Bearer demo-key-123"
```

### Get Table Schema
```bash
curl -X GET "http://localhost:8000/schema?table=users" \
     -H "Authorization: Bearer demo-key-123"
```

### Parameterized Query
```bash
curl -X POST "http://localhost:8000/query/" \
     -H "Authorization: Bearer demo-key-123" \
     -H "Content-Type: application/json" \
     -d '{
       "sql": "SELECT * FROM users WHERE age > :min_age LIMIT :limit_count",
       "params": {"min_age": 18, "limit_count": 50}
     }'
```

## 🛡️ Security Features

- **SQL Injection Protection**: Only SELECT statements allowed, dangerous keywords blocked
- **Query Validation**: Comprehensive validation of SQL syntax and structure
- **Authentication Required**: All endpoints require valid authentication
- **Rate Limiting**: Configurable request limits per user
- **Query Timeouts**: Automatic timeout for long-running queries
- **Result Limits**: Maximum row count limits to prevent resource exhaustion

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

## 📁 Project Structure

```
fastapi-api-gateway/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection and management
│   ├── routes/
│   │   ├── query.py         # Query execution endpoints
│   │   └── meta.py          # Metadata endpoints
│   └── utils/
│       ├── auth.py          # Authentication utilities
│       └── query_validator.py # SQL query validation
├── tests/
│   └── test_query.py        # API tests
├── .env                     # Environment configuration
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker container definition
└── README.md               # This file
```

## ⚙️ Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Limits
MAX_QUERY_TIMEOUT=30
MAX_RESULT_ROWS=10000
RATE_LIMIT=100
```

## 🚢 Deployment

### Railway.app
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Fly.io
1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `flyctl auth login`
3. Launch: `flyctl launch`
4. Deploy: `flyctl deploy`

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/surveys
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: surveys
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📋 Todo

- [ ] Query result caching
- [ ] User management system
- [ ] Query history persistence
- [ ] Advanced rate limiting
- [ ] Query performance monitoring
- [ ] Data export formats (CSV, Excel)
- [ ] Scheduled queries
- [ ] Query result visualization

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the [API documentation](http://localhost:8000/docs)
2. Review the logs for error details
3. Open an issue in the repository
4. Contact the development team

---

**Built with ❤️ using FastAPI, SQLAlchemy, and PostgreSQL**
