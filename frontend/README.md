# PharmaGuide Frontend

A sleek, minimalist desktop prototype for the PharmaGuide AI-powered health companion platform.

## Features

- **Natural Language Query Interface** - Ask questions about medications in plain English
- **Patient Profile Management** - Store and manage patient demographics and medical history
- **Medication List** - Track current medications with dosage and frequency
- **Side Effects Display** - View potential side effects for medications
- **Symptom Tracker** - Log and monitor symptoms over time
- **Alert Notifications** - Receive warnings about drug interactions and contraindications

## Tech Stack

- React 18 with TypeScript
- Vite for fast development and building
- Tailwind CSS for styling
- Axios for API communication

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

The development server includes a proxy that forwards `/api/*` requests to the backend at `http://localhost:8000`.

## Building for Production

Build the production bundle:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Header.tsx
│   │   ├── QueryInterface.tsx
│   │   ├── PatientProfileForm.tsx
│   │   ├── MedicationList.tsx
│   │   ├── SideEffectsDisplay.tsx
│   │   ├── SymptomTracker.tsx
│   │   └── AlertsPanel.tsx
│   ├── App.tsx             # Main app component
│   ├── api.ts              # API client
│   ├── types.ts            # TypeScript types
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## API Integration

The frontend integrates with the following backend endpoints:

- `POST /query/process` - Process natural language queries
- `POST /patient/profile` - Create/update patient profile
- `POST /patient/{id}/medications` - Add medications
- `GET /patient/{id}/medications` - Get medications
- `GET /alerts/active` - Get active alerts
- `POST /alerts/acknowledge/{id}` - Acknowledge alerts
- `POST /patient/{id}/symptoms` - Log symptoms
- `GET /patient/{id}/symptoms` - Get symptoms

## Design Philosophy

This prototype prioritizes:
- **Speed over perfection** - Quick implementation of core features
- **Happy path only** - Minimal error handling for rapid prototyping
- **Clean, minimalist UI** - Professional healthcare aesthetic with plenty of white space
- **Desktop-first** - Optimized for 1920x1080 resolution

## Notes

- This is a prototype focused on core functionality
- Error handling is minimal - production apps should add comprehensive validation
- Mock data is used in some components for demonstration purposes
- All API calls assume the backend is running and accessible

## Future Enhancements

- Add comprehensive error handling and validation
- Implement loading states and skeleton screens
- Add data persistence with local storage
- Implement real-time updates with WebSockets
- Add mobile responsive design
- Enhance accessibility features
- Add unit and integration tests
