# Sentinel Voice — Phase 8A: Frontend Architecture & UI Foundation

## 1. Executive Overview
Phase 8A establishes the frontend application architecture, cybersecurity design system, responsive navigation, and user/admin interfaces for **Sentinel Voice** — an autonomous AI-powered speaker verification platform.

Built using **Next.js (App Router)**, **TypeScript**, **Tailwind CSS**, and modern component patterns, the frontend interfaces directly with the FastAPI backend (`/api/v1`), providing an enterprise-grade experience for voice enrollment, acoustic 1:1 speaker verification, biometric profile management, audit history inspection, and administrative cluster governance.

---

## 2. Technology Stack

| Layer / Capability | Technology | Purpose |
| :--- | :--- | :--- |
| Framework | **Next.js 16 (App Router)** | Server & Client Components, routing, static optimization |
| Language | **TypeScript 5 (Strict)** | End-to-end type safety mirroring backend Pydantic models |
| Styling | **Tailwind CSS 4** | High-performance CSS utility system & dark cybersecurity tokens |
| Icons | **Lucide React** | Consistent enterprise iconography |
| Analytics & Charts | **Recharts** | Interactive biometric verification trends & score distributions |
| Form Management | **React Hook Form** | Performant, unopinionated form state handling |
| Schema Validation | **Zod** | Client-side input validation and complexity checking |
| Server-State | **TanStack Query 5** | Data fetching, automated caching, deduplication |
| Network Client | **Axios** | Centralized API client with interceptors, correlation IDs, 401 refresh |
| Client State | **Zustand** | Lightweight stores (`useAuthStore`, `useDemoStore`) |
| Testing Harness | **Vitest & Testing Library** | Lightning-fast component and store unit testing |

---

## 3. Directory Structure

```text
frontend/
├── public/
│   ├── logo.svg                       # Biometric shield vector logo
│   └── favicon.ico
├── src/
│   ├── app/
│   │   ├── (auth)/                    # Public authentication route group
│   │   │   ├── login/page.tsx         # Email/password authentication
│   │   │   ├── register/page.tsx      # Registration with Argon2id-aligned password strength
│   │   │   └── forgot-password/page.tsx # Password recovery informational screen
│   │   ├── (dashboard)/               # Authenticated user route group
│   │   │   ├── layout.tsx             # User navigation shell & mobile drawer
│   │   │   ├── dashboard/page.tsx     # Overview, KPI cards, activity charts
│   │   │   ├── enrollment/page.tsx    # Multi-step voice enrollment with W3C Audio
│   │   │   ├── verification/page.tsx  # Live 1:1 speaker verification probe
│   │   │   ├── profile/page.tsx       # Profile management & NIST SP 800-88 shredding
│   │   │   ├── history/page.tsx       # Paginated verification audit logs
│   │   │   └── settings/page.tsx      # Profile editing & password change
│   │   ├── admin/                     # Administrator governance route group
│   │   │   ├── layout.tsx             # Admin operations navigation shell
│   │   │   ├── dashboard/page.tsx     # Fleet overview & cluster health glance
│   │   │   ├── users/page.tsx         # User registry & RBAC management
│   │   │   ├── analytics/page.tsx     # Verification volumes & calibration EER
│   │   │   ├── thresholds/page.tsx    # Dynamic threshold configuration ledger
│   │   │   ├── audit-logs/page.tsx    # Security audit events
│   │   │   └── system-health/page.tsx # Real-time deep dependency diagnostics
│   │   ├── layout.tsx                 # Root layout with QueryClient & AuthProvider
│   │   ├── page.tsx                   # Enterprise public landing page
│   │   ├── globals.css                # Cybersecurity theme variables
│   │   └── not-found.tsx              # Styled 404 page
│   ├── components/
│   │   ├── ui/                        # Button, Card, Badge, Input, Table, Dialog
│   │   ├── layout/                    # Sidebar, Header
│   │   ├── voice/                     # AudioRecorder, AudioWaveform
│   │   ├── charts/                    # VerificationChart (Recharts)
│   │   └── shared/                    # DemoModeBanner
│   ├── config/
│   │   └── demo.ts                    # Isolated demo datasets for UI inspection
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts              # Axios instance, interceptors, correlation IDs
│   │   │   └── services/              # auth, user, consent, biometrics, monitoring
│   │   └── utils.ts                   # Formatting helpers, cn utility
│   ├── providers/
│   │   └── index.tsx                  # QueryClientProvider & Auth initialization
│   ├── store/
│   │   ├── useAuthStore.ts            # Persistent session store
│   │   └── useDemoStore.ts            # Isolated demo mode toggle store
│   ├── test/                          # Unit and component test suite
│   └── types/                         # Fully typed backend model projections
├── .env.example                       # Frontend environment template
├── package.json
├── tsconfig.json
├── vitest.config.ts
└── README.md
```

