import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle

# STEP 1: Load dataset
data = pd.read_csv("health_data_large.csv")

print("Dataset Loaded:")
print(data.head())

# STEP 2: Separate inputs and output
X = data[['HR', 'SpO2', 'temp', 'acc']]
y = data['condition']

# STEP 3: Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# STEP 4: Train model
model = DecisionTreeClassifier()
model.fit(X_train, y_train)

print("Model trained successfully!")

# STEP 5: Evaluate
y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))
print("\nConfusion Matrix:\n")
print(confusion_matrix(y_test, y_pred))

# STEP 6: Test prediction
test_data = [[155, 99, 37.5, 1.5]]
prediction = model.predict(test_data)
print("Test Prediction:", prediction)

# STEP 7: Save model
with open("model_large.pkl", "wb") as f:
    pickle.dump(model, f)

print("Model saved as model_large.pkl")