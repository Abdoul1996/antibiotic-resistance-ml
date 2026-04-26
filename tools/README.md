## External Tools

### STREAMLINE

* **Source:** https://github.com/UrbsLab/STREAMLINE

* **Version used:** Commit `<commit-hash>` (accessed on <date>)

* **Purpose:**
  STREAMLINE was used as the primary automated machine learning pipeline to train, evaluate, and compare classification models on two genomic feature representations:
  (1) gene presence/absence (GPA) and
  (2) SNP-based features.

* **How it was used in this project:**

  * Trained multiple ML models (e.g., Random Forest, XGBoost, Logistic Regression)
  * Performed cross-validation and model evaluation
  * Generated performance metrics (accuracy, F1-score, ROC-AUC, etc.)
  * Enabled consistent comparison between GPA and SNP datasets

* **Input data:**

  * Preprocessed feature matrices derived from pangenome analysis
  * Labels indicating ciprofloxacin resistance

* **Output:**

  * Model performance metrics
  * Evaluation plots (e.g., bar charts, boxplots)
  * Trained model artifacts

* **Notes / Modifications:**

  * Models were trained separately for GPA and SNP datasets (no feature mixing)
  * Default pipeline was used with minor configuration adjustments (specify if any)
  * Deep learning experiments were conducted outside of STREAMLINE



### TabR (Tabular Deep Learning Model)

* **Source:** https://github.com/yandex-research/tabular-dl-tabr

* **Developed by:** Yandex Research

* **Version used:** Commit `<commit-hash>` (accessed on <2025>)

* **Purpose:**
  TabR is a transformer-based model specifically designed for tabular data. It was used to evaluate whether modern deep learning approaches tailored for tabular datasets can outperform traditional machine learning models in predicting ciprofloxacin resistance.

* **How it was used in this project:**

  * Trained TabR models on both SNP and gene presence/absence (GPA) datasets
  * Used the same train/test splits and evaluation metrics as the ML pipeline
  * Benchmarked performance directly against models implemented via STREAMLINE

* **Input data:**

  * Preprocessed SNP feature matrix
  * Gene presence/absence (GPA) matrix
  * Binary resistance labels

* **Output:**

  * Model predictions
  * Performance metrics (e.g., accuracy, F1-score, ROC-AUC)

* **Notes / Modifications:**

  * Executed independently from the STREAMLINE pipeline
  * Minimal architectural changes; used implementation as provided by the authors
  * Focused on fair comparison rather than extensive hyperparameter tuning (adjust if needed)
