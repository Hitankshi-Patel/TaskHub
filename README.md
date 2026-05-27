# TaskHub

A product photography automation platform for jewellery e-commerce teams. Admins upload product images and assign tasks to photographers/designers. The assigned user triggers AI-powered image generation to produce professional product shots — studio backgrounds, themed environments, and model-wearing-jewellery images — directly from the dashboard. Admins review, request revisions, or accept the final set.

---

## Table of Contents

- [Generated Samples](#generated-samples)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Database & Migration](#database--migration)
- [AI Image Generation Approach](#ai-image-generation-approach)
- [Deployment](#deployment)
- [Known Limitations](#known-limitations)

---

## Generated Samples

All five images below are generated from the same product photo of a gold diamond ring stack. The background is removed locally using the U2Net ONNX model, then the product is composited onto each background using Pillow.

**Image 1 — Studio White**
Clean white `#FFFFFF` canvas with a soft Gaussian drop shadow. Standard e-commerce catalogue format.

![Studio White](generated_samples/composite_white_background.jpg.jpeg)

---

**Image 2 — Marble Theme**
Real marble surface photograph sourced from Unsplash (`white marble luxury surface flat lay`). Conveys luxury and premium retail positioning.

![Marble Theme](generated_samples/composite_theme_1.jpg.jpeg)

---

**Image 3 — Velvet Theme**
Deep velvet fabric texture from Unsplash (`dark navy velvet fabric texture product photography`). Rich contrast against the gold tones of the jewellery.

![Velvet Theme](generated_samples/composite_theme_2.jpg.jpeg)

---

**Image 4 — Beach Sunset (Creative)**
Golden hour beach photograph from Unsplash with background blur applied. Lifestyle-oriented editorial feel.

![Beach Sunset Creative](generated_samples/composite_creative_1.jpg.jpeg)

---

**Image 5 — Rose Garden (Creative)**
Soft-bokeh rose garden from Unsplash with background blur. Romantic and fashion-editorial aesthetic.

![Rose Garden Creative](generated_samples/composite_creative_2.jpg.jpeg)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Browser / Client                    │
│              Next.js 14 (App Router) — Vercel           │
│                                                         │
│  Login (Google / GitHub OAuth via Firebase)             │
│  Admin Dashboard   →  Task Management, Analytics        │
│  User Dashboard    →  Task View, AI Image Generation    │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS REST API
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Flask REST API — Vercel (Serverless)        │
│                                                         │
│  Firebase Admin SDK   →  Token verification             │
│  Flask-SQLAlchemy     →  ORM for all DB models          │
│  Flask-Limiter        →  Rate limiting (100 req/min)    │
│  Background Worker    →  Threaded AI generation jobs    │
│  Resend               →  Email notifications            │
└──────────┬─────────────────────────┬────────────────────┘
           │                         │
           ▼                         ▼
  ┌─────────────────┐     ┌─────────────────────────────┐
  │  Supabase        │     │  External Services           │
  │  PostgreSQL DB   │     │                             │
  │  Storage Bucket  │     │  Unsplash API (backgrounds) │
  │  (image hosting) │     │  Google Gemini Flash (model)│
  └─────────────────┘     └─────────────────────────────┘
```

### Request Flow

1. User signs in with Google/GitHub via Firebase — the browser receives a short-lived Firebase ID token.
2. The frontend POSTs the token to `/api/auth/oauth/callback`. The backend verifies it with Firebase Admin SDK, creates or retrieves the user in Postgres, and returns the profile.
3. Every subsequent API call sends the token in `Authorization: Bearer` — verified on every protected route.
4. When a user triggers image generation, the backend spawns a background thread, runs the full pipeline, uploads results to Supabase Storage, and saves URLs to the database. The frontend polls `/api/jobs/{id}/status` for progress.

### Database Models

| Table | Description |
|---|---|
| `users` | Firebase UID, email, name, role (`admin` / `user`) |
| `tasks` | Title, product image URL, status, assignment, feedback, rembg cache path |
| `generated_images` | URL, type, prompt used, angle, finality flag — linked to task |
| `audit_logs` | Full change history for all create/assign/accept/revision events |

### Task Status Flow

```
pending → assigned → in_progress → submitted → accepted
                                 ↘ revision_requested → in_progress
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Vanilla CSS |
| Auth | Firebase Authentication (Google, GitHub OAuth) |
| Backend | Python 3.11, Flask, Flask-SQLAlchemy, Flask-CORS, Flask-Limiter |
| Database | PostgreSQL via Supabase (Transaction Pooler for serverless) |
| File Storage | Supabase Storage (public bucket) |
| Background removal | U2Net ONNX via onnxruntime — runs fully locally, no API |
| Backgrounds (themes) | Unsplash API — real photographs (free tier available) |
| White background | Pure Pillow — zero API, zero cost |
| Model shots | Google Gemini Flash (`gemini-3.1-flash-image-preview`) — native image output |
| Email | Resend API |
| Deployment | Vercel (both frontend and backend) |

---

## Local Setup

### Prerequisites

- Node.js 18+
- Python 3.10+
- A Supabase project (free tier works)
- A Firebase project with Google Sign-in enabled
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Hitankshi-Patel/TaskHub.git
cd TaskHub
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the environment file and fill in your values
cp .env.example .env
```

Edit `backend/.env` with your credentials (see [Environment Variables](#environment-variables) below).

Run the backend:

```bash
# From the project root
python -m backend.app
# Backend starts at http://localhost:5000
```

### 3. Frontend setup

```bash
cd frontend

npm install

cp .env.example .env.local
```

Edit `frontend/.env.local` with your credentials.

```bash
npm run dev
# Frontend starts at http://localhost:3000
```

### 4. First login

- Open `http://localhost:3000` and sign in with Google.
- The **first user to sign in** is automatically assigned the `admin` role.
- All subsequent users are assigned `user` role.

---

## Environment Variables

### Backend — `backend/.env`

```env
SECRET_KEY=your-flask-secret-key
FLASK_DEBUG=True
PORT=5000

# Supabase Transaction Pooler URL (port 6543) — NOT the direct connection (port 5432).
# Direct connection uses IPv6 which Vercel serverless cannot reach.
# Special chars in password must be URL-encoded: @ → %40,  & → %26,  # → %23
DATABASE_URL=postgresql://postgres.xxxxx:your-password@aws-0-region.pooler.supabase.com:6543/postgres

SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Unsplash — used for photographic backgrounds (theme_1, theme_2, creative_1, creative_2)
# Free at https://unsplash.com/developers (50 requests/hour on free tier)
UNSPLASH_ACCESS_KEY=your-unsplash-access-key

# Google AI Studio — used for model-wearing-jewellery image generation
# Free key at https://aistudio.google.com/apikey
# gemini-3.1-flash-image-preview has a free quota (2 images/min on free tier)
GEMINI_API_KEY=AIza...

# Resend — email notifications on task assignment/acceptance/revision
RESEND_API_KEY=re_your_key
EMAIL_FROM=TaskHub <notifications@yourdomain.com>

# Firebase Admin SDK
FIREBASE_PROJECT_ID=your-firebase-project-id
# Local development — path to the service account JSON file
FIREBASE_CREDENTIALS_PATH=./taskhub-firebase-adminsdk.json
# Production (Vercel) — paste the full JSON as a single-line string
# FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":...}
```

### Frontend — `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:5000

NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-firebase-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=G-XXXXXXXX
```

---

## Database & Migration

### Automatic table creation

SQLAlchemy creates all tables on the first request to `/api/health`. No manual migration step is needed for a fresh setup.

### Adding or changing a column

The project does not use Alembic. Schema changes must be run manually in the Supabase SQL editor.

**Add a column:**
```sql
ALTER TABLE tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'normal';
```

**Add a table:**
```sql
CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Then add the corresponding SQLAlchemy model class in `backend/models.py`. The `/api/health` endpoint calls `db.create_all()` which picks up new models automatically.

> To add proper versioned migrations in the future: `pip install alembic && alembic init migrations` from the `backend/` directory.

---

## AI Image Generation Approach

### Pipeline overview

Each task generates up to **8 images** across 3 categories:

```
Product image URL (from task)
        ↓
[Step 0 — rembg, local ONNX]  Extract transparent PNG (runs once, cached to disk)
        ↓
┌────────────────────────────────────────────────────────────────┐
│  Image 1: White background   → Pure Pillow (#FFFFFF canvas)   │
│  Image 2: Marble theme       → Unsplash photo + Pillow        │
│  Image 3: Velvet theme       → Unsplash photo + Pillow        │
│  Image 4: Beach creative     → Unsplash photo + Pillow blur   │
│  Image 5: Floral creative    → Unsplash photo + Pillow blur   │
│  Image 6: Model front view   → Gemini Flash (native image)    │
│  Image 7: Model side view    → Gemini Flash + Image 6 anchor  │
│  Image 8: Model close-up     → Gemini Flash + Image 6 anchor  │
└────────────────────────────────────────────────────────────────┘
        ↓
[Upload to Supabase Storage → Save URL to DB]
```

### Key design decisions

**The product is never AI-generated.** For images 1–5, the product is extracted (rembg) and composited onto a background using Pillow. This preserves every pixel of the original product — no AI distortion, no hallucinated details.

**Background removal is fully local.** rembg runs the U2Net ONNX model locally via onnxruntime. The model file (~176 MB) downloads once on first use and is cached. No API key required, no cost.

**Photographic backgrounds are real photos.** Unsplash serves actual photographs (marble surfaces, velvet fabric, beach scenes, rose gardens) — not AI-generated backgrounds. This gives far more realistic product photography than any generative model produces for backgrounds.

**Model shots use Gemini Flash native image output.** `gemini-3.1-flash-image-preview` generates full images in response to multimodal prompts. The product image and a detailed jewellery description are sent alongside each prompt. Image 6 (front view) becomes an "anchor" — it is passed back to Gemini as a reference image for Images 7 and 8 to maintain model consistency across the three shots.

**rembg result is cached per task.** ONNX inference takes 5–15 seconds. After the first image in a batch, the transparent PNG is saved to `/tmp/rembg_cache/{task_id}.png` and reused for all subsequent images in the same task.

### AI APIs explored — honest account

The original goal was to generate a photorealistic model visibly *wearing* the actual jewellery product in the image. Every viable approach was evaluated:

| API / Approach | What was tried | Real outcome |
|---|---|---|
| **Replicate — SDXL Inpainting** | Inpaint the jewellery product onto a model image | Consistently distorted the jewellery shape — unacceptable for catalogue use |
| **Replicate — lucataco/remove-bg** | Background removal | Worked — was used in an earlier version, replaced by local rembg |
| **FAL AI** | Image-to-image with jewellery reference | Billing required before the first request despite "free credits" on the website |
| **FLUX (via Replicate / FAL)** | Text-to-image with product image conditioning | Documented as having free credits; in practice no free inference quota existed |
| **Google Gemini Imagen 3** (`imagen-3.0-generate-001`) | Photorealistic background generation | Works — but Imagen 3 requires billing-enabled account; cannot place product on model |
| **Google Gemini Flash** (`gemini-3.1-flash-image-preview`) | Native multimodal image generation, model wearing jewellery | **Current implementation** — free quota available (2 img/min), generates model shots with jewellery description |
| **Fully free open-source models** | Stable Diffusion local, HuggingFace hosted endpoints | Output quality was not acceptable for jewellery e-commerce photography |

**The hard reality of "free" AI image APIs:** Every major API — Replicate, FAL, FLUX, Gemini Imagen — appears prominently in Google search results with mentions of free tiers, free credits, or generous free quotas. In every case, image generation endpoints either had no free quota at all, or required a billing account to be set up before the first successful request. The only truly free option found that produces acceptable quality for this use case is Gemini Flash's native image output via the AI Studio free tier.

**Current model — Gemini Flash with free quota:** `gemini-3.1-flash-image-preview` is available on the Google AI Studio free tier with a rate limit of 2 images per minute. The pipeline sleeps 35 seconds between model shot generations to respect this limit. The API key is read from the `GEMINI_API_KEY` environment variable at runtime — no code change is needed to swap keys or upgrade to a paid plan.

---

## Deployment

### Backend (Vercel)

`backend/vercel.json` configures Vercel's Python runtime to serve Flask.

Environment variables to set in Vercel dashboard:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Supabase **Transaction Pooler** URL (port 6543, URL-encoded password) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full JSON contents of the Firebase service account file, as one string |
| `GEMINI_API_KEY` | From aistudio.google.com — free tier works |
| `UNSPLASH_ACCESS_KEY` | From unsplash.com/developers — free tier (50 req/hr) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | From Supabase project settings |
| `RESEND_API_KEY` | From resend.com |

> **Important:** Use the Supabase Transaction Pooler URL (port **6543**). The direct connection (port 5432) resolves to an IPv6 address that Vercel serverless functions cannot reach.

### Frontend (Vercel)

All `NEXT_PUBLIC_*` variables must be set in the Vercel frontend project's environment settings. They are baked into the build at compile time — a full redeploy is required after changing any of them.

Set `NEXT_PUBLIC_API_URL` to your deployed backend URL (e.g. `https://task-hub-backend-nu.vercel.app`).

### Firebase — authorise your production domain

Firebase Console → Authentication → Settings → **Authorized domains** → add your Vercel frontend domain (e.g. `taskhub-1.vercel.app`). Without this step, Google/GitHub Sign-in is blocked.

### Cross-Origin Opener Policy (COOP)

`frontend/next.config.ts` sets `Cross-Origin-Opener-Policy: same-origin-allow-popups` on all pages. This is required for Firebase `signInWithPopup` to work — Vercel's default `same-origin` COOP policy blocks the Google auth popup from posting its result back to the parent tab.

---

## Known Limitations

- **Model shots with actual product worn:** The pipeline generates a model scene using a *text description* of the jewellery, not the actual product image placed on the model. Accurate photorealistic inpainting of a specific product onto a model remains unsolved at the quality required for catalogue use — see [AI APIs explored](#ai-apis-explored--honest-account) above.

- **rembg on Vercel serverless:** The U2Net ONNX model (~176 MB) must download to `/tmp` on first use. This can cause the first generation on a cold Vercel instance to time out. Subsequent calls within the same warm instance use the cached model. On a self-hosted server this is not an issue.

- **Unsplash free tier:** The free Unsplash API key is limited to 50 requests per hour. For high-volume usage, upgrade to a production Unsplash key (requires application review).

- **Gemini Flash free tier rate limit:** 2 images per minute. Generating all 3 model shots therefore takes approximately 75–80 seconds (including the mandatory 35-second sleeps). A paid Gemini API key removes this rate limit.

- **No persistent job queue:** Generation jobs are stored in an in-memory Python dictionary in `worker.py`. Vercel serverless is stateless — a job started in one function invocation cannot be queried from a different invocation. For production scale, migrate to a queue backed by the Supabase `tasks` table or a managed service.

- **No versioned migrations:** Schema changes require manual SQL in the Supabase SQL editor. Suitable for the current scale; replace with Alembic before significant production data exists.

- **Vercel cold starts:** First request after a period of inactivity takes 3–5 seconds as the Python environment initialises.
