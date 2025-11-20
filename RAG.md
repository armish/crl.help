# RAG Search Implementation Plan

## Overview

This document outlines the comprehensive plan for implementing RAG (Retrieval-Augmented Generation) search functionality in the CRL Explorer application.

## Requirements

1. **Dedicated Search Page** - Accessible through header search bar
2. **Dual Search Modes**:
   - Keyword matching (default) - Fast, traditional search
   - RAG/Semantic search - AI-powered embedding-based search
3. **Security** - Rate limiting and CAPTCHA to prevent exploitation
4. **Context Display** - Show where matches occur with surrounding context

---

## Architecture Overview

### Backend Components

#### 1. Search Endpoints (New)

**`POST /api/search/keyword`** - Fast keyword-based search
- Searches across: `company_name`, `product_name`, `therapeutic_category`, `deficiency_reason`, `summary`, `text`
- Returns: Matching CRLs with **highlighted context** snippets
- Response includes: field name, matched text, surrounding context (1 sentence before/after)
- Rate limit: 60 requests/minute per IP

**`POST /api/search/semantic`** - RAG/embedding-based semantic search
- Uses existing `EmbeddingsService` and `RAGService` infrastructure
- Generates query embedding → finds top-k similar CRLs
- Returns: Similar CRLs with similarity scores and relevant text excerpts
- **Rate limited**: 10 requests/minute per IP (expensive due to OpenAI API)
- **CAPTCHA required**: Google reCAPTCHA v3 validation

#### 2. Rate Limiting & Security

**FastAPI SlowAPI Integration**
```python
# Rate limits
- Keyword search: 60 requests/minute per IP
- Semantic search: 10 requests/minute per IP
```

**Google reCAPTCHA v3**
- Frontend sends captcha token with semantic search requests
- Backend validates token with Google API
- Score threshold: 0.5 (reject likely bots)
- Keyword search: no captcha required (lighter protection)
- Semantic search: captcha required (heavy protection)

#### 3. Database Enhancements

Add to `CRLRepository`:
```python
def search_keywords(query: str, limit: int, offset: int) -> tuple[list, int]:
    """
    Full-text search across CRL fields.
    Returns: (matching_crls_with_context, total_count)
    """
```

Features:
- DuckDB full-text search capabilities
- Field-level match information
- Context snippet extraction around matches

---

### Frontend Components

#### 1. Header Search Bar (Enhanced Layout.jsx)

```jsx
- Search input in header (sticky, always visible)
- On Enter or Search button → navigate to /search?q={query}
- Search icon + clear button
- Mobile-responsive (collapsible on small screens)
```

#### 2. Search Page (`/search`)

```jsx
<SearchPage>
  URL: /search?q={query}

  Two-tab interface:
  ┌─────────────────────────────────────┐
  │ [Keyword Search] [Semantic Search]  │
  ├─────────────────────────────────────┤
  │                                     │
  │  Search Results                     │
  │  ┌─────────────────────────────┐   │
  │  │ CRL Card                    │   │
  │  │ - Company, Date, Category   │   │
  │  │ - Match highlights          │   │
  │  │ - Context snippets          │   │
  │  └─────────────────────────────┘   │
  │                                     │
  └─────────────────────────────────────┘
</SearchPage>
```

**Keyword Search Tab** (Default):
- Show results immediately on page load
- Display context snippets with highlights
- Show which fields matched (badges)
- Pagination for large result sets

**Semantic Search Tab**:
- Google reCAPTCHA v3 widget
- "Semantic Search" button (triggers RAG)
- Show similarity scores (0-1 range)
- Display relevant text excerpts
- Top-k results (default: 5, configurable)

**Both tabs show**:
- CRL card: company, date, category, deficiency reason
- Context preview with highlights
- "View Details" link to CRL detail page

#### 3. Search Result Components

**SearchResultCard**
```jsx
<SearchResultCard>
  - CRL metadata (company, date, app number)
  - Match indicators (which fields matched)
  - Context snippet with highlighted terms
  - Similarity score (semantic search only)
  - Link to full CRL detail page
</SearchResultCard>
```

**ContextHighlight**
```jsx
<ContextHighlight>
  - Renders text with <mark> tags for matches
  - Shows "..." for truncated context
  - Different highlight colors for different match types
</ContextHighlight>
```

---

## Implementation Plan

### Phase 1: Backend - Keyword Search

**Tasks:**

