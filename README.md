# VeraDeep


Video, ses ve metin verilerini birlikte analiz ederek LLM desteğiyle deepfake güvenilirlik skoru üretir.

---

## Proje Yapısı

```
veradeep/
├── frontend/   # Next.js 16 + TypeScript + Tailwind CSS
└── backend/    # FastAPI + Python
```

---

## Kurulum

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

> `http://localhost:3000` üzerinde çalışır.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

> `http://localhost:8000` üzerinde çalışır. Swagger UI: `http://localhost:8000/docs`

---

