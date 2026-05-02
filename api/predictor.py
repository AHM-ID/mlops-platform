def infer(model, df):
    pred = model.predict(df)[0]
    prob = 0.5
    
    try:
        # Method 1: Direct predict_proba
        if hasattr(model, 'predict_proba'):
            prob = model.predict_proba(df)[0][1]
        # Method 2: For MLflow PyFuncModel (most likely your case)
        elif hasattr(model, '_model_impl') and hasattr(model._model_impl, 'predict_proba'):
            prob = model._model_impl.predict_proba(df)[0][1]
        # Method 3: For wrapped sklearn models
        elif hasattr(model, 'sk_model') and hasattr(model.sk_model, 'predict_proba'):
            prob = model.sk_model.predict_proba(df)[0][1]
        else:
            prob = float(pred)
    except Exception as e:
        prob = float(pred)
    
    return int(pred), float(prob)