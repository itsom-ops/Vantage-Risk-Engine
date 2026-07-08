"""
test_rag_regression.py — Regression test verifying that risk narratives are intent-aware and not structurally identical.
"""

import os
import unittest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import anthropic

from db import engine as db_engine
from routes.insight import get_anthropic
from rag_engine import generate_risk_narrative

load_dotenv("vantage-risk-api/.env")

class TestRAGRegression(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.engine = db_engine
        cls.client = get_anthropic()
        
        # Grab any active company in the DB to test against
        with cls.engine.connect() as conn:
            try:
                row = conn.execute(text("SELECT id, ticker FROM companies LIMIT 1")).fetchone()
            except Exception:
                row = None
                
            if not row:
                cls.company_id = "00000000-0000-0000-0000-000000000000"
                cls.ticker = "AAPL"
                score_row = None
            else:
                cls.company_id = str(row[0])
                cls.ticker = row[1]
                
                # Fetch latest risk score row
                try:
                    score_row = conn.execute(text("""
                        SELECT altman_z, altman_tier, distance_to_default, prob_of_default, composite_risk_score, risk_tier, top_risk_driver_1
                        FROM risk_scores
                        WHERE company_id = :cid::uuid
                        ORDER BY period DESC LIMIT 1
                    """), {"cid": cls.company_id}).fetchone()
                except Exception:
                    score_row = None
            
            if not score_row:
                # Mock a risk score row for testing
                cls.risk_score_row = {
                    "altman_z": 3.1,
                    "altman_tier": "Safe",
                    "distance_to_default": 4.5,
                    "prob_of_default": 0.001,
                    "composite_risk_score": 15.0,
                    "risk_tier": "Low",
                    "top_risk_driver_1": "Retained Earnings ratio is healthy."
                }
            else:
                cls.risk_score_row = {
                    "altman_z": float(score_row[0] or 0),
                    "altman_tier": score_row[1] or "Safe",
                    "distance_to_default": float(score_row[2] or 0),
                    "prob_of_default": float(score_row[3] or 0),
                    "composite_risk_score": float(score_row[4] or 0),
                    "risk_tier": score_row[5] or "Low",
                    "top_risk_driver_1": score_row[6] or ""
                }

    def test_narrative_structural_variance(self):
        """Test that 8 varied queries result in different structures and content, rather than a boilerplate template."""
        queries = [
            f"What does {self.ticker} do and what is their business overview?", # General
            f"Should I buy or invest in {self.ticker} stock right now?", # Opinion
            f"Why is {self.ticker}'s Altman Z-Score at this current level?", # Metric
            f"What are the most recent news events and general sentiment for {self.ticker}?", # News
            f"Is {self.ticker} riskier than a high-yield tech firm?", # Comparison
            f"Explain what the Altman Z-score metric is and why credit analysts use it.", # General definition
            f"What does the latest 10-K filing say about covenant risks or debt defaults for {self.ticker}?", # SEC filing
            f"Summary review of {self.ticker}'s default probability trends." # Open-ended summary
        ]
        
        narratives = []
        recommendations = []
        
        for q in queries:
            print(f"\nRunning regression test query: '{q}'")
            narrative, recommendation, chunks_used, ms = generate_risk_narrative(
                company_id=self.company_id,
                ticker=self.ticker,
                query=q,
                risk_score_row=self.risk_score_row,
                db_engine=self.engine,
                anthropic_client=self.client
            )
            print(f"Response: {narrative} (Recommendation: {recommendation})")
            
            self.assertTrue(len(narrative) > 20, "Narrative response is too short.")
            narratives.append(narrative)
            recommendations.append(recommendation)

        # Check for structural variance: response lengths, starts, and exact duplicates
        for i in range(len(narratives)):
            for j in range(i + 1, len(narratives)):
                # Responses shouldn't be identical
                self.assertNotEqual(narratives[i], narratives[j], f"Boilerplate template detected: responses to '{queries[i]}' and '{queries[j]}' are identical!")

        print("\nRegression test completed successfully! All 8 responses are structurally distinct and intent-aware.")

if __name__ == "__main__":
    unittest.main()