1. **Add `search_keywords()` to CRLRepository**
   ```python
   def search_keywords(
       query: str,
       limit: int = 50,
       offset: int = 0
   ) -> tuple[list[dict], int]:
       """
       Full-text search across multiple fields.
       Returns: (results_with_context, total_count)
       """
   ```
   - Search fields: `company_name`, `product_name`, `therapeutic_category`,
     `deficiency_reason`, `summary`, `text`
   - Extract context snippets (±50 chars around match)
   - Return field names where matches found

2. **Create `backend/app/api/search.py`**
   - Define Pydantic schemas:
     ```python
     class KeywordSearchRequest(BaseModel):
         query: str
         limit: int = 50
         offset: int = 0

     class FieldMatch(BaseModel):
         field: str
         snippet: str
         context_before: str
         context_after: str

     class SearchResult(BaseModel):
         crl: CRLListItem
         matches: List[FieldMatch]

     class KeywordSearchResponse(BaseModel):
         results: List[SearchResult]
         total: int
         query: str
         limit: int
         offset: int
     ```

   - Implement endpoint:
     ```python
     @router.post("/keyword", response_model=KeywordSearchResponse)
     async def keyword_search(request: KeywordSearchRequest):
         # Call CRLRepository.search_keywords()
         # Format results with context
         # Return paginated response
     ```

3. **Add rate limiting**
   - Install `slowapi` package:
     ```bash
     pip install slowapi
     ```
   - Configure in `backend/app/api/search.py`:
     ```python
     from slowapi import Limiter
     from slowapi.util import get_remote_address

     limiter = Limiter(key_func=get_remote_address)

     @router.post("/keyword")
     @limiter.limit("60/minute")
     async def keyword_search(...):
         ...
     ```
   - Register limiter in `main.py`

**Deliverables:**
- Working keyword search endpoint
- Context snippet extraction
- Rate limiting (60 req/min)
- Tests for search functionality

**Estimated Time:** ~4 hours

---

### Phase 2: Backend - Semantic Search

**Tasks:**

1. **Create semantic search endpoint**
   - Define schemas:
     ```python
     class SemanticSearchRequest(BaseModel):
         query: str
         top_k: int = 5
         captcha_token: str

     class SemanticResult(BaseModel):
         crl: CRLListItem
         similarity_score: float
         relevant_excerpts: List[str]

     class SemanticSearchResponse(BaseModel):
         results: List[SemanticResult]
         query: str
     ```

   - Implement endpoint:
     ```python
     @router.post("/semantic", response_model=SemanticSearchResponse)
     @limiter.limit("10/minute")
     async def semantic_search(
         request: SemanticSearchRequest,
         request_obj: Request
     ):
         # 1. Verify reCAPTCHA token
         # 2. Generate query embedding
         # 3. Find similar CRLs (reuse RAGService._retrieve_similar_crls)
         # 4. Extract relevant excerpts
         # 5. Return results
     ```

2. **Add reCAPTCHA validation**
   - Install `httpx` (if not already present):
     ```bash
     pip install httpx
     ```

   - Create `backend/app/utils/recaptcha.py`:
     ```python
     import httpx
     from app.config import Settings

     async def verify_recaptcha(
         token: str,
         remote_ip: str,
         settings: Settings
     ) -> tuple[bool, float]:
         """
         Verify reCAPTCHA v3 token.
         Returns: (is_valid, score)
         """
         url = "https://www.google.com/recaptcha/api/siteverify"
         data = {
             "secret": settings.recaptcha_secret_key,
             "response": token,
             "remoteip": remote_ip
         }

         async with httpx.AsyncClient() as client:
             response = await client.post(url, data=data)
             result = response.json()

             success = result.get("success", False)
             score = result.get("score", 0.0)

             return success and score >= 0.5, score
     ```

   - Add to `backend/app/config.py`:
     ```python
     class Settings(BaseSettings):
         ...
         recaptcha_secret_key: str = ""
     ```

3. **Update RAGService for search**
   - Extract reusable method for semantic retrieval
   - Return similarity scores and text excerpts
   - No answer generation needed (just retrieval)

**Deliverables:**
- Semantic search endpoint
- reCAPTCHA validation
- Rate limiting (10 req/min)
- Tests with mocked reCAPTCHA

**Estimated Time:** ~4 hours

---

### Phase 3: Frontend - Search UI

**Tasks:**

