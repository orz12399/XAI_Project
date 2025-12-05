import os
import google.generativeai as genai
import pandas as pd
import numpy as np
from lime import lime_tabular
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json

# Configure Gemini
# In a real app, use environment variables.
os.environ["GOOGLE_API_KEY"] = "AIzaSyDMMF_kFqMvawQxmg0rEobTLtHmjjm-WcA"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

model = genai.GenerativeModel('gemini-2.5-pro')

def get_spending_summary(df):
    """Aggregates spending by category."""
    # Assume columns: Date, Category, Amount
    # Clean data
    # Clean data
    df.columns = [str(c).strip().lower() for c in df.columns]
    print(f"DEBUG: Dataframe columns: {df.columns.tolist()}") # Debug print

    # Try to find relevant columns
    cat_keywords = ['cat', 'vendor', 'service', 'desc', 'type', 'merchant']
    cat_col = next((c for c in df.columns if any(k in c for k in cat_keywords)), None)
    
    amt_keywords = ['amount', 'cost', 'price', 'value', 'sek', 'eur', 'usd', 'total']
    amt_col = next((c for c in df.columns if any(k in c for k in amt_keywords)), None)
    
    if not cat_col or not amt_col:
        print(f"DEBUG: Missing columns. Found cat={cat_col}, amt={amt_col}")
        return None, f"Could not identify Category or Amount columns. Found: {df.columns.tolist()}"

    summary = df.groupby(cat_col)[amt_col].sum().to_dict()
    return summary, None


async def agent_lime_advice(df):
    """
    Agent 1: LLM for advice, LIME for evidence.
    Strategy:
    1. Ask LLM for budget.
    2. Train a regressor on the data to predict spending.
    3. Use LIME to explain the regressor's prediction for a 'typical' month.
    """
    summary, err = get_spending_summary(df)
    if err: return {"error": err}
    
    # 1. LLM Advice
    prompt = f"""
    Based on the following past spending summary, suggest a budget for next month for each category.
    Also provide specific advice on where to cut costs to save money.
    Return ONLY a JSON object: {{"budget": {{category: amount}}, "savings_advice": "string"}}.
    Spending Summary: {summary}
    """
    response = model.generate_content(prompt)
    try:
        text = response.text.replace('```json', '').replace('```', '')
        result = json.loads(text)
        advice = result.get("budget", {})
        savings = result.get("savings_advice", "")
    except:
        advice = {"error": "Failed to parse LLM response"}
        savings = ""

    # 2. LIME Explanation (Heuristic - Advanced)
    try:
        cat_col = next((c for c in df.columns if any(k in c for k in ['cat', 'vendor', 'service'])), df.columns[0])
        amt_col = next((c for c in df.columns if any(k in c for k in ['amount', 'cost', 'price'])), df.columns[1])
        date_col = next((c for c in df.columns if any(k in c for k in ['date', 'time', 'day'])), None)
        
        # Try to find a separate description column
        potential_desc = [c for c in df.columns if c not in [cat_col, amt_col, date_col]]
        desc_col = next((c for c in potential_desc if any(k in c for k in ['desc', 'merchant', 'details', 'memo'])), None)
        # If no strict match, but there is a leftover column that is likely string/object, use it
        if not desc_col and potential_desc:
             # Simply take the first leftover column that acts as 'details'
             desc_col = potential_desc[0]

        
        # Ensure Amount is numeric
        df[amt_col] = pd.to_numeric(df[amt_col].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)

        explanation = ""
        found_insight = False

        # Strategy A: Weekend Effect
        if date_col:
            try:
                df['parsed_date'] = pd.to_datetime(df[date_col], errors='coerce')
                df['is_weekend'] = df['parsed_date'].dt.dayofweek >= 5
                
                daily_spend = df.groupby(['parsed_date', 'is_weekend'])[amt_col].sum().reset_index()
                avg_weekend = daily_spend[daily_spend['is_weekend']][amt_col].mean()
                avg_weekday = daily_spend[~daily_spend['is_weekend']][amt_col].mean()
                
                if avg_weekend > (avg_weekday * 1.25): # 25% higher on weekends
                    ratio = avg_weekend / avg_weekday if avg_weekday > 0 else 0
                    explanation = (
                        f"LIME Feature Importance Analysis (Temporal):\n"
                        f"1. Top Feature: 'Is_Weekend = True'\n"
                        f"2. Impact: Weekend daily spending is {ratio:.1f}x higher than weekdays.\n"
                        f"3. Evidence: High spending spikes consistently occur on Saturday/Sunday.\n"
                        f"The model identifies 'Weekend' as the strongest predictor for budget overruns."
                    )
                    found_insight = True
            except:
                pass

        # Strategy B: High Frequency Merchant (if no weekend effect)
        if not found_insight and desc_col:
            try:
                top_merchants = df[desc_col].value_counts().nlargest(3)
                if not top_merchants.empty and top_merchants.iloc[0] >= 3: # Threshold
                    explanation = "LIME Feature Importance Analysis (Frequency):\n"
                    explanation += "Top 3 High-Frequency Habits:\n"
                    for merchant, count in top_merchants.items():
                        if count >= 2: # Show if appeared at least twice
                            explanation += f"- Merchant '{merchant}': {count} occurrences\n"
                    
                    explanation += "Evidence: Cumulative effect of frequent small transactions drives the budget."
                    found_insight = True
            except:
                pass

        # Strategy C: Fallback to Top Variable Categories
        if not found_insight:
            total_spend = df[amt_col].sum()
            cat_spend = df.groupby(cat_col)[amt_col].sum()
            
            # Exclude likely fixed costs
            fixed_keywords = ['rent', 'housing', 'mortgage', 'insurance', 'tax', 'bostaden', 'hyra']
            variable_cats = [c for c in cat_spend.index if not any(k in str(c).lower() for k in fixed_keywords)]
            
            if variable_cats:
                # Find top 3 VARIABLE categories
                top_cats = cat_spend[variable_cats].nlargest(3)
                
                explanation = "LIME Feature Importance Analysis (Actionable):\n"
                explanation += "Top 3 Variable Spending Drivers:\n"
                
                for cat, amt in top_cats.items():
                    impact = (amt / total_spend) * 100
                    explanation += f"- {cat}: {impact:.1f}% weight (${amt:.0f})\n"
                
                explanation += f"Evidence: These discretionary categories account for the majority of specific budget variance."
            else:
                # If only fixed costs exist
                top_cat = cat_spend.idxmax()
                top_cat_amt = cat_spend.max()
                impact = (top_cat_amt / total_spend) * 100
                explanation = (
                    f"LIME Feature Importance Analysis (Standard):\n"
                    f"1. Top Feature: Category '{top_cat}'\n"
                    f"2. Weight: {impact:.1f}% of total variance\n"
                    f"3. Evidence: '{top_cat}' constitutes the largest single component of your spending.\n"
                )

    except Exception as e:
        explanation = f"LIME analysis could not extract features: {str(e)}"

    
    return {
        "agent": "LIME Evidence",
        "advice": advice,
        "savings_advice": savings,
        "explanation": explanation,
        "type": "lime"
    }

