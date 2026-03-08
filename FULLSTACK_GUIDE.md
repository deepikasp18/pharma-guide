# PharmaGuide Full-Stack Development Guide

## 🎉 Your Application is Running!

Both the backend API and frontend UI are now running and ready to use.

## 🌐 Access Points

### Frontend (React UI)
**URL:** http://localhost:3000

The main user interface where you can:
- Submit health queries
- Manage patient profiles
- View medication information
- Check drug interactions
- Monitor alerts
- Log symptoms

### Backend (FastAPI)
**URL:** http://localhost:8000

The REST API that powers the frontend.

### API Documentation
**Swagger UI:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

Interactive API documentation for testing endpoints directly.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (localhost:3000)                  │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         React Frontend (Vite + TypeScript)         │    │
│  │  - Patient Management                              │    │
│  │  - Query Interface                                 │    │
│  │  - Medication Tracking                             │    │
│  │  - Alerts Dashboard                                │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           │ HTTP Requests (/api/*)           │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │              Vite Dev Server (Proxy)               │    │
│  │         Forwards /api/* → localhost:8000           │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Proxied Requests
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (localhost:8000)                │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                  API Endpoints                     │    │
│  │  - /query/process                                  │    │
│  │  - /patient/profile                                │    │
│  │  - /reasoning/interactions                         │    │
│  │  - /alerts/active                                  │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Mock Services (In-Memory)                  │    │
│  │  - Mock Neptune (Graph Database)                   │    │
│  │  - Mock OpenSearch                                 │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Manual Start (Current Setup)

**Backend is already running on port 8000**  
**Frontend is already running on port 3000**

Just open your browser to http://localhost:3000

### Option 2: Start Both Services Together

For future sessions, use the full-stack script:

```bash
./scripts/run_fullstack.sh
```

This will:
1. Check and install dependencies
2. Start backend on port 8000
3. Start frontend on port 3000
4. Show you all access URLs

Press `Ctrl+C` to stop both services.

## 📱 Using the Frontend

### 1. Home Page
Visit http://localhost:3000 to see the main interface.

### 2. Submit Health Queries
- Type your health question in the query box
- Example: "What are the side effects of Lisinopril?"
- Click "Submit" to get AI-powered responses

### 3. Manage Patient Profile
- Create or update patient information
- Add demographics (age, gender, weight)
- List current conditions
- Track medications

### 4. View Medications
- See all current medications
- Check dosages and frequencies
- Add new medications

### 5. Monitor Alerts
- View active health alerts
- Check drug interactions
- Acknowledge alerts

### 6. Log Symptoms
- Record symptoms as they occur
- Track severity and duration
- Link symptoms to medications

## 🔧 Development Workflow

### Frontend Development

**Location:** `frontend/`

**Start dev server:**
```bash
cd frontend
npm run dev
```

**Build for production:**
```bash
cd frontend
npm run build
```

**Preview production build:**
```bash
cd frontend
npm run preview
```

### Backend Development

**Location:** `src/`

**Start dev server:**
```bash
./scripts/run_local.sh
```

**Run tests:**
```bash
uv run pytest tests/ -v
```

**Check API docs:**
http://localhost:8000/docs

### Making Changes

**Frontend changes:**
- Edit files in `frontend/src/`
- Vite will hot-reload automatically
- No need to restart the server

**Backend changes:**
- Edit files in `src/`
- Server will auto-reload (if using `--reload` flag)
- Changes reflect immediately

## 🧪 Testing the Full Stack

### Test Flow 1: Query Processing

1. **Frontend:** Open http://localhost:3000
2. **Action:** Submit query "What are the side effects of aspirin?"
3. **Backend:** Processes query via `/query/process`
4. **Frontend:** Displays results

### Test Flow 2: Patient Management

1. **Frontend:** Navigate to patient profile section
2. **Action:** Create new patient profile
3. **Backend:** Stores in mock database via `/patient/profile`
4. **Frontend:** Shows confirmation

### Test Flow 3: API Direct Testing

1. **Open:** http://localhost:8000/docs
2. **Select:** Any endpoint (e.g., `POST /query/process`)
3. **Click:** "Try it out"
4. **Enter:** Test data
5. **Execute:** See response

## 📂 Project Structure

```
pharma-guide/
├── frontend/                    # React Frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── api.ts             # API client
│   │   ├── types.ts           # TypeScript types
│   │   ├── App.tsx            # Main app component
│   │   └── main.tsx           # Entry point
│   ├── package.json           # Frontend dependencies
│   └── vite.config.ts         # Vite configuration
│
├── src/                        # Backend API
│   ├── api/                   # API endpoints
│   ├── knowledge_graph/       # Graph services
│   ├── nlp/                   # NLP processing
│   └── main.py               # FastAPI app
│
├── scripts/
│   ├── run_fullstack.sh      # Start both services
│   ├── run_local.sh          # Start backend only
│   └── setup_local_dev.sh    # Initial setup
│
└── docs/                      # Documentation
```

## 🔍 Debugging

### Check Backend Status
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0"
}
```

### Check Frontend Status
Open browser console (F12) and check for errors.

### View Backend Logs
If using the full-stack script:
```bash
tail -f backend.log
```

### View Frontend Logs
If using the full-stack script:
```bash
tail -f frontend.log
```

### Common Issues

**Port already in use:**
```bash
# Find process using port 3000
lsof -i :3000
# Kill it
kill -9 <PID>

# Find process using port 8000
lsof -i :8000
kill -9 <PID>
```

**Frontend can't connect to backend:**
- Check backend is running: `curl http://localhost:8000/health`
- Check Vite proxy config in `frontend/vite.config.ts`
- Check browser console for CORS errors

**Dependencies missing:**
```bash
# Backend
uv sync

# Frontend
cd frontend && npm install
```

## 🎨 Frontend Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **Axios** - HTTP client

## 🔌 Backend Technology Stack

- **FastAPI** - Web framework
- **Python 3.11+** - Programming language
- **Pydantic** - Data validation
- **Mock Services** - In-memory database

## 📊 API Endpoints Used by Frontend

### Query Processing
- `POST /query/process` - Submit health questions
- `GET /query/explain/{query_id}` - Get query explanation
- `POST /query/feedback` - Submit feedback

### Patient Management
- `POST /patient/profile` - Create/update profile
- `PUT /patient/profile/{id}` - Update profile
- `POST /patient/{id}/medications` - Add medication
- `GET /patient/{id}/medications` - Get medications
- `POST /patient/{id}/symptoms` - Log symptom
- `GET /patient/{id}/symptoms` - Get symptoms

### Alerts
- `GET /alerts/active` - Get active alerts
- `POST /alerts/acknowledge/{id}` - Acknowledge alert

### Reasoning
- `POST /reasoning/interactions` - Analyze drug interactions
- `POST /reasoning/analyze` - Analyze patient context

## 🚢 Production Deployment

### Frontend Build
```bash
cd frontend
npm run build
# Output in frontend/dist/
```

### Backend Production
```bash
# Set production environment
export USE_MOCK_SERVICES=false
export ENVIRONMENT=production

# Run with production server
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment
```bash
# Build and run with docker-compose
docker-compose up -d
```

## 📚 Additional Resources

- [Backend API Documentation](http://localhost:8000/docs)
- [Mock Data Guide](docs/MOCK_DATA_GUIDE.md)
- [Local Development Guide](docs/LOCAL_DEVELOPMENT.md)
- [Environment Setup](docs/ENVIRONMENT_SETUP.md)
- [FAQ](docs/FAQ.md)

## 🎯 Next Steps

1. ✅ **Explore the UI** - Open http://localhost:3000
2. ✅ **Test queries** - Submit health questions
3. ✅ **Create patient profile** - Add patient information
4. ✅ **Check API docs** - Visit http://localhost:8000/docs
5. ✅ **Make changes** - Edit code and see live updates

## 💡 Tips

- **Hot Reload:** Both frontend and backend support hot reloading
- **Mock Data:** All data is in-memory, resets on restart
- **API Testing:** Use Swagger UI for quick API testing
- **Browser DevTools:** Use React DevTools for component debugging
- **Network Tab:** Monitor API calls in browser DevTools

---

**Enjoy building with PharmaGuide!** 🎉

Both services are running and ready for development and testing.