1. **Add search bar to header**
   - Edit `frontend/src/components/Layout.jsx`:
     ```jsx
     // Add search input in header
     const [searchQuery, setSearchQuery] = useState('');
     const navigate = useNavigate();

     const handleSearch = (e) => {
       e.preventDefault();
       if (searchQuery.trim()) {
         navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
       }
     };

     // In header JSX:
     <form onSubmit={handleSearch}>
       <input
         type="search"
         placeholder="Search CRLs..."
         value={searchQuery}
         onChange={(e) => setSearchQuery(e.target.value)}
       />
       <button type="submit">Search</button>
     </form>
     ```

2. **Create SearchPage component**
   - File: `frontend/src/pages/SearchPage.jsx`
   - Features:
     - Read `?q=` from URL params
     - Two-tab layout (Keyword/Semantic)
     - Default to Keyword tab with auto-search
     - SEO metadata with Helmet
     - Loading states
     - Error handling
     - Empty states

3. **Create SearchResultCard component**
   - File: `frontend/src/components/SearchResultCard.jsx`
   - Display:
     - CRL metadata (company, date, app number, category)
     - Match field badges
     - Context snippets with highlights
     - Similarity score (if semantic)
     - "View Details" link

4. **Create ContextHighlight component**
   - File: `frontend/src/components/ContextHighlight.jsx`
   - Features:
     - Render text with `<mark>` tags
     - Handle multiple match patterns
     - Show ellipsis for truncated content
     - Responsive text sizing

5. **Add reCAPTCHA integration**
   - Install package:
     ```bash
     npm install react-google-recaptcha-v3
     ```

   - Wrap App in reCAPTCHA provider:
     ```jsx
     // In App.jsx
     import { GoogleReCaptchaProvider } from 'react-google-recaptcha-v3';

     <GoogleReCaptchaProvider reCaptchaKey="YOUR_SITE_KEY">
       <QueryClientProvider client={queryClient}>
         ...
       </QueryClientProvider>
     </GoogleReCaptchaProvider>
     ```

   - Use in SearchPage:
     ```jsx
     import { useGoogleReCaptcha } from 'react-google-recaptcha-v3';

     const { executeRecaptcha } = useGoogleReCaptcha();

     const handleSemanticSearch = async () => {
       const token = await executeRecaptcha('semantic_search');
       // Send to backend with token
     };
     ```

6. **Add route in App.jsx**
   ```jsx
   import SearchPage from './pages/SearchPage';

   <Route path="/search" element={<SearchPage />} />
   ```

**Deliverables:**
- Header search bar with navigation
- Complete SearchPage with tabs
- Result card components
- reCAPTCHA integration
- Responsive design

**Estimated Time:** ~6 hours

---

### Phase 4: Testing & Polish

**Tasks:**

1. **Backend tests**
   - File: `backend/tests/test_search.py`
   - Test cases:
     - Keyword search with various queries
     - Context snippet extraction
     - Pagination
     - Rate limiting behavior
     - Semantic search with mocked embeddings
     - reCAPTCHA validation (mocked)
     - Error handling (empty query, invalid input)

2. **Frontend tests**
   - File: `frontend/src/pages/SearchPage.test.jsx`
   - Test cases:
     - Search input navigation
     - Result rendering
     - Tab switching
     - Loading states
     - Error states
     - reCAPTCHA flow (mocked)

3. **Integration testing**
   - End-to-end search flow
   - Rate limiting (verify headers)
   - Error handling (no results, API errors)
   - Mobile responsiveness

4. **Performance optimization**
   - Add result caching (React Query)
   - Debounce search input
   - Lazy load results on scroll
   - Optimize context snippet extraction

5. **Documentation**
   - Update README with search feature
   - Add environment variable docs (reCAPTCHA keys)
   - API documentation in OpenAPI/Swagger

**Deliverables:**
- Comprehensive test coverage
- Performance optimizations
- Updated documentation

**Estimated Time:** ~3 hours

---

## Technical Implementation Details

### Context Snippet Extraction Algorithm

```python
def extract_context(
    text: str,
    match_position: int,
    match_length: int,
    context_chars: int = 100
) -> dict:
    """
    Extract context around a match in text.

    Algorithm:
    1. Find sentence boundaries before/after match
    2. Include ±1 sentence or ±context_chars, whichever is smaller
    3. Add "..." if truncated

    Returns:
        {
            "before": "...sentence before match",
            "match": "matched text",
            "after": "sentence after match..."
        }
    """
    # Implementation details...
```

