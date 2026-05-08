"""
SWAN-DF Değerlendirme (Evaluation) Servisi.
Modelin tahminleri ile gerçek etiketleri (ground truth) karşılaştırarak
Accuracy, Precision, Recall, F1-Score ve Confusion Matrix hesaplar.
"""

from __future__ import annotations
from typing import Any


class EvaluationService:
    def __init__(self) -> None:
        pass

    def calculate_metrics(self, y_true: list[str], y_pred: list[str], positive_label: str = "fake") -> dict[str, Any]:
        """
        Tahmin ve gerçek etiket listelerini alarak temel performans metriklerini hesaplar.
        
        Args:
            y_true: Gerçek etiketler listesi (ör: ['fake', 'real', 'fake'])
            y_pred: Model tahminleri listesi (ör: ['fake', 'fake', 'real'])
            positive_label: Pozitif sınıfın etiketi (varsayılan: 'fake')
            
        Returns:
            Metrikleri ve confusion matrix'i içeren sözlük.
        """
        if not y_true or not y_pred or len(y_true) != len(y_pred):
            raise ValueError("y_true ve y_pred aynı uzunlukta ve boş olmamalıdır.")

        tp = 0  # True Positive
        tn = 0  # True Negative
        fp = 0  # False Positive
        fn = 0  # False Negative

        for true_label, pred_label in zip(y_true, y_pred):
            true_l = true_label.lower()
            pred_l = pred_label.lower()
            
            if true_l == positive_label.lower():
                if pred_l == positive_label.lower():
                    tp += 1
                else:
                    fn += 1
            else:
                if pred_l == positive_label.lower():
                    fp += 1
                else:
                    tn += 1

        total = tp + tn + fp + fn
        
        accuracy = (tp + tn) / total if total > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        if precision + recall > 0:
            f1_score = 2 * (precision * recall) / (precision + recall)
        else:
            f1_score = 0.0

        confusion_matrix = {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "matrix": [
                [tn, fp],  # [True Negative, False Positive]
                [fn, tp]   # [False Negative, True Positive]
            ]
        }

        return {
            "total_samples": total,
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "confusion_matrix": confusion_matrix
        }

    def evaluate_model_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Veritabanından çekilen EvaluationResult (dict formatında) listesini değerlendirir.
        
        Beklenen result formatı:
        {
            "ground_truth_label": "fake",
            "prediction_score": 0.85
        }
        """
        y_true = []
        y_pred = []
        
        for r in results:
            y_true.append(r.get("ground_truth_label", "real"))
            score = r.get("prediction_score", 0.0)
            # Threshold 0.5 kabul ediliyor
            y_pred.append("fake" if score >= 0.5 else "real")
            
        return self.calculate_metrics(y_true, y_pred, positive_label="fake")

    def generate_paper_table(self, metrics: dict[str, Any], model_name: str = "SWAN-DF") -> str:
        """
        Hesaplanan metrikleri akademik makale tablosu (Markdown formatında) olarak döndürür.
        """
        return (
            f"| Model | Accuracy | Precision | Recall | F1-Score |\\n"
            f"|-------|----------|-----------|--------|----------|\\n"
            f"| {model_name} | {metrics.get('accuracy', 0):.4f} | {metrics.get('precision', 0):.4f} | "
            f"{metrics.get('recall', 0):.4f} | {metrics.get('f1_score', 0):.4f} |"
        )

    def generate_latex_table(self, metrics: dict[str, Any], model_name: str = "SWAN-DF") -> str:
        """
        Hesaplanan metrikleri akademik makale tablosu (LaTeX formatında) olarak döndürür.
        """
        return (
            "\\\\begin{table}[h]\\n"
            "\\\\centering\\n"
            "\\\\begin{tabular}{l c c c c}\\n"
            "\\\\hline\\n"
            "Model & Accuracy & Precision & Recall & F1-Score \\\\\\\\\\n"
            "\\\\hline\\n"
            f"{model_name} & {metrics.get('accuracy', 0):.4f} & {metrics.get('precision', 0):.4f} & "
            f"{metrics.get('recall', 0):.4f} & {metrics.get('f1_score', 0):.4f} \\\\\\\\\\n"
            "\\\\hline\\n"
            "\\\\end{tabular}\\n"
            "\\\\caption{Performance Evaluation Metrics}\\n"
            "\\\\label{tab:metrics}\\n"
            "\\\\end{table}"
        )
