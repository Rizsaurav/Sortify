"""
Classifier Training Script
==========================
Trains a fast classifier from embeddings + category labels.

Input: training_data_with_embeddings.json
Output: category_classifier.pkl (ready for production)
"""

import json
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from typing import Dict, Any, Tuple, List
from collections import Counter


class ClassifierTrainer:
    """Train document categorization classifier."""
    
    def __init__(self):
        self.classifier = None
        self.label_encoder = {}  # category_name -> index
        self.label_decoder = {}  # index -> category_name
    
    def load_training_data(
        self,
        training_file: str = "training_data_with_embeddings.json"
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Load training data with embeddings."""
        
        with open(training_file, 'r') as f:
            data = json.load(f)
        
        print(f"Loading {len(data)} samples...")
        
        X = []
        y = []
        filenames = []
        
        for sample in data:
            embedding = np.array(sample['embedding'], dtype=np.float32)
            category = sample['category']
            filename = sample['filename']
            
            X.append(embedding)
            y.append(category)
            filenames.append(filename)
        
        unique_labels = sorted(set(y))
        self.label_encoder = {label: idx for idx, label in enumerate(unique_labels)}
        self.label_decoder = {idx: label for label, idx in self.label_encoder.items()}
        
        y_encoded = np.array([self.label_encoder[label] for label in y])
        X = np.array(X)
        
        return X, y_encoded, filenames
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_type: str = "random_forest"
    ) -> Dict[str, Any]:
        """Train classifier."""
        
        print(f"Training {model_type}...")
        
        # Split data 
        unique_classes = len(set(y))
        test_size = 0.2
        min_samples_needed = unique_classes
        
        if len(X) * test_size < min_samples_needed:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
        
        # Choose model
        if model_type == "random_forest":
            self.classifier = RandomForestClassifier(
                n_estimators=200,
                max_depth=30,
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1,
                verbose=0
            )
        elif model_type == "logistic_regression":
            self.classifier = LogisticRegression(
                max_iter=1000,
                random_state=42,
                n_jobs=-1,
                multi_class='multinomial',
                solver='lbfgs'
            )
        
        # Train
        self.classifier.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.classifier.score(X_train, y_train)
        test_score = self.classifier.score(X_test, y_test)
        
        # Cross-validation with auto-adjusted cv
        min_class_size = min(np.bincount(y))
        cv = min(5, min_class_size) if min_class_size >= 2 else 2
        cv_scores = cross_val_score(self.classifier, X, y, cv=cv, n_jobs=-1)
        
        y_pred = self.classifier.predict(X_test)
        
        return {
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'X_test': X_test,
            'y_test': y_test,
            'y_pred': y_pred
        }
    
    def save_model(self, output_file: str = "category_classifier.pkl"):
        """
        Save trained model to file.
        
        Args:
            output_file: Where to save model
        """
        if self.classifier is None:
            raise ValueError("No trained model to save!")
        
        model_data = {
            'classifier': self.classifier,
            'label_encoder': self.label_encoder,
            'label_decoder': self.label_decoder
        }
        
        with open(output_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"\nModel saved to: {output_file}")
    
    def load_model(self, model_file: str = "category_classifier.pkl"):
        """
        Load trained model from file.
        
        Args:
            model_file: Path to saved model
        """
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        
        self.classifier = model_data['classifier']
        self.label_encoder = model_data['label_encoder']
        self.label_decoder = model_data['label_decoder']
        
        print(f"Model loaded from: {model_file}")
    
    def predict(
        self,
        embedding: np.ndarray
    ) -> Tuple[str, float]:
        """
        Predict category for a document.
        
        Args:
            embedding: Document embedding vector (1024 dims)
            
        Returns:
            (category_name, confidence)
        """
        if self.classifier is None:
            raise ValueError("No trained model! Train or load a model first.")
        
        # Reshape if single embedding
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        # Predict
        pred_idx = self.classifier.predict(embedding)[0]
        pred_proba = self.classifier.predict_proba(embedding)[0]
        
        category = self.label_decoder[pred_idx]
        confidence = float(pred_proba[pred_idx])
        
        return category, confidence
    
    def predict_batch(
        self,
        embeddings: np.ndarray
    ) -> List[Tuple[str, float]]:
        """
        Predict categories for multiple documents.
        
        Args:
            embeddings: Array of embeddings (N x 1024)
            
        Returns:
            List of (category, confidence) tuples
        """
        if self.classifier is None:
            raise ValueError("No trained model!")
        
        pred_indices = self.classifier.predict(embeddings)
        pred_probas = self.classifier.predict_proba(embeddings)
        
        results = []
        for idx, proba in zip(pred_indices, pred_probas):
            category = self.label_decoder[idx]
            confidence = float(proba[idx])
            results.append((category, confidence))
        
        return results
    
    def plot_confusion_matrix(
        self,
        y_test: np.ndarray,
        y_pred: np.ndarray,
        save_file: str = "confusion_matrix.png"
    ):
        """Plot confusion matrix."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            cm = confusion_matrix(y_test, y_pred)
            
            plt.figure(figsize=(20, 18))
            sns.heatmap(
                cm,
                annot=True,
                fmt='d',
                cmap='Blues',
                xticklabels=[self.label_decoder[i] for i in range(len(self.label_decoder))],
                yticklabels=[self.label_decoder[i] for i in range(len(self.label_decoder))],
                cbar_kws={'label': 'Count'}
            )
            plt.title('Confusion Matrix', fontsize=16, pad=20)
            plt.ylabel('True Category', fontsize=12)
            plt.xlabel('Predicted Category', fontsize=12)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.yticks(rotation=45, fontsize=8)
            plt.tight_layout()
            plt.savefig(save_file, dpi=300, bbox_inches='tight')
            print(f"Confusion matrix saved to: {save_file}")
        except Exception as e:
            print(f"Could not plot confusion matrix: {e}")
            print("Install matplotlib and seaborn to generate visualization")


def main():
    """Main training pipeline."""
    # Initialize trainer
    trainer = ClassifierTrainer()
    
    # Load training data
    X, y, filenames = trainer.load_training_data("training_data_with_embeddings.json")
    
    # Train model
    metrics = trainer.train(X, y, model_type="random_forest")
    
    # Save model
    trainer.save_model("category_classifier.pkl")
    
    print(f"\nTRAINING COMPLETE")
    print(f"Test Accuracy: {metrics['test_accuracy']:.1%}")
    print(f"Model saved: category_classifier.pkl")


if __name__ == "__main__":
    main()