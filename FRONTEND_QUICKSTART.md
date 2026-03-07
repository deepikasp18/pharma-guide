# PharmaGuide Frontend - Quick Start Guide

## What's Been Created

A complete React + TypeScript frontend with:
- Clean, minimalist healthcare UI design
- Natural language query interface
- Patient profile management
- Medication tracking with warnings
- Side effects display
- Symptom tracker
- Alert notifications

## Getting Started

### 1. Start the Backend (if not already running)

```bash
# From the project root
docker-compose up -d
```

The backend API will be available at `http://localhost:8000`

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Start the Development Server

```bash
npm run dev
```

The frontend will open at `http://localhost:3000`

## Using the Application

### First Time Setup

1. **Create Patient Profile**
   - Click "Patient Profile" tab
   - Fill in basic information (name, age, gender, weight, height)
   - Add medical conditions and allergies
   - Click "Save Profile"

2. **Add Medications**
   - Click "Medications" tab
   - Click "+ Add Medication"
   - Enter medication details (name, dosage, frequency, start date)
   - Click "Add Medication"

3. **Ask Questions**
   - Click "Ask Questions" tab
   - Type natural language questions like:
     - "What are the side effects of Lisinopril?"
     - "Can I take aspirin with my current medications?"
     - "What should I know about drug interactions?"
   - Click "Ask" to get AI-powered responses

4. **Track Symptoms**
   - Click "Symptom Tracker" tab
   - Click "+ Log Symptom"
   - Enter symptom details and severity
   - Click "Log Symptom"

### Key Features

- **Real-time Alerts**: Interaction warnings appear at the top when detected
- **Side Effects Panel**: Right sidebar shows potential side effects for your medications
- **Quick Info**: Patient summary in the right sidebar
- **Confidence Scores**: Query responses show confidence levels
- **Source Citations**: Responses include data source references

## Project Structure

```
frontend/
├── src/
│   ├── components/       # All UI components
│   ├── App.tsx          # Main application
│   ├── api.ts           # Backend API integration
│   ├── types.ts         # TypeScript interfaces
│   └── index.css        # Global styles
├── package.json
├── vite.config.ts       # Vite configuration with proxy
└── tailwind.config.js   # Tailwind CSS configuration
```

## API Proxy Configuration

The Vite dev server is configured to proxy API requests:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Proxy: `/api/*` → `http://localhost:8000/*`

This means frontend requests to `/api/query/process` are automatically forwarded to `http://localhost:8000/query/process`.

## Customization

### Colors
Edit `tailwind.config.js` to change the color scheme:
```javascript
colors: {
  primary: '#2563eb',    // Main brand color
  secondary: '#64748b',  // Secondary color
  accent: '#0ea5e9',     // Accent color
  // ... more colors
}
```

### API Endpoint
Edit `vite.config.ts` to change the backend URL:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',  // Change this
    // ...
  }
}
```

## Building for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

Preview the production build:
```bash
npm run preview
```

## Troubleshooting

### Backend Connection Issues
- Ensure the backend is running: `docker-compose ps`
- Check backend health: `curl http://localhost:8000/health`
- Verify proxy configuration in `vite.config.ts`

### Port Already in Use
If port 3000 is taken, Vite will automatically use the next available port (3001, 3002, etc.)

### Dependencies Not Installing
- Clear npm cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again

## Next Steps

This is a working prototype. For production, consider:
- Add comprehensive error handling
- Implement loading states
- Add form validation
- Implement authentication
- Add unit and integration tests
- Optimize performance
- Add accessibility features
- Implement responsive design for mobile

## Support

For issues or questions:
1. Check the backend is running and healthy
2. Review browser console for errors
3. Check network tab for failed API requests
4. Verify API endpoints match backend implementation