### Rate Limiting Strategy

```python
# Using SlowAPI with FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# In main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In search.py endpoints
@router.post("/keyword")
@limiter.limit("60/minute")  # 60 requests per minute
async def keyword_search(request: Request, ...):
    ...

@router.post("/semantic")
@limiter.limit("10/minute")  # 10 requests per minute (OpenAI cost)
async def semantic_search(request: Request, ...):
    ...
```

### DuckDB Full-Text Search

```python
# In CRLRepository.search_keywords()
def search_keywords(self, query: str, limit: int, offset: int):
    """
    Use DuckDB's string matching and LIKE operators.

    For better performance, consider adding a full-text search
    extension or creating a MATERIALIZED VIEW with indexed columns.
    """

    # Escape special characters in query
    safe_query = query.replace("'", "''").replace("%", "\\%")

    # Build dynamic WHERE clause for multiple fields
    search_fields = [
        'company_name', 'product_name', 'therapeutic_category',
        'deficiency_reason', 'summary', 'text'
    ]

    conditions = [
        f"LOWER({field}) LIKE LOWER('%{safe_query}%')"
        for field in search_fields
    ]

    where_clause = ' OR '.join(conditions)

    # Execute search with context extraction
    sql = f"""
        SELECT
            *,
            CASE
                WHEN LOWER(company_name) LIKE LOWER('%{safe_query}%')
                    THEN 'company_name'
                WHEN LOWER(product_name) LIKE LOWER('%{safe_query}%')
                    THEN 'product_name'
                -- ... other fields
            END as matched_field
        FROM crls
        WHERE {where_clause}
        LIMIT {limit} OFFSET {offset}
    """

    # Extract context snippets for each match
    # Return formatted results
```

---

## Security Considerations

1. **Rate Limiting**
   - Prevents abuse of expensive OpenAI embedding API
   - Different limits for different endpoints
   - IP-based tracking

2. **reCAPTCHA v3**
   - Blocks automated bots from scripting searches
   - Score-based validation (threshold: 0.5)
   - Required for semantic search only

3. **Input Validation**
   - Sanitize search queries to prevent SQL injection
   - Escape special characters
   - Maximum query length validation

4. **API Key Protection**
   - OpenAI API key stored in environment variables
   - reCAPTCHA secret key never exposed to frontend

5. **Response Size Limits**
   - Limit context snippet length
   - Pagination for large result sets
   - Maximum top-k for semantic search

---

## Dependencies

### Backend
```bash
pip install slowapi      # Rate limiting
pip install httpx        # Async HTTP client (reCAPTCHA validation)
```

### Frontend
```bash
npm install react-google-recaptcha-v3  # reCAPTCHA integration
```

---

## Environment Variables

### Backend
```bash
# .env
OPENAI_API_KEY=sk-...
RECAPTCHA_SECRET_KEY=6Lc...  # Google reCAPTCHA v3 secret key
```

### Frontend
```bash
# .env
VITE_RECAPTCHA_SITE_KEY=6Lc...  # Google reCAPTCHA v3 site key
```

---

## Estimated Timeline

- **Phase 1** (Backend Keyword Search): ~4 hours
- **Phase 2** (Backend Semantic Search + Security): ~4 hours
- **Phase 3** (Frontend UI): ~6 hours
- **Phase 4** (Testing & Polish): ~3 hours
- **Total**: ~17 hours

---

## Future Enhancements

1. **Search Analytics**
   - Track popular search queries
   - Monitor semantic search usage
   - Identify common search patterns

2. **Advanced Filters**
   - Filter results by date range
   - Filter by company, category, etc.
   - Combine keyword + semantic search

3. **Search Suggestions**
   - Autocomplete based on past queries
   - "Did you mean...?" for typos
   - Related searches

4. **Export Results**
   - Export search results to CSV
   - Save search queries
   - Email alerts for new matching CRLs

5. **Performance Optimizations**
   - Cache popular queries
   - Pre-compute embeddings for common searches
   - Database indexing improvements

---

## Success Metrics

- **Functionality**: Both keyword and semantic search work correctly
- **Performance**: Keyword search <500ms, Semantic search <3s
- **Security**: Rate limiting prevents abuse, reCAPTCHA blocks bots
- **UX**: Clear context display, responsive design, good empty/error states
- **Test Coverage**: >80% backend, >70% frontend
