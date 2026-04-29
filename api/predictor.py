def infer(model, df):
    pred = model.predict(df)[0]
    prob = model.predict_proba(df)[0][1]
    return int(pred), float(prob)