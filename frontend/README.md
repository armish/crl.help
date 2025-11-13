# FDA CRL Explorer - Frontend

React frontend for exploring FDA Complete Response Letters with AI-powered insights.

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **TanStack Query (React Query v5)** - Data fetching and caching
- **TanStack Table** - Powerful table component (Phase 9)
- **Axios** - HTTP client
- **Zustand** - Lightweight state management
- **React Router** - Client-side routing (Phase 9)

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── Layout.jsx       # Main layout with header/footer
│   ├── pages/               # Page components
│   │   └── HomePage.jsx     # Main homepage with stats
│   ├── services/            # API and data fetching
│   │   ├── api.js           # Axios instance with interceptors
│   │   └── queries.js       # React Query hooks
│   ├── store/               # State management
│   │   └── filterStore.js   # Zustand store for filters
│   ├── App.jsx              # Root component with providers
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles with Tailwind
├── vite.config.js           # Vite configuration with API proxy
├── tailwind.config.js       # Tailwind CSS configuration
└── package.json             # Dependencies
```

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### API Proxy

The Vite dev server proxies API requests to the backend:
- `/api/*` → `http://localhost:8000/api/*`
- `/health` → `http://localhost:8000/health`

This avoids CORS issues during development.

## Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build production bundle
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint (if configured)

## Features Implemented (Phase 8)

### ✅ Foundation
- [x] Vite + React project initialization
- [x] Tailwind CSS configuration
- [x] React Query setup for data fetching
- [x] Axios client with error handling
- [x] Zustand store for filter state
- [x] API proxy configuration
- [x] Main layout component
- [x] Homepage with statistics cards

### 🔄 Coming in Phase 9
- [ ] CRL table with TanStack Table
- [ ] Filter panel (approval status, year, company, search)
- [ ] Pagination controls
- [ ] Detail modal for individual CRLs
- [ ] Q&A panel for RAG-powered questions

## React Query Hooks

All API interactions are handled through custom hooks in `src/services/queries.js`:

- `useCRLs(params)` - Fetch paginated CRL list with filters
- `useCRL(id)` - Fetch single CRL with summary
- `useCRLText(id)` - Fetch CRL with full letter text
- `useStats()` - Fetch overall statistics
- `useCompanies(limit)` - Fetch company statistics
- `useAskQuestion()` - Mutation for Q&A
- `useQAHistory(limit)` - Fetch Q&A history
- `useHealth()` - Backend health check

## Zustand Store

Filter state is managed with Zustand (`src/store/filterStore.js`):

```javascript
import useFilterStore from './store/filterStore';

// In component:
const { filters, setFilter, clearFilters } = useFilterStore();
const queryParams = useQueryParams(); // Get all params for API
```

## API Client

Axios instance in `src/services/api.js` provides:
- Automatic error handling
- Request/response logging in development
- Consistent error structure
- 30-second timeout

## Styling

Uses Tailwind CSS with custom configuration:
- Light gray background (`bg-gray-50`)
- Responsive design with mobile-first approach
- Consistent spacing and typography
- Card-based layouts for components

## Environment Variables

Create `.env` file if needed (currently not used, but available for future):

```env
VITE_API_URL=http://localhost:8000  # Override API URL if needed
```

## Production Build

```bash
npm run build
```

Outputs optimized bundle to `dist/` directory.

To preview:
```bash
npm run preview
```

## Next Steps (Phase 9)

1. **CRL Table Component**
   - Implement with TanStack Table
   - Add sorting, filtering, pagination
   - Row click to open detail modal

2. **Filter Panel**
   - Dropdowns for approval status, year, company
   - Search input with debouncing
   - Clear filters button

3. **Detail Modal**
   - Show full CRL metadata
   - Display AI summary prominently
   - Full letter text (expandable)

4. **Q&A Panel**
   - Question input with submit
   - Display answer with citations
   - Show relevant CRLs

---

*Phase 8 Foundation Complete - Ready for Phase 9 Core Features*