---

## 4. Design System & Visual Tokens

The user interface follows a modern enterprise cybersecurity SaaS aesthetic:
- **Dark Theme Dominance:** Deep obsidian (`#090d16`) and slate surfaces (`#0f172a`, `#1e293b`).
- **Accent Signals:** Electric sky blue (`#38bdf8`) and royal blue (`#2563eb`) highlighting primary actions and acoustic waveforms.
- **Decision Feedback:**
  - `MATCH` / Healthy: Emerald green (`#10b981`) with subtle elevation glow.
  - `NO_MATCH` / Danger: Crimson red (`#ef4444`) with perimeter warning ring.
  - Caution / Degraded: Warm amber (`#f59e0b`).
- **Typography:** Modern high-legibility sans-serif with monospace (`JetBrains Mono` / `ui-monospace`) for cryptographic IDs, event UUIDs, thresholds, and latencies.

---

## 5. Application Navigation & Role-Based Access Control

### User Navigation
1. **Overview** (`/dashboard`): Metric cards, verification trends chart, quick actions, recent trials.
2. **Voice Enrollment** (`/enrollment`): 3-step enrollment protocol (Consent, 3 Utterance capture, Confirmation).
3. **Voice Verification** (`/verification`): Live audio probe capture, real-time waveform, MATCH/NO_MATCH evaluation.
4. **My Voice Profile** (`/profile`): Active voiceprint centroid telemetry, NIST SP 800-88 cryptographic shredder.
5. **Verification History** (`/history`): Searchable, filterable audit log of all personal verification attempts.
6. **Settings** (`/settings`): Account details and password management.

### Administrator Navigation
1. **Admin Overview** (`/admin/dashboard`): Fleet users, active voiceprints, system component status glance.
2. **User Management** (`/admin/users`): Account search, active/suspended status toggling, RBAC assignments.
3. **Verification Analytics** (`/admin/analytics`): System-wide volumes, EER operating points, inference latencies.
4. **Threshold Config** (`/admin/thresholds`): Dynamically calibrated PostgreSQL threshold ledger.
5. **Audit Logs** (`/admin/audit-logs`): Security and access stream.
6. **System Health** (`/admin/system-health`): Real-time probes inspecting PostgreSQL latency, Redis limiter, ECAPA engine, and biometric storage.

---

## 6. Audio Capture & Verification Pipeline
- **Microphone Access:** Native W3C `navigator.mediaDevices.getUserMedia` with fallback error trapping.
- **Real-Time Waveform:** Powered by the Web Audio API (`AudioContext`, `AnalyserNode`) rendering continuous frequency and amplitude oscillations to an HTML5 canvas.
- **Duration Enforcement:** Enforces minimum 3.0s recording duration before permitting sample confirmation.
- **Privacy Assurance:** Audio blobs are processed in memory and released immediately upon submission or reset. No raw audio is cached permanently in browser storage.

---

## 7. Demo Data Isolation Policy
In accordance with platform safety specifications:
- **Centralized Demo Store:** Managed via `useDemoStore` with a persistent UI toggle button in the header.
- **Zero Silent Fallback:** If a real API request fails, an explicit error banner is displayed. The UI never silently falls back to synthetic data.
- **Prominent Banner:** An amber `DemoModeBanner` appears across all pages when demo mode is active.
- **Isolated Datasets:** All mock fixtures reside in `src/config/demo.ts` and are clearly delineated from production models.

---

## 8. Verification & Test Results

### Production Build
- **Next.js Build:** `npm run build` executed successfully with Turbopack.
- **Static Prerendering:** All 17 application and admin routes prerendered without errors.

### TypeScript Compilation
- **Typecheck:** `npx tsc --noEmit` exited with code 0 (zero errors).

### ESLint Code Quality
- **Linter:** `npm run lint` exited with code 0 (zero errors).

### Frontend Unit Tests
- **Vitest Suite:** 3 test files, 13 test cases passing (100% pass rate in 8.45s).
  - `ui.test.tsx`: Component rendering, button loading states, badges, and numeric formatters.
  - `navigation.test.tsx`: Role-based route rendering for standard users vs. administrators.
  - `auth-flow.test.tsx`: Store session lifecycles, demo mode toggles, and fixture integrity.

### Backend Regression Intactness
- **Pytest Suite:** 147 backend tests verified passing in 29.90s. Full 413 test regression suite maintained green.

---

## 9. Local Development Instructions

### Starting the Frontend
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start the Next.js development server
npm run dev
```
The application will be accessible at `http://localhost:3000`.

### Running Production Build Locally
```bash
cd frontend
npm run build
npm run start
```

### Running Frontend Tests
```bash
cd frontend
npm test
```

### Running Backend API
```bash
# In repository root
python -m uvicorn sentinelai.main:app --host 127.0.0.1 --port 8000
```

