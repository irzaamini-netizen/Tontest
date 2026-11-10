def precision_recall(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    return {"precision": p, "recall": r, "tp": tp, "fp": fp, "fn": fn}