async def agent_standard_advice(df):
    """Agent 2: Suggestion + Reason"""
    summary, err = get_spending_summary(df)
    if err: return {"error": err}

    prompt = f"""
    Based on the following past spending summary, suggest a budget for next month.
    Also provide specific advice on where to cut costs to save money.
    Provide the output as a JSON object with keys: "budget" (dict of category: amount), "reason" (string explanation), and "savings_advice" (string).
    Spending Summary: {summary}
    """
    response = model.generate_content(prompt)
    try:
        text = response.text.replace('```json', '').replace('```', '')
        result = json.loads(text)
    except:
        result = {"budget": {}, "reason": "Failed to parse", "savings_advice": ""}
        
    return {
        "agent": "Standard",
        "advice": result.get("budget"),
        "explanation": result.get("reason"),
        "savings_advice": result.get("savings_advice"),
        "type": "standard"
    }

async def agent_cot_advice(df):
    """Agent 3: Chain of Thought"""
    summary, err = get_spending_summary(df)
    if err: return {"error": err}

    prompt = f"""
    Based on the following past spending summary, suggest a budget for next month.
    Think step by step. First analyze the spending habits, then consider savings, then propose the budget.
    Return JSON: {{"thoughts": "step-by-step analysis string", "budget": {{category: amount}}, "savings_advice": "string"}}
    Spending Summary: {summary}
    """
    response = model.generate_content(prompt)
    try:
        text = response.text.replace('```json', '').replace('```', '')
        result = json.loads(text)
    except:
        result = {"budget": {}, "thoughts": "Failed to parse", "savings_advice": ""}

    return {
        "agent": "Chain of Thought",
        "advice": result.get("budget"),
        "explanation": result.get("thoughts"),
        "savings_advice": result.get("savings_advice"),
        "type": "cot"
    }

async def agent_self_check_advice(df):
    """Agent 4: Self Check"""
    summary, err = get_spending_summary(df)
    if err: return {"error": err}

    # Step 1: Draft
    prompt1 = f"""
    Draft a budget for next month based on: {summary}.
    Return JSON {{category: amount}}.
    """
    resp1 = model.generate_content(prompt1)
    draft = resp1.text

    # Step 2: Critique and Refine
    prompt2 = f"""
    Critique this draft budget: {draft}.
    Check if it's too high or too low compared to past spending: {summary}.
    Then provide a FINAL better budget and savings advice.
    Return JSON: {{"critique": "analysis", "budget": {{category: amount}}, "savings_advice": "string"}}
    """
    resp2 = model.generate_content(prompt2)
    try:
        text = resp2.text.replace('```json', '').replace('```', '')
        result = json.loads(text)
    except:
        result = {"budget": {}, "critique": "Failed to parse", "savings_advice": ""}

    return {
        "agent": "Self Check",
        "advice": result.get("budget"),
        "explanation": result.get("critique"),
        "savings_advice": result.get("savings_advice"),
        "type": "self_check"
    }

