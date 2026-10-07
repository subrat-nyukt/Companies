"""
=============================================================
E02 — FastAPI Model Serving: Real-Time Risk Scoring API
=============================================================
Run: uvicorn e02_fastapi_model_serving:app --reload
Test UI: http://localhost:8000/docs

Requires: pip install fastapi uvicorn scikit-learn shap pydantic
=============================================================
"""

import time, pickle, numpy as np, warnings
warnings.filterwarnings("ignore")
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager


# ── Input / Output Schemas ──────────────────────────────────
class DriverFeatures(BaseModel):
    driver_id:          str
    wk_earn_3m:         float = Field(..., ge=0)
    cancel_rate_1m:     float = Field(..., ge=0, le=1)
    bureau_score:       int   = Field(..., ge=300, le=850)
    missed_remit_pct:   float = Field(..., ge=0, le=1)
    debt_to_income:     float = Field(..., ge=0)
    platform_tenure_mo: int   = Field(..., ge=0)
    hard_brake_1m:      int   = Field(..., ge=0)
    downpayment_pct:    float = Field(..., ge=0, le=1)
    ltv_ratio:          float = Field(..., ge=0)
    avg_bank_bal_3m:    float = Field(..., ge=0)

    class Config:
        json_schema_extra = {"example": {
            "driver_id": "DRV_001", "wk_earn_3m": 1500.0,
            "cancel_rate_1m": 0.08, "bureau_score": 680,
            "missed_remit_pct": 0.05, "debt_to_income": 0.35,
            "platform_tenure_mo": 18, "hard_brake_1m": 4,
            "downpayment_pct": 0.25, "ltv_ratio": 0.72,
            "avg_bank_bal_3m": 2500.0
        }}


class RiskPrediction(BaseModel):
    driver_id:    str
    risk_score:   float
    risk_band:    str
    decision:     str
    reason_codes: list[dict]
    latency_ms:   float


# ── Model Manager ───────────────────────────────────────────
FEATURE_NAMES = [
    "wk_earn_3m", "cancel_rate_1m", "bureau_score",
    "missed_remit_pct", "debt_to_income", "platform_tenure_mo",
    "hard_brake_1m", "downpayment_pct", "ltv_ratio", "avg_bank_bal_3m",
]

class ModelManager:
    def __init__(self):
        self.model     = None
        self.explainer = None
        self._t0       = time.time()

    def load(self):
        """Load or train model. In production: mlflow.sklearn.load_model(uri)"""
        import os
        from sklearn.ensemble import GradientBoostingClassifier
        path = "credit_risk_model.pkl"
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.model = pickle.load(f)
            print("[Model] Loaded from disk")
        else:
            print("[Model] Training demo model...")
            rng = np.random.default_rng(42)
            n = 3000
            X = rng.standard_normal((n, len(FEATURE_NAMES)))
            lp = -2 + 0.8*X[:,0] - 0.5*X[:,2] + 0.6*X[:,3]
            y  = (1/(1+np.exp(-lp)) > 0.5).astype(int)
            self.model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
            self.model.fit(X, y)
            with open(path, "wb") as f:
                pickle.dump(self.model, f)
            print("[Model] Saved to disk")
        # SHAP
        try:
            import shap
            self.explainer = shap.TreeExplainer(self.model)
            print("[SHAP] Explainer ready [OK]")
        except ImportError:
            print("[SHAP] Not installed — reason codes disabled")

    def predict(self, feat: list[float]) -> dict:
        X = np.array(feat).reshape(1, -1)
        score = float(self.model.predict_proba(X)[0, 1])
        band  = "LOW" if score < 0.3 else ("MEDIUM" if score < 0.6 else "HIGH")
        dec   = "APPROVE" if score < 0.3 else ("REVIEW" if score < 0.6 else "DECLINE")
        codes = []
        if self.explainer:
            sv  = self.explainer.shap_values(X)[0]
            for rank, idx in enumerate(np.argsort(np.abs(sv))[::-1][:3], 1):
                codes.append({"rank": rank, "feature": FEATURE_NAMES[idx],
                               "value": round(float(X[0,idx]),4),
                               "shap":  round(float(sv[idx]),4),
                               "direction": "(+) Increases risk" if sv[idx]>0 else "(-) Decreases risk"})
        return {"risk_score": round(score,4), "risk_band": band,
                "decision": dec, "reason_codes": codes}

    @property
    def uptime(self):
        return round(time.time() - self._t0, 1)


# ── App ─────────────────────────────────────────────────────
mgr = ModelManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    mgr.load()
    yield

app = FastAPI(
    title="Driver Credit Risk API",
    description="Real-time PD scoring for driver loans. SHAP reason codes included.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": mgr.model is not None, "uptime_sec": mgr.uptime}


@app.post("/predict", response_model=RiskPrediction)
async def predict(req: DriverFeatures):
    """Score one driver. Returns risk_score, decision, and SHAP reason codes."""
    if not mgr.model:
        raise HTTPException(503, "Model not loaded")
    t0   = time.perf_counter()
    feat = [req.wk_earn_3m, req.cancel_rate_1m, req.bureau_score,
            req.missed_remit_pct, req.debt_to_income, req.platform_tenure_mo,
            req.hard_brake_1m, req.downpayment_pct, req.ltv_ratio, req.avg_bank_bal_3m]
    result = mgr.predict(feat)
    return RiskPrediction(driver_id=req.driver_id,
                          latency_ms=round((time.perf_counter()-t0)*1000, 2),
                          **result)


@app.post("/predict/batch")
async def predict_batch(reqs: list[DriverFeatures]):
    if len(reqs) > 1000:
        raise HTTPException(400, "Max 1000 per batch")
    return [await predict(r) for r in reqs]


# ── Local test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  E02 — FastAPI Model Serving (local test)")
    print("=" * 55)
    mgr.load()
    feat = [1500.0, 0.08, 680, 0.05, 0.35, 18, 4, 0.25, 0.72, 2500.0]
    r = mgr.predict(feat)
    print(f"\n  Score: {r['risk_score']} | Band: {r['risk_band']} | Decision: {r['decision']}")
    for rc in r["reason_codes"]:
        print(f"    {rc}")
    print("\n  To run API: uvicorn e02_fastapi_model_serving:app --reload")
    print("  Swagger UI: http://localhost:8000/docs")
